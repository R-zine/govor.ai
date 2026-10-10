"""Bounded live probe for the Windows renderer shared-memory handoff."""

from __future__ import annotations

import hashlib
import json
import time

from govor_media.renderer_bridge import RendererBridgeSource


def main() -> None:
    deadline = time.monotonic() + 5.0
    video_hashes: set[bytes] = set()
    video_frames = 0
    video_rgb_max = 0
    audio_blocks = 0
    audio_peak = 0
    source = RendererBridgeSource()
    try:
        while time.monotonic() < deadline:
            video = source.video_reader.read_latest()
            if video is not None:
                video_frames += 1
                video_hashes.add(hashlib.sha256(video.rgba).digest())
                video_rgb_max = max(
                    video_rgb_max,
                    max(video.rgba[0::4]),
                    max(video.rgba[1::4]),
                    max(video.rgba[2::4]),
                )

            audio = source.audio_reader.read_next()
            if audio is not None:
                audio_blocks += 1
                samples = memoryview(audio.pcm_s16le).cast("h")
                audio_peak = max(audio_peak, max(abs(sample) for sample in samples))

            if (
                video_frames >= 5
                and len(video_hashes) >= 2
                and video_rgb_max > 0
                and audio_blocks >= 5
                and audio_peak > 0
            ):
                break
            time.sleep(0.005)
    finally:
        source.close()

    result = {
        "video_frames": video_frames,
        "distinct_video_frames": len(video_hashes),
        "video_rgb_max": video_rgb_max,
        "audio_blocks": audio_blocks,
        "audio_peak": audio_peak,
    }
    print(json.dumps(result, sort_keys=True))
    if video_frames < 5:
        raise RuntimeError("renderer probe received fewer than five complete video frames")
    if len(video_hashes) < 2:
        raise RuntimeError("renderer probe did not observe animation between video frames")
    if video_rgb_max == 0:
        raise RuntimeError("renderer probe received only black video frames")
    if audio_blocks < 5 or audio_peak == 0:
        raise RuntimeError("renderer probe did not receive non-silent application PCM")


if __name__ == "__main__":
    main()
