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

1. Put the PC and phone on the same trusted private network. The PC may use Ethernet or Wi-Fi; the
   phone uses Wi-Fi. Do not use a guest/client-isolated wireless network.
2. In Windows **Settings > Network & internet**, open the connected Ethernet or Wi-Fi network and
   set **Network profile type** to **Private**. govor.ai refuses to advertise a Public-profile
   adapter.
3. Run `Start-Govor.cmd`.
4. If Windows Firewall prompts, allow the packaged Python runtime on private networks only. The
   phone needs TCP ports 8765 and 8766; local inference remains bound to loopback.
5. Keep the console and host window open. The host starts on a dedicated **Connect your phone**
   screen with instructions, a QR, and an expiry countdown. The 3D lesson remains hidden until a
   lesson starts. The code is valid for ten minutes.
6. In the Android release, tap **Scan host QR** and point the phone at the host display. If the QR
   cannot be scanned, choose **Manual pairing options** in the host window and **Pair manually**
   on Android, then copy the displayed values. The console also retains the same diagnostics. Do
   not accept pairing details supplied by an unexpected device or network page.
7. To stop govor.ai, return to the console and press Enter. Wait for the message confirming that
   managed child processes closed before moving or updating the directory.

The pairing code is single use. The temporary QR image is removed when the launcher exits. A
successfully paired Android installation keeps a random device credential and offers
**Reconnect to saved host** on later starts.

The launcher chooses the active Private-profile adapter preferred by Windows. If the console lists
multiple eligible private addresses and the chosen one is not on the phone-reachable LAN, stop the
app and run `Start-Govor.cmd --lan-address <listed-IPv4>` from PowerShell or Command Prompt. The
override cannot select a Public, virtual/VPN, disconnected, or unassigned address. After changing
the host address, choose **Scan a different host QR** on Android.

## Add lessons

1. Double-click `Manage-Lessons.cmd` in the extracted Windows package.
2. Choose one `.json` lesson or one `.zip` bundle containing one or more JSON lessons.
3. Wait for the confirmation dialog. If govor.ai is running, connected Android clients update
   their lesson list automatically; no host restart or phone reconnect is required. A lesson
   already in progress is not changed and the new catalog applies to the next lesson.

Imports are local, additive, and offline. Existing scenario IDs are never overwritten. A rejected
or partially invalid bundle installs nothing; correct the content and select it again. The package
stores imported files under `content\lessons`. Keep a copy of custom lesson files before replacing
the extracted version directory during an update, then import them into the new version.

## Create a lesson

1. Start govor.ai with `Start-Govor.cmd` and leave its console open. The creator uses the local
   language model owned by that running process.
2. Double-click `Create-Lesson.cmd`.
3. Describe the topic or speaking goal. Optionally choose beginner/intermediate/advanced content,
   any currently installed environment, and one through eight exercises. Automatic uses
   intermediate content, five exercises, and a deterministic suitable/fallback environment.
4. Select **Create** and wait for the result dialog. Generation can take longer on the first call.
5. The lesson is saved under `content\lessons` and appears on connected phones without restarting
   the host. It does not replace a lesson already in progress.

Creation remains offline and sends the description only to the local loopback model. Generated
content is structurally validated but can still contain awkward or inaccurate teaching material;
try a clearer topic or remove the new JSON file while govor.ai is stopped if the result is not
useful. Keep wanted custom lesson files when updating the portable directory.

## Add 3D environments

1. Double-click `Manage-Environments.cmd` in the extracted Windows package.
2. Choose one environment `.zip` supplied for govor.ai. Do not unpack it first.
3. Wait for the confirmation dialog. The environment is registered immediately; the host and
   Godot player do not need to restart.
4. Open `Create-Lesson.cmd` to select the new environment, or import a lesson whose
   `scene_template_id` matches it. A connected phone shows the environment when that lesson next
   starts.

Environment imports are local, additive, and offline. A bundle may contain multiple JSON recipes,
but cannot contain Godot projects, programs, models, textures, or other files. Invalid bundles
install nothing. Imported recipes are stored under `content\environments`; keep a copy before
replacing the extracted version directory during an update.

## Update

### Signed incremental patch

This path is available only when the current package already contains `Apply-Govor-Patch.cmd`.
Older packages, including the completed 0.1.11 acceptance package, require the full-replacement
steps below once before they can receive incremental patches.

1. Stop govor.ai and wait for its clean-shutdown message.
2. Save the supplied `.govorpatch` or patch ZIP locally. Do not unpack or run a script from it.
3. Double-click the package's existing `Apply-Govor-Patch.cmd`, select the patch, and wait for the
   signed source version plus every old/new file hash to be checked before changes begin.
4. If it reports a wrong base, local conflict, signature/integrity failure, or rollback, do not
   copy files manually; request a patch for the exact installed version or use a complete release.
5. When an Android update is included, the verified APK path is printed. Copy it to the phone,
   open it, and approve Android's normal update prompt. It must appear as an update to
   `ai.govor.app`; never uninstall first, because that discards app-private pairing state.

The patch is a signed data archive, not an executable. The trusted updater is the copy already in
the installed release. It preserves unlisted files, including imported lesson/environment content,
and never modifies `%LOCALAPPDATA%` models, progress, credentials, or TLS identity except for
temporary update staging and an included verified APK. Android installation is never silent and
may be blocked by the phone's sideload policy.

### Complete release replacement

1. Stop the old launcher completely.
2. Verify and extract the new ZIP into a new versioned directory rather than mixing files from two
   versions.
3. Copy/re-import any custom lesson or environment content from the old release when needed.
4. Run the new `Setup-Govor.cmd`. Already present models are rechecked and are not downloaded again
   when their size and SHA-256 still match.
5. Run the new `Start-Govor.cmd`.

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
