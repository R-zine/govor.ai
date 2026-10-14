# ADR-0010: Opt-in cloud providers and protected credentials

- Status: accepted
- Date: 2026-10-14
- Milestone: 7

## Context

The product must remain useful fully offline while allowing a learner to choose cloud dialogue,
recognition, or speech independently. A provider key must not become ordinary configuration, and
choosing cloud text generation must not implicitly upload microphone audio. OpenAI-compatible APIs
are common but differ in supported models, response schemas, audio formats, and retention policy.

## Decision

Keep `offline_only=true` and all subsystem selectors local by default. Reject cloud configuration
under that default and also enforce a per-request outbound policy before credential retrieval or
network access. Require separate explicit consent for cloud microphone upload.

Add `services/provider_router` to compose recognition, dialogue, and speech independently. Provide
bounded OpenAI-compatible adapters for `/chat/completions`, `/audio/transcriptions`, and
`/audio/speech`. Reuse one closed structured-dialogue codec across local and cloud adapters.
Represent missing word/phoneme timing as null. Report locality and privacy-relevant limitations in
provider capabilities. Stream successful responses through 64 KiB JSON and 1.5 MiB WAV limits.

Store keys as current-user generic credentials in Windows Credential Manager. Configuration holds
only a validated credential target. Fetch the secret immediately before a request; never pass it
through Android, settings, environment variables, command arguments, health output, or logs.
Credential management reads new values from an interactive secure prompt and standard input.

## Consequences

- Local-only operation has no credential prerequisite and cannot make a cloud request.
- Text, recognition, and speech can be mixed independently.
- Cloud recognition has a conspicuous second consent because it exports raw microphone audio.
- Authentication, rate-limit, timeout, transport, and malformed-output failures are typed and
  handled by the existing recoverable session/fallback behavior; response bodies are not logged.
- Compatibility is best effort: strict JSON schema and WAV support must be supplied by the chosen
  endpoint. No provider-specific SDK or new dependency is added.
- The application retains no cloud recordings, but third-party retention is outside its control
  and must be disclosed and reviewed by the learner before opt-in.

## Rejected

- A single global local/cloud mode: it prevents useful mixed configurations and makes microphone
  upload too easy to enable accidentally.
- API keys in `.env`, settings, launcher arguments, or Android storage: these are unnecessarily
  exposed to logs, process inspection, backups, or the LAN client.
- Implicit cloud fallback from local failure: it violates meaningful opt-in and the offline gate.
- Invented timing for cloud speech: it violates the actual-or-null media-time contract.
