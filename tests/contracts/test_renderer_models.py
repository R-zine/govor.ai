from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from govor_contracts import (
    AvatarAnimationPayload,
    PrimitivePayload,
    RendererCommandPayload,
    RendererTeacherProfileSelectedPayload,
    SceneObjectPayload,
    SceneSpecificationPayload,
    SpeechEnergySamplePayload,
    Vector3Payload,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_shared_renderer_fixture_validates_scene_animation_model() -> None:
    fixture = json.loads(
        (ROOT / "tests/fixtures/contracts/valid/control-renderer-command.json").read_text(
            encoding="utf-8"
        )
    )

    command = RendererCommandPayload.model_validate(fixture["payload"])

    assert command.avatar_animation is not None
    assert command.avatar_animation.visemes[0].viseme == "closed"


def test_teacher_profile_selection_is_closed() -> None:
    assert RendererTeacherProfileSelectedPayload(profile_id="amira").profile_id == "amira"
    with pytest.raises(ValidationError):
        RendererTeacherProfileSelectedPayload(profile_id="../../arbitrary")  # type: ignore[arg-type]


def test_shared_custom_scene_fixture_validates_primitive_model() -> None:
    fixture = json.loads(
        (ROOT / "tests/fixtures/contracts/valid/control-custom-scene.json").read_text(
            encoding="utf-8"
        )
    )

    command = RendererCommandPayload.model_validate(fixture["payload"])

    assert command.scene is not None
    assert command.scene.environment_id == "hotel-lobby"
    assert command.scene.objects[0].primitive is not None
    assert command.scene.objects[0].primitive.shape == "box"


def test_scene_rejects_arbitrary_asset_and_duplicate_instances() -> None:
    position = Vector3Payload(x=0, y=0, z=0)
    with pytest.raises(ValidationError):
        SceneObjectPayload(
            instance_id="unsafe-object",
            asset_id="../../arbitrary.glb",  # type: ignore[arg-type]
            position=position,
            yaw_degrees=0,
            scale=1,
        )

    primitive = PrimitivePayload(
        shape="box",
        size=Vector3Payload(x=4, y=1, z=0.8),
        color="#70452A",
    )
    custom = SceneObjectPayload(
        instance_id="front-desk",
        primitive=primitive,
        position=position,
        yaw_degrees=0,
        scale=1,
    )
    assert custom.asset_id is None
    with pytest.raises(ValidationError, match="exactly one"):
        SceneObjectPayload(
            instance_id="ambiguous",
            asset_id="cafe-cup",
            primitive=primitive,
            position=position,
            yaw_degrees=0,
            scale=1,
        )

    item = SceneObjectPayload(
        instance_id="same-object",
        asset_id="cafe-cup",
        position=position,
        yaw_degrees=0,
        scale=1,
    )
    with pytest.raises(ValidationError, match="unique"):
        SceneSpecificationPayload(
            scene_id="duplicate-scene",
            environment_id="cafe",
            camera_preset="counter",
            lighting_preset="warm",
            transition="fade",
            avatar_position=position,
            avatar_yaw_degrees=0,
            objects=[item, item],
        )


def test_avatar_timeline_requires_matching_teacher_command_duration() -> None:
    animation = AvatarAnimationPayload(
        duration_us=100_000,
        gesture="speaking",
        expression="encouraging",
        viseme_source="none",
        speech_energy=[SpeechEnergySamplePayload(media_time_us=0, level_milli=100)],
        visemes=[],
    )

    with pytest.raises(ValidationError, match="duration"):
        RendererCommandPayload(
            session_id=uuid4(),
            command_id=uuid4(),
            action="teacher_speaking",
            media_start_us=0,
            duration_us=120_000,
            avatar_animation=animation,
        )
