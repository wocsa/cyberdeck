"""Unprivileged regression checks; no mounts, downloads, or live network changes."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cyberdeck-bootstrap-")
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name) / "stage0"
        self.stage.mkdir()
        self.root = self.stage / "rootfs"
        self.calls = self.stage / "calls"
        self.env = dict(os.environ, ROOTFS_DIR=str(self.root),
                        STAGE_WORK_DIR=str(self.stage), STAGE_DIR=str(REPO / "stage0"),
                        LOG_FILE=str(self.stage / "build.log"), RELEASE="trixie",
                        TEST_CALLS=str(self.calls), TEST_MODE="success")

    def complete_root(self):
        (self.root / "bin").mkdir(parents=True, exist_ok=True)
        (self.root / "etc/apt").mkdir(parents=True, exist_ok=True)
        (self.root / "bin/sh").touch()
        (self.root / "bin/sh").chmod(0o755)

    def run_bootstrap(self, command, mode="success"):
        # Stub only the privileged debootstrap launcher. Exercise the real
        # bootstrap result handling, diagnostics, and stage0 retry logic.
        harness = r'''
source scripts/common
setarch() {
    printf 'called\n' >> "$TEST_CALLS"
    case "$TEST_MODE" in
        failure)
            mkdir -p "$ROOTFS_DIR/debootstrap"
            printf 'download failed\n' > "$ROOTFS_DIR/debootstrap/debootstrap.log"
            return 42 ;;
        failure-without-log) return 42 ;;
        incomplete) mkdir -p "$ROOTFS_DIR" ;;
        success)
            mkdir -p "$ROOTFS_DIR/bin" "$ROOTFS_DIR/etc/apt"
            touch "$ROOTFS_DIR/bin/sh"
            chmod 755 "$ROOTFS_DIR/bin/sh" ;;
    esac
}
export -f setarch
'''
        return subprocess.run(["bash", "-e", "-c", harness + command], cwd=REPO,
                              env=dict(self.env, TEST_MODE=mode), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def test_failed_bootstrap_preserves_diagnostics(self):
        result = self.run_bootstrap('bootstrap trixie "$ROOTFS_DIR" mirror', "failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.stage / "debootstrap.log").read_text(), "download failed\n")

    def test_nonzero_exit_rejected_even_with_complete_looking_root(self):
        self.complete_root()
        result = self.run_bootstrap('bootstrap trixie "$ROOTFS_DIR" mirror', "failure-without-log")
        self.assertNotEqual(result.returncode, 0)

    def test_zero_exit_with_incomplete_root_is_rejected(self):
        result = self.run_bootstrap('bootstrap trixie "$ROOTFS_DIR" mirror', "incomplete")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete rootfs", result.stdout)

    def test_successful_bootstrap(self):
        result = self.run_bootstrap('bootstrap trixie "$ROOTFS_DIR" mirror')
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_retry_replaces_partial_root_only(self):
        self.root.mkdir()
        (self.root / "partial").touch()
        unrelated = self.stage / "keep"
        unrelated.touch()
        result = self.run_bootstrap("bash -e stage0/prerun.sh")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.root / "partial").exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue((self.root / "etc/apt").is_dir())

    def test_retry_replaces_root_with_unfinished_debootstrap(self):
        self.complete_root()
        (self.root / "debootstrap").mkdir()
        result = self.run_bootstrap("bash -e stage0/prerun.sh")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.calls.exists())
        self.assertFalse((self.root / "debootstrap").exists())

    def test_complete_root_is_reused(self):
        self.complete_root()
        result = self.run_bootstrap("bash -e stage0/prerun.sh")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.calls.exists())

    def test_unexpected_root_path_is_not_removed(self):
        other = self.stage / "unexpected"
        other.mkdir()
        marker = other / "keep"
        marker.touch()
        self.env["ROOTFS_DIR"] = str(other)
        result = self.run_bootstrap("bash -e stage0/prerun.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(marker.exists())


@unittest.skipUnless(shutil.which("nmcli"), "nmcli is needed for offline Wi-Fi checks")
class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cyberdeck-network-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "etc/systemd/system").mkdir(parents=True)
        (self.root / "etc/cloud").mkdir()
        self.profile = self.root / "etc/NetworkManager/system-connections/cyberdeck-wifi.nmconnection"

    def configure(self, ssid="dojo", password="test-password", cloud_init="0"):
        # Redirect the chroot's NetworkManager paths into a temporary root;
        # nmcli itself runs in offline mode and never contacts a network daemon.
        harness = r'''
on_chroot() {
    sed "s|/etc/NetworkManager|${ROOTFS_DIR}/etc/NetworkManager|g" | bash -e
}
export -f on_chroot
bash -e ./02-run.sh
'''
        return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", harness],
                              cwd=REPO / "stage2/04-cyberdeck",
                              env=dict(os.environ, ROOTFS_DIR=str(self.root),
                                       WPA_ESSID=ssid, WPA_PASSWORD=password,
                                       ENABLE_CLOUD_INIT=cloud_init),
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def test_secured_wifi_and_cloud_init_disable(self):
        result = self.configure()
        self.assertEqual(result.returncode, 0, result.stdout)
        profile = self.profile.read_text()
        self.assertIn("ssid=dojo", profile)
        self.assertIn("key-mgmt=wpa-psk", profile)
        self.assertIn("psk=test-password", profile)
        self.assertEqual(self.profile.stat().st_mode & 0o777, 0o600)
        self.assertIn("[ipv4]\nmethod=auto", profile)
        self.assertNotIn("autoconnect=false", profile)
        self.assertTrue((self.root / "etc/cloud/cloud-init.disabled").exists())
        self.assertTrue((self.root / "etc/systemd/system/cyberdeck-firewall.service").exists())

    def test_open_network_has_no_psk(self):
        result = self.configure(password="", cloud_init="1")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("[wifi-security]", self.profile.read_text())
        self.assertFalse((self.root / "etc/cloud/cloud-init.disabled").exists())

    def test_unset_ssid_does_not_create_a_profile(self):
        result = self.configure(ssid="", password="")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.profile.exists())

    def test_shell_metacharacters_are_literal(self):
        result = self.configure(ssid='Dojo "guest"; $(false)', password='secret`false`$word')
        self.assertEqual(result.returncode, 0, result.stdout)
        profile = self.profile.read_text()
        # NetworkManager escapes semicolons in its keyfile representation.
        self.assertIn(r'ssid=Dojo "guest"\\; $(false)', profile)
        self.assertIn('psk=secret`false`$word', profile)


if __name__ == "__main__":
    unittest.main()
