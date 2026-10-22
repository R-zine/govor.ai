# Windows installation and use

The Milestone 8 distribution is a portable Windows x64 archive. It contains the exported Godot
player and its own Python/local-AI runtimes; do not install Python, Godot, Gradle, or Android Studio
to use it.

This package has passed development-machine, clean-Windows VM, Android-emulator, and physical
target checks. The VM result still applies only to the exact recorded image and does not establish
target-PC or physical-phone behavior; that separate physical evidence comes from the completed
Milestone 9 run on the documented target PC, realme RMX3939, and intended private Wi-Fi.

Do not use the obsolete 0.1.1 candidate: its Windows command wrappers cannot pass the launcher
subcommand. Use 0.1.2 or later, verify its digest, and extract it into a new directory.

## First-time setup

1. Verify the ZIP and APK SHA-256 values against the supplied artifact manifest.
2. Extract the whole `govor.ai-<version>-windows-x64.zip` into a user-writable directory. Do not run
   from inside the ZIP and do not place it under a system-managed directory if your account cannot
   write there.
3. Run `Setup-Govor.cmd`. If the Microsoft Visual C++ runtime required by the packaged local-AI
   executable is absent, accept the Windows administrator prompt. Setup downloads Microsoft's
   versioned x64 redistributable directly, verifies its pinned SHA-256 and Microsoft signature, and
   installs it before continuing.
4. Setup downloads approximately 3.4 GB of dialogue, recognition, and speech model data. Leave the
   PC connected to the internet until every model reports a verified SHA-256 digest.
   Partial or mismatched files are never promoted into the model directory.
5. Disconnect from the internet if desired. Normal local lessons use no cloud service.

Models, learner progress, security state, and logs are stored under `%LOCALAPPDATA%\govor.ai`, not
inside the extracted version directory.

## Start, pair, and stop

1. Put the PC and phone on the same trusted private network.
2. Run `Start-Govor.cmd`.
3. If Windows Firewall prompts, allow the packaged Python runtime on private networks only. The
   phone needs TCP ports 8765 and 8766; local inference remains bound to loopback.
4. Keep the console open. It shows the PC address, control/media ports, certificate SHA-256
   fingerprint, model/service status, and a one-time eight-digit code valid for ten minutes.
5. Follow the Android guide. Compare/copy the complete 64-hex-character fingerprint; do not accept
   a fingerprint supplied by an unexpected device or network page.
6. To stop govor.ai, return to the console and press Enter. Wait for the message confirming that
   managed child processes closed before moving or updating the directory.

The pairing code is single use. A successfully paired Android installation keeps a random device
credential and normally needs only the same PC address/ports on later starts.

## Update

1. Stop the old launcher completely.
2. Verify and extract the new ZIP into a new versioned directory rather than mixing files from two
   versions.
3. Run the new `Setup-Govor.cmd`. Already present models are rechecked and are not downloaded again
   when their size and SHA-256 still match.
4. Run the new `Start-Govor.cmd`.

The `%LOCALAPPDATA%\govor.ai` directory is deliberately shared across versions, so models, pairing,
and structured progress survive this replacement. Keep a backup of learner progress before a
major update.

## Reset or uninstall

- Delete the extracted version directories to remove the portable application.
- To remove all local models, logs, pairing state, and progress as well, delete
  `%LOCALAPPDATA%\govor.ai` only after making any desired progress export. This cannot be undone.
- Removing only `%LOCALAPPDATA%\govor.ai\security` forces a new PC certificate and device pairing.
  Clear the Android app's storage or reinstall it before pairing again.

See `troubleshooting.md` in the package for startup, model, firewall, certificate, and pairing
failures.
