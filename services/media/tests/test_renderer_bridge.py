from __future__ import annotations

import struct

import numpy as np
import pytest

pytest.importorskip("aiortc")

from govor_media.renderer_bridge import (
    AUDIO_BLOCK_CAPACITY,
    AUDIO_CHANNELS,
    AUDIO_HEADER,
    AUDIO_HEADER_SIZE,
    AUDIO_MAGIC,
    AUDIO_MAP_SIZE,
    AUDIO_PAYLOAD_SIZE,
    AUDIO_SAMPLE_RATE,
    AUDIO_SAMPLES_PER_BLOCK,
    AUDIO_SLOT_HEADER,
    AUDIO_SLOT_HEADER_SIZE,
    AUDIO_SLOT_SIZE,
    VIDEO_FLAG_BOTTOM_UP,
    VIDEO_HEADER,
    VIDEO_HEADER_SIZE,
    VIDEO_HEIGHT,
    VIDEO_MAGIC,
    VIDEO_MAP_SIZE,
    VIDEO_PAYLOAD_SIZE,
    VIDEO_PIXEL_FORMAT_RGBA,
    VIDEO_STRIDE,
    VIDEO_WIDTH,
    RendererAudioBufferReader,
    RendererAudioTrack,
    RendererVideoBufferReader,
    RendererVideoTrack,
)


def publish_video(
    buffer: bytearray,
    *,
    sequence: int,
    value: int,
    torn: bool = False,
    generation: int = 71,
) -> None:
    in_progress = sequence * 2 - 1
    published = sequence * 2
    VIDEO_HEADER.pack_into(
        buffer,
        0,
        VIDEO_MAGIC,
        1,
        VIDEO_HEADER_SIZE,
        VIDEO_WIDTH,
        VIDEO_HEIGHT,
        VIDEO_STRIDE,
        VIDEO_PAYLOAD_SIZE,
        in_progress,
        123_456,
        VIDEO_FLAG_BOTTOM_UP,
        VIDEO_PIXEL_FORMAT_RGBA,
        generation,
    )
    buffer[VIDEO_HEADER_SIZE:] = bytes([value]) * VIDEO_PAYLOAD_SIZE
    if not torn:
        struct.pack_into("<Q", buffer, 32, published)


def initialize_audio(buffer: bytearray, *, generation: int = 73) -> None:
    AUDIO_HEADER.pack_into(
        buffer,
        0,
        AUDIO_MAGIC,
        1,
        AUDIO_HEADER_SIZE,
        AUDIO_SAMPLE_RATE,
        AUDIO_CHANNELS,
        AUDIO_SAMPLES_PER_BLOCK,
        AUDIO_BLOCK_CAPACITY,
        AUDIO_SLOT_SIZE,
        0,
        0,
        0,
        generation,
    )


def publish_audio(buffer: bytearray, *, sequence: int, value: int) -> None:
    slot_index = (sequence - 1) % AUDIO_BLOCK_CAPACITY
    slot_offset = AUDIO_HEADER_SIZE + slot_index * AUDIO_SLOT_SIZE
    AUDIO_SLOT_HEADER.pack_into(
        buffer,
        slot_offset,
        0,
        sequence * 20_000,
        AUDIO_SAMPLES_PER_BLOCK,
        0,
    )
    pcm = np.full(AUDIO_SAMPLES_PER_BLOCK, value, dtype="<i2").tobytes()
    assert len(pcm) == AUDIO_PAYLOAD_SIZE
    payload_offset = slot_offset + AUDIO_SLOT_HEADER_SIZE
    buffer[payload_offset : payload_offset + AUDIO_PAYLOAD_SIZE] = pcm
    struct.pack_into("<Q", buffer, slot_offset, sequence)
    struct.pack_into("<Q", buffer, 40, sequence)


def test_video_reader_rejects_in_progress_and_repeated_frames() -> None:
    buffer = bytearray(VIDEO_MAP_SIZE)
    reader = RendererVideoBufferReader(buffer)
    try:
        publish_video(buffer, sequence=1, value=17, torn=True)
        assert reader.read_latest() is None

        struct.pack_into("<Q", buffer, 32, 2)
        frame = reader.read_latest()
        assert frame is not None
        assert (frame.width, frame.height, frame.stride) == (
            VIDEO_WIDTH,
            VIDEO_HEIGHT,
            VIDEO_STRIDE,
        )
        assert frame.bottom_up is True
        assert frame.rgba[:4] == bytes([17, 17, 17, 17])
        assert reader.read_latest() is None

        publish_video(buffer, sequence=1, value=29, generation=72)
        restarted_frame = reader.read_latest()
        assert restarted_frame is not None
        assert restarted_frame.rgba[:4] == bytes([29, 29, 29, 29])
    finally:
        reader.close()


def test_audio_reader_skips_retained_audio_then_preserves_order() -> None:
    buffer = bytearray(AUDIO_MAP_SIZE)
    initialize_audio(buffer)
    for sequence in range(1, 4):
        publish_audio(buffer, sequence=sequence, value=sequence * 100)

    reader = RendererAudioBufferReader(buffer)
    try:
        assert reader.read_next() is None

        publish_audio(buffer, sequence=4, value=400)
        following = reader.read_next()
        assert following is not None
        assert following.sequence == 4
        assert reader.read_next() is None

        initialize_audio(buffer, generation=74)
        publish_audio(buffer, sequence=1, value=900)
        assert reader.read_next() is None
        publish_audio(buffer, sequence=2, value=1_000)
        restarted = reader.read_next()
        assert restarted is not None
        assert restarted.sequence == 2
    finally:
        reader.close()


@pytest.mark.asyncio
async def test_renderer_tracks_emit_720p_video_and_continuous_audio() -> None:
    video_buffer = bytearray(VIDEO_MAP_SIZE)
    publish_video(video_buffer, sequence=1, value=64)
    audio_buffer = bytearray(AUDIO_MAP_SIZE)
    initialize_audio(audio_buffer)
    publish_audio(audio_buffer, sequence=1, value=500)
    video_reader = RendererVideoBufferReader(video_buffer)
    audio_reader = RendererAudioBufferReader(audio_buffer)
    try:
        video_frame = await RendererVideoTrack(video_reader).recv()
        audio_track = RendererAudioTrack(audio_reader)
        audio_frame = await audio_track.recv()
        silence_frame = await audio_track.recv()

        assert (video_frame.width, video_frame.height) == (VIDEO_WIDTH, VIDEO_HEIGHT)
        assert audio_frame.sample_rate == AUDIO_SAMPLE_RATE
        assert audio_frame.samples == AUDIO_SAMPLES_PER_BLOCK
        assert silence_frame.sample_rate == AUDIO_SAMPLE_RATE
        assert silence_frame.samples == AUDIO_SAMPLES_PER_BLOCK
    finally:
        video_reader.close()
        audio_reader.close()
