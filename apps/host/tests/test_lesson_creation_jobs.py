import asyncio
from uuid import uuid4

import pytest
from govor_contracts import LessonCreateRequestPayload, LessonCreateResultPayload
from govor_host.lesson_creation_jobs import LessonCreationJobs


@pytest.mark.asyncio
async def test_jobs_are_idempotent_private_bounded_and_timed_out() -> None:
    calls = 0
    updates = []

    async def creator(_: LessonCreateRequestPayload) -> LessonCreateResultPayload:
        nonlocal calls
        calls += 1
        await asyncio.sleep(60)
        raise AssertionError("should time out")

    async def changed() -> None:
        updates.append(jobs.display.state)

    jobs = LessonCreationJobs(creator, changed, timeout_seconds=0.02)
    request = LessonCreateRequestPayload(topic="Travel")
    job_id = uuid4()
    await jobs.start("phone-a", job_id, request)
    await jobs.start("phone-a", job_id, request)
    assert jobs.status("phone-b").state == "idle"
    with pytest.raises(ValueError):
        await jobs.start("phone-b", uuid4(), request)
    await asyncio.sleep(0.05)
    assert jobs.status("phone-a").state == "failed"
    assert "timed out" in jobs.status("phone-a").message
    assert calls == 1 and updates == ["generating", "failed"]
    await jobs.close()
