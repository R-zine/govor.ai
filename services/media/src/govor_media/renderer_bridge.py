"""Windows-local renderer-to-aiortc media bridge.

The Godot renderer publishes one latest RGBA video frame and a bounded ring of mono PCM blocks
through named memory mappings. These mappings are local inter-process transport only; aiortc
remains the sole network-facing media implementation.
"""

from __future__ import annotations

import asyncio
import logging
import mmap
import struct
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, cast

import numpy as np
from aiortc import AudioStreamTrack, VideoStreamTrack
from av import AudioFrame, VideoFrame

LOGGER = logging.getLogger("uvicorn.error")

VIDEO_MAP_NAME = "govor.ai.renderer.video.v1"
AUDIO_MAP_NAME = "govor.ai.renderer.audio.v1"

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_BYTES_PER_PIXEL = 4
VIDEO_STRIDE = VIDEO_WIDTH * VIDEO_BYTES_PER_PIXEL
VIDEO_HEADER_SIZE = 64
VIDEO_PAYLOAD_SIZE = VIDEO_STRIDE * VIDEO_HEIGHT
VIDEO_MAP_SIZE = VIDEO_HEADER_SIZE + VIDEO_PAYLOAD_SIZE
VIDEO_MAGIC = b"GOVVID01"
VIDEO_PIXEL_FORMAT_RGBA = 1
VIDEO_FLAG_BOTTOM_UP = 1
VIDEO_HEADER = struct.Struct("<8sIIIIIIQqIIQ")
VIDEO_SEQUENCE_OFFSET = 32
VIDEO_GENERATION_OFFSET = 56

AUDIO_SAMPLE_RATE = 48_000
AUDIO_CHANNELS = 1
AUDIO_SAMPLES_PER_BLOCK = 960
AUDIO_BLOCK_CAPACITY = 64
AUDIO_HEADER_SIZE = 64
AUDIO_SLOT_HEADER_SIZE = 24
AUDIO_PAYLOAD_SIZE = AUDIO_SAMPLES_PER_BLOCK * 2
AUDIO_SLOT_SIZE = AUDIO_SLOT_HEADER_SIZE + AUDIO_PAYLOAD_SIZE
AUDIO_MAP_SIZE = AUDIO_HEADER_SIZE + AUDIO_BLOCK_CAPACITY * AUDIO_SLOT_SIZE
AUDIO_MAGIC = b"GOVAUD01"
AUDIO_HEADER = struct.Struct("<8sIIIIIIIIQqQ")
AUDIO_WRITE_SEQUENCE_OFFSET = 40
AUDIO_GENERATION_OFFSET = 56
AUDIO_SLOT_HEADER = struct.Struct("<QqII")


def _open_named_mapping(name: str, size: int) -> mmap.mmap:
    if sys.platform != "win32":
        raise RuntimeError("The renderer bridge currently supports Windows only")
    # The Windows mmap signature has a tagname parameter that is intentionally absent on Unix.
    mapping_factory = cast(Any, mmap.mmap)
    return cast(mmap.mmap, mapping_factory(-1, size, name, mmap.ACCESS_WRITE))


@dataclass(frozen=True, slots=True)
class RendererVideoFrame:
    width: int
    height: int
    stride: int
    media_time_us: int
    bottom_up: bool
    rgba: bytes


