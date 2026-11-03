# ADR-0006: Loopback local AI with deterministic bilingual policy

- Status: accepted
- Date: 2026-10-11
- Milestone: 3

ADR-0022 later connects the validated dialogue boolean to semantic answer assessment while
preserving the deterministic help/language and progression guards described here.

## Context

Milestone 3 replaces scripted recognition and dialogue with local inference while keeping provider
implementations out of the domain. The application needs English, Bulgarian, and mixed-language
behavior; constrained output; bounded memory; predictable failure recovery; and no cloud or
transcript retention. Model output cannot be trusted to decide application control or teaching
progress by itself.

The target development PC has an NVIDIA GeForce RTX 3060 with 12,288 MiB VRAM and 32 GiB RAM. The
model must coexist later with Godot and the media encoder. Two Apache-2.0 Qwen3 Q4_K_M candidates
were therefore tested with the same prompt, seed, closed schema, and seven bilingual fixtures:
4B (2,497,280,256 bytes) and 1.7B (1,107,408,544 bytes).

## Decision

Use the pinned llama.cpp b11540 Windows Vulkan server on loopback with Qwen3 4B Q4_K_M as the
default dialogue model. Use pinned whisper.cpp b5454 CPU with the multilingual small model for
recognition. Both runtime URLs are loopback-only, dependencies and weights are checksum-pinned,
and no network call is made after initial artifact download.

The selected model, provider identity, context size, and GPU-layer count are launcher configuration,
not domain constants. An alternate GGUF can be evaluated without changing lesson policy, but its
provider ID must be explicit and it cannot become the default without a new evidence record.

Qwen3 4B is selected over 1.7B even though the smaller candidate used less memory and had a lower
warm median in this narrow run. Both passed 7/7 fixture outcomes, but the 4B candidate needed a
deterministic policy correction in one case versus three for 1.7B. The 4B process used about
2.71 GB working set and the measured GPU allocation increase was about 3.10 GiB, leaving substantial
headroom on the 12 GiB development GPU. This is a product-specific selection, not a general model
quality claim. Revisit it if representative lesson evaluation or Milestone 9 coexistence evidence
favors the smaller model.

Keep recognition, dialogue, and speech behind `packages/provider_interfaces`. Keep lesson context,
conservative language detection, explicit high-confidence help intents, progress invariants, and
bounded session history in `packages/domain`. History is compressed as a configurable sliding
window (eight turns by default, maximum 32); no transcript memory is persisted.

Generation supplies llama.cpp with a strict JSON schema and independently parses the reply with
unknown fields forbidden. The domain policy then enforces locale and progress. Bulgarian
clarification/reformulation/vocabulary help cannot advance the exercise, and repeat, slower speech,
ambiguity, or recognition failure cannot count as an English answer. Transient timeouts and server
failures receive one bounded retry; malformed/resource-exhausted output falls immediately to a
deterministic scripted response. Valid no-speech recognition produces a Bulgarian repeat request
without fabricating a transcript.

The media service owns one bounded in-memory microphone capture. It resamples incoming WebRTC
frames to mono 16 kHz signed PCM and exposes start/finish/cancel only through a loopback internal
HTTP endpoint. whisper.cpp input/output files are ephemeral and removed in a `finally` path.

Milestone 3 retains a 150 ms, clearly identified diagnostic tone so the completed text turn can
still traverse the existing Android audio contract. It is not TTS evidence. English/Bulgarian
voices, fallback speech, alignment, speed, and replay belong to Milestone 4.

## Rejected

- Treating the model's classification/progress flag as authoritative: pedagogical behavior would
  vary with sampling and malformed/injected output could cross control boundaries.
- Selecting Qwen3 1.7B solely for its lower memory and median: it required more policy corrections
  in the current fixture set; the 4B model fits the measured development machine.
- Sending raw microphone bytes through the control WebSocket: this duplicates the established
  WebRTC media path and expands transcript/audio exposure.
- Binding model or capture services to the LAN: neither needs a phone-facing listener.
- Calling the diagnostic tone speech synthesis: Milestone 4 has not run.

## Evidence and limits

`./scripts/benchmark.ps1 -Profile local-ai` ran both model candidates, two human-speech fixtures,
and a real local-provider turn sequence through host orchestration. The selected 4B model passed
7/7 English/Bulgarian/mixed cases with 1,002.8 ms median and 2,883.6 ms maximum dialogue latency.
The 1.7B candidate passed 7/7 with 688.5 ms median and 2,639.7 ms maximum. The recognizer correctly
classified English and Bulgarian and found the asserted words, but the Bulgarian transcript had
word errors and is not evidence of production accuracy. Detailed measurements and fixture
provenance are in `docs/benchmarks/2026-10-11-local-ai-bilingual.md`.

The benchmark is a bounded development-machine sample, not a broad language-quality study. It did
not cover live hesitant speech, Bulgarian-accented English, acoustics, physical Android hardware,
Wi-Fi, simultaneous final rendering/encoding load, thermals, or bounded stability. Those deficits
informed the separately executed Milestone 9 target-hardware bundle, which later passed; they do
not turn these emulator/software results into physical evidence.
