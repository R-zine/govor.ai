# ADR-0022: Semantic answer assessment with application-owned progression

- Status: accepted
- Date: 2026-11-03
- Amends: ADR-0006 and ADR-0008 answer assessment

## Context

The local dialogue model already returned a constrained `advance_exercise` boolean, but the
lesson service discarded it. `TeachingEngine` assessed every answer with literal phrase
patterns. The café's coffee patterns rejected “Hello, I'd like a cup of tea, please,” and analogous
failures affected imported/generated lessons. Extending keyword lists cannot cover natural
paraphrases or distinguish a relevant answer from negated or unrelated keyword-bearing text.

## Decision

Use the existing structured dialogue request to compare the transcript with the active exercise
question and communicative goal. The prompt accepts paraphrases, contractions, context-appropriate
short answers, and reasonable learner choices, while rejecting missing information, unrelated
answers, and instructions about grading. Vocabulary and example sentences are teaching support,
not a word checklist. History/learner text is untrusted conversation data. Request the verdict
before feedback and parse `advance_exercise` as a strict JSON boolean; extra fields and string or
number coercions are rejected. Local dialogue uses greedy sampling (`temperature=0`) for the
assessment rather than creative variation. This reuses one inference call and the existing
contract shape.

`LocalLessonService` passes the policy-filtered verdict to `TeachingEngine.evaluate` as the optional
`answer_accepted` input. True and false both replace literal matching; false is never retried
against keywords. On a provider error, timeout, or malformed response, the input is `None` and the
existing limited matcher supports deterministic scripted operation. Fake mode remains explicit
and uses that matcher. No extra provider, cloud call, dependency, or transcript persistence is added.

The engine still rejects non-English/help turns, maintains attempts and persisted counters,
advances exactly one exercise, chooses the next prompt/correction, determines completion, and
changes difficulty under its existing rules. The model cannot supply an exercise index or action.
Generated/imported lessons use their own current question/goal through this same path.

## Consequences and verification

This is semantic transcript assessment, not pronunciation scoring. Recognition mistakes and model
misjudgments remain possible. The fallback retains its narrower literal limitations. Application
control is bounded even if a model incorrectly accepts an answer; prompt-injection resistance is
tested but is not claimed to be perfect.

Domain/service regressions cover the reported tea order, negative verdicts overriding keyword
matches, unavailable/invalid-model fallback, persistence, and help/language non-advancement.
Provider tests reject coerced booleans. The reproducible real-model fixture set is
`tests/fixtures/ai/answer-assessment-cases.json`, executed through `scripts/local_ai_benchmark.py`
against pinned loopback Qwen3/llama.cpp with the actual engine. Benchmark evidence and exact
commands are recorded in `docs/benchmarks/2026-11-03-semantic-answer-assessment.md` and `STATUS.md`.