class RendererVideoBufferReader:
    """Read complete video publications while rejecting torn or malformed frames."""

    def __init__(self, buffer: mmap.mmap | bytearray | memoryview) -> None:
        self._buffer = memoryview(buffer)
        if len(self._buffer) < VIDEO_MAP_SIZE:
            raise ValueError("video bridge buffer is smaller than the protocol capacity")
        self._last_sequence = 0
        self._writer_generation = 0

    def close(self) -> None:
        self._buffer.release()

    def read_latest(self) -> RendererVideoFrame | None:
        header = VIDEO_HEADER.unpack_from(self._buffer)
        (
            magic,
            version,
            header_size,
            width,
            height,
            stride,
            payload_size,
            sequence,
            media_time_us,
            flags,
            pixel_format,
            writer_generation,
        ) = header
        if (
            magic != VIDEO_MAGIC
            or version != 1
            or header_size != VIDEO_HEADER_SIZE
            or width != VIDEO_WIDTH
            or height != VIDEO_HEIGHT
            or stride != VIDEO_STRIDE
            or payload_size != VIDEO_PAYLOAD_SIZE
            or pixel_format != VIDEO_PIXEL_FORMAT_RGBA
            or writer_generation == 0
            or sequence == 0
            or sequence % 2 != 0
        ):
            return None

        if writer_generation != self._writer_generation:
            self._writer_generation = writer_generation
            self._last_sequence = 0
        if sequence == self._last_sequence:
            return None

        rgba = bytes(self._buffer[VIDEO_HEADER_SIZE : VIDEO_HEADER_SIZE + payload_size])
        (sequence_after_copy,) = struct.unpack_from("<Q", self._buffer, VIDEO_SEQUENCE_OFFSET)
        (generation_after_copy,) = struct.unpack_from("<Q", self._buffer, VIDEO_GENERATION_OFFSET)
        if (
            sequence_after_copy != sequence
            or sequence_after_copy % 2 != 0
            or generation_after_copy != writer_generation
        ):
            return None

        self._last_sequence = sequence
        return RendererVideoFrame(
            width=width,
            height=height,
            stride=stride,
            media_time_us=media_time_us,
            bottom_up=bool(flags & VIDEO_FLAG_BOTTOM_UP),
            rgba=rgba,
        )


@dataclass(frozen=True, slots=True)
class RendererAudioBlock:
    sequence: int
    media_time_us: int
    pcm_s16le: bytes


class RendererAudioBufferReader:
    """Consume ordered PCM blocks from the bounded renderer ring."""

    def __init__(self, buffer: mmap.mmap | bytearray | memoryview) -> None:
        self._buffer = memoryview(buffer)
        if len(self._buffer) < AUDIO_MAP_SIZE:
            raise ValueError("audio bridge buffer is smaller than the protocol capacity")
        self._last_sequence = 0
        self._writer_generation = 0

    def close(self) -> None:
        self._buffer.release()

    def read_next(self) -> RendererAudioBlock | None:
        header = AUDIO_HEADER.unpack_from(self._buffer)
        (
            magic,
            version,
            header_size,
            sample_rate,
            channels,
            samples_per_block,
            capacity,
            slot_size,
            _reserved,
            write_sequence,
            _latest_media_time_us,
            writer_generation,
        ) = header
        if (
            magic != AUDIO_MAGIC
            or version != 1
            or header_size != AUDIO_HEADER_SIZE
            or sample_rate != AUDIO_SAMPLE_RATE
            or channels != AUDIO_CHANNELS
            or samples_per_block != AUDIO_SAMPLES_PER_BLOCK
            or capacity != AUDIO_BLOCK_CAPACITY
            or slot_size != AUDIO_SLOT_SIZE
            or writer_generation == 0
            or write_sequence == 0
        ):
            return None

        if writer_generation != self._writer_generation:
            self._writer_generation = writer_generation
            # Join after the current write position. Replaying the last retained block here would
            # emit stale audio when a peer reconnects after the renderer has stopped producing PCM.
            self._last_sequence = write_sequence
            return None
        if write_sequence <= self._last_sequence:
            return None

        target_sequence = self._last_sequence + 1
        oldest_available = max(1, write_sequence - capacity + 1)
        target_sequence = max(target_sequence, oldest_available)

        slot_index = (target_sequence - 1) % capacity
        slot_offset = header_size + slot_index * slot_size
        sequence, media_time_us, sample_count, _slot_reserved = AUDIO_SLOT_HEADER.unpack_from(
            self._buffer, slot_offset
        )
        if sequence != target_sequence or sample_count != AUDIO_SAMPLES_PER_BLOCK:
            return None

        payload_offset = slot_offset + AUDIO_SLOT_HEADER_SIZE
        payload_size = sample_count * 2
        pcm = bytes(self._buffer[payload_offset : payload_offset + payload_size])
        (sequence_after_copy,) = struct.unpack_from("<Q", self._buffer, slot_offset)
        (generation_after_copy,) = struct.unpack_from("<Q", self._buffer, AUDIO_GENERATION_OFFSET)
        if sequence_after_copy != target_sequence or generation_after_copy != writer_generation:
            return None

        self._last_sequence = target_sequence
        return RendererAudioBlock(
            sequence=target_sequence,
            media_time_us=media_time_us,
            pcm_s16le=pcm,
        )


