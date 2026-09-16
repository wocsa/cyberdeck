"""Architecture preflight regression checks without root or real chroots."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cyberdeck-arch-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name) / "work with 'quotes'"
        self.work.mkdir()
        self.marker = self.work / "existing-rootfs"
        self.marker.touch()
        self.calls = Path(self.temp.name) / "calls"

    def check(self, mode):
        harness = r'''
source scripts/dependencies_check
arch-test() {
    printf '%s\n' "$*" >> "$TEST_CALLS"
    case "$1" in
        -n) [ "$TEST_MODE" = native ] ;;
        -c)
            [ -d "$2" ] || return 2
            [ "$3" = armhf ] || return 2
            [ "$TEST_MODE" != broken-chroot ] ;;
        armhf) [ "$TEST_MODE" != no-emulation ] ;;
        *) return 2 ;;
    esac
}
setarch() {
    [ "$1" = linux32 ] || return 2
    shift
    "$@"
}
capsh() {
    [ "$1" = --drop=cap_setfcap ] || return 2
    [ "$2" = -- ] || return 2
    shift 2
    bash "$@"
}
export -f arch-test
check_architecture
'''
        result = subprocess.run(
            ["bash", "-e", "-c", harness], cwd=REPO, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=dict(os.environ, ARCH="armhf", WORK_DIR=str(self.work),
                     CAPSH_ARG="--drop=cap_setfcap", TEST_MODE=mode,
                     TEST_CALLS=str(self.calls)))
        self.assertTrue(self.marker.exists())
        self.assertEqual(list(self.work.iterdir()), [self.marker])
        return result

    def test_native_does_not_need_chroot_emulation(self):
        result = self.check("native")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.calls.read_text().splitlines(), ["-n armhf"])

    def test_no_emulation_fails_before_chroot(self):
        result = self.check("no-emulation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No fallback mechanism", result.stdout)
        self.assertEqual(len(self.calls.read_text().splitlines()), 2)

    def test_host_only_emulation_is_rejected_with_repair_instructions(self):
        result = self.check("broken-chroot")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed inside the build chroot", result.stdout)
        self.assertIn("sudo apt-get install qemu-user-static binfmt-support", result.stdout)
        self.assertIn("sudo update-binfmts --enable qemu-arm", result.stdout)

    def test_chroot_capable_emulation_is_accepted(self):
        result = self.check("emulated")
        self.assertEqual(result.returncode, 0, result.stdout)
        calls = self.calls.read_text().splitlines()
        self.assertEqual(len(calls), 3)
        self.assertTrue(calls[-1].startswith("-c "))

    def test_dependency_accepts_static_executable_name(self):
        (self.work / "depends").write_text("qemu-arm:qemu-user-static\n")
        harness = r'''
source scripts/dependencies_check
hash() { [ "$1" = qemu-arm-static ]; }
uname() { echo armv7l; }
dependencies_check "$BASE_DIR/depends"
'''
        result = subprocess.run(
            ["bash", "-e", "-c", harness], cwd=REPO, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=dict(os.environ, BASE_DIR=str(self.work), SCRIPT_DIR=str(REPO / "scripts")))
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
