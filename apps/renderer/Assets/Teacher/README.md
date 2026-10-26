# Teacher profiles

The renderer ships three selectable, high-detail teacher profiles: Elena, Amira, and Daniel.
They share a real facial rig with 34 blend shapes and 14 speech visemes. Selection is available in
the host pairing screen's **Teacher** menu, is persisted locally, and is sent to the loopback host
through the closed `renderer.teacher_profile_selected` contract.

The host resolves the profile at synthesis time. Elena uses Kokoro `bf_emma`/`af_heart`, Amira
uses `bf_isabella`/`af_bella`, and Daniel uses `bm_george`/`am_michael` for British/American
English respectively. Bulgarian has only the bundled male Piper Dimitar voice: Daniel uses it,
while Elena and Amira use the local eSpeak NG `f3` female variant. Cloud-compatible presentation
voices are independently configurable and default to `coral`, `nova`, and `onyx`; provider voice
names are presentation settings rather than a provider guarantee about speaker identity.

See `Ara/README.md` for provenance, licenses, reproducible profile inputs, asset checksums, and the
animation-stripping build step.