class RendererVideoTrack(VideoStreamTrack):
    """Pace and expose the latest complete renderer frame to aiortc."""

    def __init__(self, reader: RendererVideoBufferReader) -> None:
        super().__init__()
        self._reader = reader
        self._last_rgba = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 4), dtype=np.uint8)
        self._reported_renderer_frame = False

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        publication = self._reader.read_latest()
        if publication is not None:
            image = np.frombuffer(publication.rgba, dtype=np.uint8).reshape(
                publication.height, publication.width, VIDEO_BYTES_PER_PIXEL
            )
            if publication.bottom_up:
                image = image[::-1]
            self._last_rgba = np.ascontiguousarray(image)
            rgb = self._last_rgba[:, :, :3]
            rgb_max = int(rgb.max())
            if not self._reported_renderer_frame and rgb_max > 0:
                LOGGER.info(
                    "Received first renderer video frame: width=%s height=%s rgb_min=%s rgb_max=%s",
                    publication.width,
                    publication.height,
                    int(rgb.min()),
                    rgb_max,
                )
                self._reported_renderer_frame = True

        frame = VideoFrame.from_ndarray(self._last_rgba, format="rgba")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class RendererAudioTrack(AudioStreamTrack):
    """Expose renderer PCM continuously, substituting silence when no current audio exists."""

    def __init__(self, reader: RendererAudioBufferReader) -> None:
        super().__init__()
        self._reader = reader
        self._sample_cursor = 0
        self._started_at: float | None = None
        self._reported_renderer_audio = False

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_running_loop()
        if self._started_at is None:
            self._started_at = loop.time()
        expected = self._started_at + self._sample_cursor / AUDIO_SAMPLE_RATE
        delay = expected - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)

        publication = self._reader.read_next()
        if publication is None:
            samples = np.zeros((1, AUDIO_SAMPLES_PER_BLOCK), dtype=np.int16)
        else:
            samples = np.frombuffer(publication.pcm_s16le, dtype="<i2").reshape(1, -1)
            if not self._reported_renderer_audio:
                LOGGER.info(
                    "Received first renderer audio block: sample_rate_hz=%s samples=%s peak=%s",
                    AUDIO_SAMPLE_RATE,
                    AUDIO_SAMPLES_PER_BLOCK,
                    int(np.abs(samples.astype(np.int32)).max()),
                )
                self._reported_renderer_audio = True

        frame = AudioFrame.from_ndarray(samples, format="s16", layout="mono")
        frame.sample_rate = AUDIO_SAMPLE_RATE
        frame.pts = self._sample_cursor
        frame.time_base = Fraction(1, AUDIO_SAMPLE_RATE)
        self._sample_cursor += AUDIO_SAMPLES_PER_BLOCK
        return frame


class RendererBridgeSource:
    """Own the named mappings and the aiortc tracks backed by them."""

    def __init__(self) -> None:
        self._video_mapping = _open_named_mapping(VIDEO_MAP_NAME, VIDEO_MAP_SIZE)
        try:
            self._audio_mapping = _open_named_mapping(AUDIO_MAP_NAME, AUDIO_MAP_SIZE)
        except Exception:
            self._video_mapping.close()
            raise
        self.video_reader = RendererVideoBufferReader(self._video_mapping)
        self.audio_reader = RendererAudioBufferReader(self._audio_mapping)
        self.video = RendererVideoTrack(self.video_reader)
        self.audio = RendererAudioTrack(self.audio_reader)

    def close(self) -> None:
        self.video_reader.close()
        self.audio_reader.close()
        self._video_mapping.close()
        self._audio_mapping.close()
