"""Bounded host-owned creation jobs which survive phone socket/lifecycle teardown."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from govor_contracts import (
    LessonCreateRequestPayload,
    LessonCreateResultPayload,
    LessonCreationStatusPayload,
)

Creator = Callable[[LessonCreateRequestPayload], Awaitable[LessonCreateResultPayload]]
LOGGER = logging.getLogger("uvicorn.error")


class LessonCreationJobs:
    def __init__(
        self,
        creator: Creator | None,
        changed: Callable[[], Awaitable[None]],
        *,
        timeout_seconds: float = 270.0,
    ) -> None:
        self._creator = creator
        self._changed = changed
        self._timeout = timeout_seconds
        self._statuses: dict[str, LessonCreationStatusPayload] = {}
        self._task: asyncio.Task[None] | None = None
        self.display = self.status("unused")

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self, owner: str) -> LessonCreationStatusPayload:
        return self._statuses.get(
            owner,
            LessonCreationStatusPayload(
                state="idle", message="No lesson creation is running on this host."
            ),
        )

    async def start(self, owner: str, job_id: UUID, payload: LessonCreateRequestPayload) -> None:
        previous = self._statuses.get(owner)
        if previous is not None and (
            previous.job_id == job_id or (previous.state == "generating" and self.busy)
        ):
            return
        if self.busy:
            raise ValueError("the host is already creating a lesson")
        if len(self._statuses) >= 16 and owner not in self._statuses:
            self._statuses.pop(next(iter(self._statuses)))
        status = LessonCreationStatusPayload(
            job_id=job_id,
            state="generating",
            message=(
                "Creating lesson on your PC. You can lock the phone; "
                "progress returns when you reconnect."
            ),
        )
        self._statuses[owner] = self.display = status
        self._task = asyncio.create_task(self._run(owner, job_id, payload))

    async def _run(self, owner: str, job_id: UUID, payload: LessonCreateRequestPayload) -> None:
        try:
            await self._changed()
            if self._creator is None:
                result = LessonCreateResultPayload(
                    status="failed", message="Lesson creation is unavailable in this host mode."
                )
            else:
                async with asyncio.timeout(self._timeout):
                    result = await self._creator(payload)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            LOGGER.warning("lesson creation failed error_type=%s", type(error).__name__)
            result = LessonCreateResultPayload(
                status="failed",
                message=(
                    "Lesson creation timed out. Please try a shorter lesson."
                    if isinstance(error, TimeoutError)
                    else "The local lesson model could not create a valid lesson. Please try again."
                ),
            )
        self._statuses[owner] = self.display = LessonCreationStatusPayload(
            job_id=job_id, state=result.status, message=result.message, result=result
        )
        await self._changed()

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
