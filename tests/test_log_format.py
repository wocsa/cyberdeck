"""Exercise the real rsyslog formatter over a private Unix socket, without root."""

from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest


FORMAT = Path(__file__).resolve().parents[1] / "stage2/04-cyberdeck/files/20-iptables.conf"


@unittest.skipUnless(shutil.which("rsyslogd"), "rsyslogd is required")
class LogFormatTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cdlog-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "syslog"
        self.sock = self.root / "input"
        config = self.root / "rsyslog.conf"
        config.write_text(
            'module(load="imuxsock" SysSock.Use="off")\n'
            f'input(type="imuxsock" Socket="{self.sock}")\n'
            + FORMAT.read_text().replace('/var/log/syslog', str(self.output))
            + f'\n*.* action(type="omfile" file="{self.output}")\n')
        self.errors = (self.root / "stderr").open("w+")
        self.addCleanup(self.errors.close)
        self.process = subprocess.Popen(
            ["rsyslogd", "-n", "-i", str(self.root / "pid"), "-f", str(config)],
            stdout=self.errors, stderr=self.errors)
        self.addCleanup(self.stop)
        deadline = time.monotonic() + 3
        while not self.sock.exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                self.errors.seek(0)
                errors = self.errors.read()
                if f"could not open config file '{config}': Permission denied" in errors:
                    self.skipTest("Host confinement denies rsyslog access to the private test config; run on the Pi")
                self.fail(errors)
            time.sleep(0.01)

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)

    def emit(self, msg):
        started = time.monotonic()
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            sender.sendto(("<6>kernel: " + msg).encode(), str(self.sock))
        deadline = started + 1
        while not self.output.exists() or not self.output.read_text():
            if time.monotonic() > deadline:
                self.fail("Event was not visible within one second")
            time.sleep(0.01)
        first = self.output.read_text()
        self.stop()  # Flush any duplicate queued by a second file action.
        self.assertEqual(first, self.output.read_text())
        self.assertEqual(len(first.splitlines()), 1)
        return first

    def test_incoming_tcp_once_and_immediate(self):
        line = self.emit("CDNET OBSERVE NEW IN=wlan0 OUT= MAC=aa:bb SRC=192.0.2.1 "
                         "DST=192.0.2.2 LEN=60 TTL=64 PROTO=TCP SPT=45678 DPT=22 SYN URGP=0")
        self.assertIn("net: ACTION=OBSERVE STATUS=NEW DIR=IN PROTO=TCP "
                      "SRC=192.0.2.1 SPT=45678 DST=192.0.2.2 DPT=22 IN=wlan0", line)
        self.assertRegex(line, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
        self.assertNotIn("MAC=", line)
        self.assertNotIn("URGP=", line)

    def test_ipv6_outgoing(self):
        line = self.emit("CDNET OBSERVE NEW IN= OUT=wlan0 SRC=2001:db8::1 "
                         "DST=2001:db8::2 PROTO=UDP SPT=12345 DPT=53")
        self.assertIn("DIR=OUT PROTO=UDP SRC=2001:db8::1 SPT=12345 "
                      "DST=2001:db8::2 DPT=53 OUT=wlan0", line)

    def test_forwarded_drop(self):
        line = self.emit("CDNET DROP BLOCKED IN=wlan0 OUT=eth0 SRC=192.0.2.1 "
                         "DST=198.51.100.1 PROTO=TCP SPT=12345 DPT=8080")
        self.assertIn("ACTION=DROP STATUS=BLOCKED DIR=FWD", line)
        self.assertIn("IN=wlan0 OUT=eth0", line)

    def test_icmp_error_does_not_borrow_embedded_ports(self):
        line = self.emit("CDNET OBSERVE RELATED IN=wlan0 OUT= SRC=192.0.2.2 "
                         "DST=192.0.2.1 PROTO=ICMP TYPE=3 CODE=3 "
                         "[SRC=192.0.2.1 DST=192.0.2.2 PROTO=UDP SPT=12345 DPT=53]")
        self.assertIn("PROTO=ICMP SRC=192.0.2.2 SPT=- DST=192.0.2.1 DPT=-", line)
        self.assertIn("TYPE=3 CODE=3", line)

    def test_other_kernel_logs_keep_normal_routing(self):
        line = self.emit("ordinary kernel event")
        self.assertIn("ordinary kernel event", line)
        self.assertNotIn("net: ACTION=", line)
