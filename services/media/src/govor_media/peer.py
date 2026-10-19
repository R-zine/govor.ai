from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal

from aiortc import (
    MediaStreamError,
    MediaStreamTrack,
    RTCPeerConnection,
    RTCSessionDescription,
)
from av import AudioFrame

from .fixture_ice import ForwardedIceConfiguration, install_forwarded_ice
from .microphone_capture import MicrophoneCapture
from .renderer_bridge import RendererBridgeSource
from .tracks import ApplicationAudioTrack, DiagnosticVideoTrack

LOGGER = logging.getLogger("uvicorn.error")


@dataclass(slots=True)
class MicrophoneMetrics:
    frames_received: int = 0
    samples_received: int = 0
    sample_rate_hz: int | None = None


class MediaPeer:
    """One Windows media peer for one Android lesson client."""

    def __init__(
        self,
        *,
        media_source: Literal["diagnostic", "renderer"] = "diagnostic",
        microphone_capture: MicrophoneCapture | None = None,
        forwarded_ice: ForwardedIceConfiguration | None = None,
    ) -> None:
        self.connection = RTCPeerConnection()
        self._renderer_bridge: RendererBridgeSource | None = None
        self._forwarded_ice = forwarded_ice
        self.video: MediaStreamTrack
        self.audio: MediaStreamTrack
        if media_source == "renderer":
            self._renderer_bridge = RendererBridgeSource()
            self.video = self._renderer_bridge.video
            self.audio = self._renderer_bridge.audio
        else:
            self.video = DiagnosticVideoTrack()
            self.audio = ApplicationAudioTrack()
        self.microphone = MicrophoneMetrics()
        self._microphone_capture = microphone_capture
        self.microphone_frame_received = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()
        self.connection.addTrack(self.video)
        self.connection.addTrack(self.audio)

        @self.connection.on("track")
        def on_track(track: MediaStreamTrack) -> None:
            if track.kind == "audio":
                task = asyncio.create_task(self._consume_microphone(track))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

        @self.connection.on("connectionstatechange")
        def on_connection_state_change() -> None:
            LOGGER.info("WebRTC connection state changed: %s", self.connection.connectionState)

    async def accept_offer(self, sdp: str) -> str:
        if not sdp or len(sdp.encode("utf-8")) > 1_048_576:
            raise ValueError("SDP offer is empty or too large")
        await self.connection.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
        answer = await self.connection.createAnswer()
        if self._forwarded_ice is not None:
            await install_forwarded_ice(self.connection, self._forwarded_ice)
        await self.connection.setLocalDescription(answer)
        local = self.connection.localDescription
        if local is None:
            raise RuntimeError("WebRTC failed to create a local answer")
        return local.sdp

    async def close(self) -> None:
        for task in tuple(self._tasks):
            task.cancel()
        for task in tuple(self._tasks):
            with suppress(asyncio.CancelledError):
                await task
        try:
            await self.connection.close()
        finally:
            if self._renderer_bridge is not None:
                self._renderer_bridge.close()
                self._renderer_bridge = None

    async def _consume_microphone(self, track: MediaStreamTrack) -> None:
        try:
            while True:
                frame = await track.recv()
                self.microphone.frames_received += 1
                self.microphone.samples_received += getattr(frame, "samples", 0)
                self.microphone.sample_rate_hz = getattr(frame, "sample_rate", None)
                if self._microphone_capture is not None and isinstance(frame, AudioFrame):
                    self._microphone_capture.append(frame)
                if self.microphone.frames_received == 1:
                    LOGGER.info(
                        "Received first client microphone frame: sample_rate_hz=%s samples=%s",
                        self.microphone.sample_rate_hz,
                        getattr(frame, "samples", 0),
                    )
                self.microphone_frame_received.set()
        except MediaStreamError:
            # Normal remote-track teardown must not surface as an unobserved task exception.
            return
