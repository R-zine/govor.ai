from __future__ import annotations

import json
import xml.etree.ElementTree as element_tree
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_m8_vm_network_is_loopback_forwarded_to_the_host_emulator() -> None:
    config = json.loads((REPOSITORY_ROOT / "config" / "m8-vm.json").read_text(encoding="utf-8"))

    assert config["schema_version"] == 1
    assert config["hypervisor"] == "qemu-whpx"
    assert config["qemu_version"] == "11.0.50"
    assert config["guest_control_port"] == 8765
    assert config["guest_media_port"] == 8766
    assert config["monitor_host_port"] == 55223
    assert config["android_host_alias"] == "10.0.2.2"
    assert config["guest_ice_port"] == 18770
    assert config["ice_host_port"] == 18770
    assert (
        len(
            {
                config["ssh_host_port"],
                config["monitor_host_port"],
                config["control_host_port"],
                config["media_host_port"],
                config["ice_host_port"],
            }
        )
        == 5
    )
    assert config["control_host_port"] != config["guest_control_port"]
    assert config["media_host_port"] != config["guest_media_port"]
    assert config["reference_iso_page"].startswith("https://www.microsoft.com/")


def test_m8_unattended_template_is_parseable_and_contains_no_committed_secret() -> None:
    template = (REPOSITORY_ROOT / "distribution" / "vm" / "Autounattend.xml.template").read_text(
        encoding="utf-8"
    )
    rendered = (
        template.replace("{{IMAGE_INDEX}}", "1")
        .replace("{{ADMIN_PASSWORD}}", "test-fixture-password")
        .replace("{{PRODUCT_KEY_BLOCK}}", "")
    )

    # Static repository template, not external or runtime XML input.
    element_tree.fromstring(rendered)  # noqa: S314
    assert template.count("{{IMAGE_INDEX}}") == 1
    assert template.count("{{ADMIN_PASSWORD}}") == 2
    assert template.count("{{PRODUCT_KEY_BLOCK}}") == 1
    assert "test-fixture-password" not in template
    assert "BypassTPMCheck" in template
    assert "BypassSecureBootCheck" in template
    assert "BypassCPUCheck" in template


def test_m8_vm_script_crosses_release_entrypoints_and_preserves_the_hardware_gate() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "m8-vm.ps1").read_text(encoding="utf-8")

    for action in (
        "Prerequisites",
        "Provision",
        "ResumeProvision",
        "FinalizeProvision",
        "StageRelease",
        "SetupRelease",
        "StartRelease",
        "WaitRelease",
    ):
        assert f"'{action}'" in script
    assert "hostfwd=tcp:127.0.0.1" in script
    assert "hostfwd=udp:127.0.0.1" in script
    assert "GOVOR_MEDIA_ICE_FIXTURE_ADVERTISE_HOST" in script
    assert "GOVOR_MEDIA_ICE_FIXTURE_BIND_PORT" in script
    assert "GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS=90" in script
    assert "Govor-M8-Ice" in script
    assert "[Console]::In.ReadToEnd()" in script
    assert "[ScriptBlock]::Create" in script
    assert "-EncodedCommand" not in script
    assert "sendkey a" in script
    assert "foreach ($attempt in 1..30)" in script
    assert "Start-Sleep -Milliseconds 500" in script
    assert "tcp:127.0.0.1:$($config.monitor_host_port),server=on,wait=off" in script
    assert "Start-Govor.cmd" in script
    assert "pairing details were not flushed" in script
    assert "(Test-Path 'C:\\GovorM8\\release.log' -PathType Leaf) -and" in script
    assert script.count("$ProgressPreference = 'SilentlyContinue'") >= 3
    assert "Setup-Govor.cmd" in script
    assert "--smoke-seconds {{SMOKE_SECONDS}}" in script
    assert "AddSeconds(240)" in script
    assert "if=pflash" in script
    assert "'-cpu', 'Skylake-Client-v4'" in script
    assert "qemu-xhci,id=xhci" in script
    assert "usb-kbd,bus=xhci.0" in script
    assert "file=fat:$seed,format=raw,readonly=on,if=none,id=seed" in script
    assert "usb-storage,drive=seed,removable=on" in script
    assert "Provisioning resume started from the existing base disk." in script
    assert "Provisioning record retrieved and clean base stopped." in script
    assert "'-N', '\"\"'" in script
    assert "The VM SSH key pair is incomplete." in script
    assert "setup_product_key_provided = [bool]$SetupProductKey" in script
    assert "SetupProductKey must be a five-by-five Windows setup key" in script
    assert "A refused or incomplete SSH" in script
    assert "Guest artifact manifest hash mismatch." in script
    assert "Where-Object name -EQ" not in script
    assert "$zipEntries.Count -ne 1" in script
    assert "$apkEntries.Count -ne 1" in script
    assert "Copy-ToGuest -Paths @()" not in script


def test_m8_guest_bootstrap_pins_ssh_to_the_generated_public_key() -> None:
    bootstrap = (REPOSITORY_ROOT / "distribution" / "vm" / "bootstrap.ps1.template").read_text(
        encoding="utf-8"
    )

    assert bootstrap.count("{{SSH_PUBLIC_KEY}}") == 1
    assert "administrators_authorized_keys" in bootstrap
    assert "OpenSSH.Server" in bootstrap
    assert "New-NetFirewallRule" in bootstrap
    assert "Join-Path $seed.Root 'provisioned.json'" not in bootstrap
    assert "C:\\GovorM8" in bootstrap
