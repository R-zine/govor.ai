from __future__ import annotations

import json
import math
import struct
import wave
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from govor_scene_planner import (
    ALLOWED_ASSET_IDS,
    SceneObject,
    ScenePlanner,
    SceneSpecification,
    TimedPhoneme,
    build_avatar_animation,
    import_environment_bundle,
)

ROOT = Path(__file__).resolve().parents[3]
ENVIRONMENT_FIXTURE = ROOT / "tests/fixtures/contracts/valid/environment-hotel-lobby.json"


def _wav(samples: list[int], sample_rate: int = 16_000) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return output.getvalue()


def test_all_scene_templates_are_distinct_and_validated() -> None:
    planner = ScenePlanner()
    scenes = [planner.plan(template_id) for template_id in planner.supported_templates]

    assert planner.supported_templates == ("cafe", "supermarket", "airport", "home")
    assert {scene.environment_id for scene in scenes} == {
        "cafe",
        "supermarket",
        "airport",
        "home",
    }
    assert len({scene.scene_id for scene in scenes}) == 4
    assert all(len(scene.objects) >= 4 for scene in scenes)
    assert all(item.asset_id in ALLOWED_ASSET_IDS for scene in scenes for item in scene.objects)


def test_unknown_template_and_asset_are_rejected() -> None:
    with pytest.raises(ValueError, match="not allow-listed"):
        ScenePlanner().plan("model-selected-path")
    with pytest.raises(ValueError, match="allow-listed"):
        SceneObject("unsafe", "../../arbitrary.glb", (0.0, 0.0, 0.0))


def test_custom_environment_catalog_loads_validated_primitives(tmp_path) -> None:
    (tmp_path / "hotel-lobby.json").write_bytes(ENVIRONMENT_FIXTURE.read_bytes())

    planner = ScenePlanner(tmp_path)
    scene = planner.plan("hotel-lobby")

    assert planner.environment_choices[-1] == ("hotel-lobby", "Hotel lobby")
    assert scene.objects[0].asset_id is None
    assert scene.objects[0].primitive is not None
    assert scene.objects[0].primitive.shape == "box"


def test_environment_bundle_import_is_additive_and_canonical(tmp_path) -> None:
    source = tmp_path / "environments.zip"
    destination = tmp_path / "installed"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("hotel/environment.json", ENVIRONMENT_FIXTURE.read_bytes())

    imported = import_environment_bundle(source, destination)

    assert [item.environment_id for item in imported] == ["hotel-lobby"]
    installed = json.loads((destination / "hotel-lobby.json").read_text(encoding="utf-8"))
    assert installed["display_name"] == "Hotel lobby"
    assert ScenePlanner(destination).plan("hotel-lobby").scene_id == "hotel-lobby-v1"


@pytest.mark.parametrize(
    ("member_name", "content"),
    [
        ("../escape.json", ENVIRONMENT_FIXTURE.read_bytes()),
        ("plugin.dll", b"not code"),
    ],
)
def test_environment_bundle_rejects_unsafe_or_non_json_entries(
    tmp_path, member_name: str, content: bytes
) -> None:
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(member_name, content)

    with pytest.raises(ValueError):
        import_environment_bundle(source, tmp_path / "installed")


def test_environment_bundle_rejects_built_in_collision_without_partial_install(tmp_path) -> None:
    definition = json.loads(ENVIRONMENT_FIXTURE.read_text(encoding="utf-8"))
    definition["environment_id"] = "cafe"
    source = tmp_path / "collision.zip"
    destination = tmp_path / "installed"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("collision.json", json.dumps(definition))

    with pytest.raises(ValueError, match="already exists"):
        import_environment_bundle(source, destination)
    assert not tuple(destination.glob("*.json"))


def test_environment_import_requires_an_existing_zip(tmp_path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        import_environment_bundle(tmp_path / "missing.zip", tmp_path / "installed")
    source = tmp_path / "environment.json"
    source.write_bytes(ENVIRONMENT_FIXTURE.read_bytes())
    with pytest.raises(ValueError, match="zip"):
        import_environment_bundle(source, tmp_path / "installed")


def test_environment_bundle_rejects_duplicate_environment_ids(tmp_path) -> None:
    source = tmp_path / "duplicates.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("one.json", ENVIRONMENT_FIXTURE.read_bytes())
        archive.writestr("two.json", ENVIRONMENT_FIXTURE.read_bytes())

    with pytest.raises(ValueError, match="duplicate environment"):
        import_environment_bundle(source, tmp_path / "installed")


def test_duplicate_instances_and_out_of_range_transforms_are_rejected() -> None:
    item = SceneObject("same", "cafe-cup", (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="unique"):
        SceneSpecification(
            "invalid",
            "cafe",
            "counter",
            "warm",
            "fade",
            (0.0, 0.0, 0.0),
            0.0,
            (item, item),
        )
    with pytest.raises(ValueError, match="position"):
        SceneObject("far", "cafe-cup", (21.0, 0.0, 0.0))


def test_pcm_energy_and_real_phoneme_timing_drive_avatar_animation() -> None:
    samples = [
        round(math.sin(index / 11) * (1_000 if index < 800 else 8_000)) for index in range(1_600)
    ]
    animation = build_avatar_animation(
        _wav(samples),
        100_000,
        (
            TimedPhoneme("m", 0, 25_000),
            TimedPhoneme("a", 25_000, 55_000),
            TimedPhoneme("u", 55_000, 100_000),
        ),
    )

    assert animation.viseme_source == "provider_phoneme_alignment"
    assert [cue.viseme for cue in animation.visemes] == ["closed", "open", "round"]
    assert [(cue.start_us, cue.end_us) for cue in animation.visemes] == [
        (0, 25_000),
        (25_000, 55_000),
        (55_000, 100_000),
    ]
    assert animation.speech_energy[-1].level_milli > animation.speech_energy[0].level_milli
    assert max(sample.level_milli for sample in animation.speech_energy) == 1_000


def test_missing_phoneme_alignment_uses_energy_without_inventing_visemes() -> None:
    animation = build_avatar_animation(_wav([500] * 800), 50_000, None)

    assert animation.viseme_source == "none"
    assert animation.visemes == ()
    assert animation.speech_energy


def test_invalid_wav_and_alignment_are_rejected() -> None:
    with pytest.raises(ValueError, match="valid WAV"):
        build_avatar_animation(b"not-wav", 100_000, None)
    with pytest.raises(ValueError, match="exceeds"):
        build_avatar_animation(
            _wav([0] * 1_600),
            100_000,
            (TimedPhoneme("a", 0, 100_001),),
        )
