# ADR-0001: Modular monorepo with schema-first boundaries

- Status: accepted
- Date: 2026-10-08

## Context

The product spans Python, Kotlin, and C# and must evolve without requiring unrelated rebuilds.
Cross-process compatibility and safe handling of generated output are more important than sharing
one implementation language.

## Decision

Use a modular monorepo. Keep pure domain rules separate from frameworks, define JSON Schema 2020-12
wire contracts under `packages/contracts/schemas`, and maintain typed Python/Kotlin/C# bindings.
Version network and domain contracts explicitly. Use protocol `1.0` for the initial experiment and
integer microseconds as the canonical media time base.

## Consequences

There is some deliberate cross-language model duplication. Compatibility tests and fixtures are
required before changing schemas. Framework adapters translate at boundaries rather than leaking
SDK types into domain code.
