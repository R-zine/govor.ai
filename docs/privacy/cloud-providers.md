# Optional cloud providers and privacy

govor.ai is local-only by default. `offline_only=true`, and recognition, dialogue, and speech each
default to `local`. Cloud traffic requires an explicit provider selection and
`offline_only=false`; cloud recognition also requires `allow_cloud_microphone_upload=true`. The
runtime gate is checked before credential lookup and before HTTP, so re-enabling offline mode
prevents an already-created adapter from sending a request.

## What leaves the PC

Only the selected subsystem sends its required payload:

| Selection | Data sent to the configured HTTPS provider |
| --- | --- |
| Cloud dialogue | Recognized learner text, current lesson prompt/objective/vocabulary, intent hint, and bounded recent conversation history |
| Cloud recognition | One bounded in-memory utterance WAV plus model/response-format fields |
| Cloud speech | Teacher response text, voice/model choice, and playback speed |

The application does not request provider-side recording, does not persist cloud audio, and does
not add telemetry. It cannot control a third party's service logs, abuse monitoring, training, or
retention. Review the chosen provider's terms and deletion controls before opting in. Selecting
only one cloud subsystem does not send data required exclusively by the other two.

## Credentials

Secrets are stored under `govor.ai/provider/<target>` in the current Windows user's Credential
Manager. Configuration and health output contain only the safe target name. Manage a credential
interactively so it never appears in a command argument or environment variable:

```powershell
./scripts/provider-credentials.ps1 -Action Set -Target openai-dialogue
./scripts/provider-credentials.ps1 -Action Status -Target openai-dialogue
./scripts/provider-credentials.ps1 -Action Delete -Target openai-dialogue
```

Never put a key in `.env`, a `GOVOR_` variable, a script argument, Android settings, or a log.

## Opt-in configuration

Non-secret provider configuration uses the `GOVOR_` settings prefix. For example, choosing only
cloud dialogue leaves microphone recognition and speech synthesis local:

```powershell
$env:GOVOR_OFFLINE_ONLY = 'false'
$env:GOVOR_DIALOGUE_PROVIDER = 'cloud'
$env:GOVOR_CLOUD_DIALOGUE_BASE_URL = 'https://provider.example/v1'
$env:GOVOR_CLOUD_DIALOGUE_MODEL = 'compatible-model-id'
$env:GOVOR_CLOUD_DIALOGUE_CREDENTIAL_TARGET = 'openai-dialogue'
./scripts/dev.ps1 -Mode local -AllowCloud -DialogueProvider cloud -PairingToken '<at-least-32-random-characters>'
```

Cloud recognition requires both `-RecognitionProvider cloud` and
`-AllowCloudMicrophoneUpload`. The adapters target OpenAI-compatible endpoint shapes, but provider
support for strict JSON schema and WAV output varies; unsupported or malformed results fail safely.

## Local deletion

`./scripts/progress.ps1 -Action Delete -ConfirmDelete` removes structured history while preserving
settings. `./scripts/progress.ps1 -Action DeleteAll -ConfirmDelete` removes all structured learner
history and restores learner settings to product defaults. Delete provider credentials separately
with the credential command above. Complete deletion uses SQLite secure deletion plus compaction.
These local actions cannot delete data a third party may have
retained; use that provider's deletion mechanism as well.
