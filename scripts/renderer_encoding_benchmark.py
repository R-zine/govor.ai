"""Measure software VP8 encode cost for live Godot shared-memory frames."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from govor_media.renderer_bridge import RendererBridgeSource


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def run(frame_target: int) -> dict[str, object]:
    codec = av.CodecContext.create("libvpx", "w")
    codec.width = 1280
    codec.height = 720
    codec.pix_fmt = "yuv420p"
    codec.time_base = Fraction(1, 30)
    codec.framerate = Fraction(30, 1)
    codec.bit_rate = 1_500_000
    codec.options = {"deadline": "realtime", "cpu-used": "8"}
    codec.open()

    source = RendererBridgeSource()
    encoded_times_ms: list[float] = []
    packet_count = 0
    deadline = time.monotonic() + 8.0
    try:
        while len(encoded_times_ms) < frame_target and time.monotonic() < deadline:
            frame = source.video_reader.read_latest()
            if frame is None:
                time.sleep(0.002)
                continue
            rgba = np.frombuffer(frame.rgba, dtype=np.uint8).reshape((720, 1280, 4))
            video_frame = av.VideoFrame.from_ndarray(rgba, format="rgba")
            video_frame.pts = len(encoded_times_ms)
            started = time.perf_counter_ns()
            packets = codec.encode(video_frame)
            encoded_times_ms.append((time.perf_counter_ns() - started) / 1_000_000)
            packet_count += len(packets)
        packet_count += len(codec.encode(None))
    finally:
        source.close()

    if len(encoded_times_ms) < frame_target:
        raise RuntimeError(f"renderer ended before {frame_target} distinct frames could be encoded")
    return {
        "codec": "libvpx-vp8-software",
        "hardware_encoding": False,
        "resolution": "1280x720",
        "frame_count": len(encoded_times_ms),
        "packet_count": packet_count,
        "encode_ms_mean": statistics.fmean(encoded_times_ms),
        "encode_ms_p50": _percentile(encoded_times_ms, 0.50),
        "encode_ms_p95": _percentile(encoded_times_ms, 0.95),
        "encode_ms_max": max(encoded_times_ms),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=20)
    arguments = parser.parse_args()
    if not 5 <= arguments.frames <= 120:
        raise ValueError("frame count must be between 5 and 120")
    result = run(arguments.frames)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
