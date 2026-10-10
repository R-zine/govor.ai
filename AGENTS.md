# Agent operating guide

`docs/MASTER_SPEC.md` is the authoritative product brief. This repository is evidence-driven:
never infer that compilation, mocks, emulators, or generated artifacts prove physical-device,
GPU, audio, or network behavior.

## Start every session

Read, in order:

1. `docs/MASTER_SPEC.md` (in full).
2. This file.
3. `docs/milestones/ROADMAP.md` and `docs/milestones/STATUS.md`.
4. `docs/architecture/overview.md`, `data-flow.md`, and `security.md`.
5. Relevant files under `docs/decisions`, `docs/contracts`, and tests.

Inspect `git status` before editing. This checkout may report dubious ownership in managed
environments; use the command-scoped form below rather than changing global Git configuration:

```powershell
git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' status --short --branch
```

Preserve unrelated user changes. Never use destructive Git commands. Do not commit incomplete
work unless the user explicitly asks. A completed milestone must be committed as described under
Milestone handoff.

## Engineering rules

- Work milestone by milestone and update `STATUS.md` after every meaningful verification run.
- The active renderer is Godot 4.7.2 .NET under `apps/renderer`; Unity is not part of the stack.
- Milestone 1 is complete on the native-emulator development proof. Physical phone, Wi-Fi,
  hardware-codec, acoustic, target-machine performance, monitor-off, and soak acceptance is one
  mandatory Milestone 9 release bundle; do not use its absence to block Milestones 2-8.
- Keep the domain independent of FastAPI, Android, Godot, and provider implementations.
- Put versioned wire contracts in `packages/contracts/schemas`; validate untrusted messages at
  process boundaries.
- Every wire envelope has `protocol_version`, `message_type`, `correlation_id`, and `payload`.
- Use integer microseconds from media start as the canonical media time base.
- Provider capabilities are explicit. Unavailable word/phoneme timing is `null`, never invented.
- Production adapters and fakes have unmistakable names. Fakes are allowed for deterministic
  development and tests, never as evidence that production providers work.
- Local inference services bind to loopback. A LAN-facing gateway requires pairing,
  authentication, payload limits, timeouts, and secure transport before release use.
- Do not log secrets, raw microphone audio, or full learner transcripts by default.
- Do not add cloud calls, telemetry, accounts, or paid services by default.
- Pin dependencies and update `THIRD_PARTY_LICENSES.md` when adding one.

## Commands

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer
./scripts/test.ps1 -Scope python
./scripts/test.ps1 -Scope contracts
./scripts/test.ps1 -Scope kotlin
./scripts/test.ps1 -Scope csharp
./scripts/test.ps1 -Scope media
./scripts/test.ps1 -Scope godot
./scripts/test.ps1 -Scope all
./scripts/dev.ps1 -Mode mock
./scripts/media-dev.ps1 -PairingToken '<at-least-32-random-characters>' -AllowInsecureDevLan
```

Hardware tests are separate:

```powershell
./scripts/test.ps1 -Scope hardware
./scripts/benchmark.ps1 -Profile media-poc
```

Record the machine, device, network, exact command, timestamp, result, and artifacts in
`docs/testing/hardware-tests.md` and `docs/benchmarks/`. If suitable hardware is absent, mark the
test **blocked** or **not executed**; never report simulated values as measurements.

The media development server and debug APK deliberately permit cleartext signaling only for the
trusted-LAN feasibility test. They are not release-safe. Do not weaken the release manifest or
describe the pre-shared development token as production pairing.

## Milestone handoff

For each milestone, record implementation, decisions, files changed, commands executed, results,
acceptance criteria (verified passing / verified failing / not executed / blocked / not yet
implemented), blockers, and exact next commands in `docs/milestones/STATUS.md`. Update the roadmap
and ADRs at the same time. Continue only when prerequisites are genuinely satisfied. Never infer
Milestone 9 physical-hardware acceptance from Milestone 1 emulator evidence.

After every milestone is genuinely complete and its handoff documentation is current, create one
focused milestone commit. Exclude unrelated user changes. If milestone changes cannot be separated
safely from unrelated work, stop and ask rather than committing unrelated files.
