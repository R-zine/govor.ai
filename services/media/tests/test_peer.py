from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

pytest.importorskip("aiortc")

from aiortc import MediaStreamError, MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from govor_media import ApplicationAudioTrack, MediaPeer


class EndedAudioTrack(MediaStreamTrack):
    kind = "audio"

    async def recv(self) -> None:
        raise MediaStreamError


@pytest.mark.asyncio
async def test_microphone_consumer_treats_track_end_as_normal_teardown() -> None:
    peer = MediaPeer()
    try:
        await peer._consume_microphone(EndedAudioTrack())
        assert peer.microphone.frames_received == 0
    finally:
        await peer.close()


@pytest.mark.asyncio
async def test_bidirectional_audio_and_video_loopback() -> None:
    client = RTCPeerConnection()
    server = MediaPeer()
    remote_tracks: dict[str, MediaStreamTrack] = {}
    track_received = asyncio.Event()

    @client.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        remote_tracks[track.kind] = track
        if {"audio", "video"}.issubset(remote_tracks):
            track_received.set()

    microphone = ApplicationAudioTrack(frequency_hz=330.0)
    client.addTrack(microphone)
    client.addTransceiver("video", direction="recvonly")

    try:
        offer = await client.createOffer()
        await client.setLocalDescription(offer)
        local_offer = client.localDescription
        assert local_offer is not None
        answer_sdp = await server.accept_offer(local_offer.sdp)
        await client.setRemoteDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))

        await asyncio.wait_for(track_received.wait(), timeout=10)
        video_frame = await asyncio.wait_for(remote_tracks["video"].recv(), timeout=10)
        audio_frame = await asyncio.wait_for(remote_tracks["audio"].recv(), timeout=10)
        await asyncio.wait_for(server.microphone_frame_received.wait(), timeout=10)

        assert video_frame.width == 1280
        assert video_frame.height == 720
        assert audio_frame.sample_rate == 48_000
        assert server.microphone.frames_received > 0
        assert server.microphone.samples_received > 0
    finally:
        with suppress(Exception):
            await client.close()
        await server.close()
