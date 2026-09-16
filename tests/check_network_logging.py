"""Privileged integration check; run in a disposable network namespace.

sudo unshare --net python3 tests/check_network_logging.py path/to/firewall.conf
Requires iproute2, util-linux, iptables and ping. Never runs in the host netns.
"""

import errno
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def count(chain):
    rules = run("iptables-save", "-c").stdout.splitlines()
    return sum(int(line.split(":", 1)[0][1:]) for line in rules
               if f"-A {chain} " in line and "-j LOG " in line)


def check_delta(chain, expected, operation):
    before = count(chain)
    operation()
    actual = count(chain) - before
    assert actual == expected, f"{chain}: expected {expected} records, got {actual}"
    print(f"PASS {chain}: {actual} log records", flush=True)


def udp(port, count=20, family=socket.AF_INET, target="198.18.0.2", blocked=False):
    with socket.socket(family, socket.SOCK_DGRAM) as client:
        for _ in range(count):
            try:
                client.sendto(b"sparring", (target, port))
            except OSError as error:
                if not blocked or error.errno not in (errno.EPERM, errno.EACCES, errno.ECONNREFUSED):
                    raise


if __name__ == "__main__":
    assert os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net"), \
        "Run with sudo unshare --net; refusing to modify the host firewall"
    rules = Path(sys.argv[1]).resolve()
    peer = subprocess.Popen(["unshare", "--net", "sleep", "120"])
    server = None
    try:
        for _ in range(100):
            if os.readlink(f"/proc/{peer.pid}/ns/net") != os.readlink("/proc/self/ns/net"):
                break
            time.sleep(0.01)
        else:
            raise RuntimeError("peer namespace did not start")
        prefix = ["nsenter", "-t", str(peer.pid), "-n"]
        run("ip", "link", "add", "cdtest0", "type", "veth", "peer", "name", "cdtest1")
        run("ip", "link", "set", "cdtest1", "netns", str(peer.pid))
        for cmd, iface, addr, v6 in [([], "cdtest0", "198.18.0.1/30", "fd00:cde::1/64"),
                                    (prefix, "cdtest1", "198.18.0.2/30", "fd00:cde::2/64")]:
            run(*cmd, "ip", "link", "set", "lo", "up")
            run(*cmd, "ip", "addr", "add", addr, "dev", iface)
            run(*cmd, "ip", "-6", "addr", "add", v6, "dev", iface, "nodad")
            run(*cmd, "ip", "link", "set", iface, "up")
        run("iptables-restore", str(rules))
        run("ip6tables-restore", str(rules))
        server_code = '''
import selectors,socket
s=selectors.DefaultSelector()
for family,host in [(socket.AF_INET,'198.18.0.2'),(socket.AF_INET6,'fd00:cde::2')]:
    for port in (19001,19002):
        u=socket.socket(family,socket.SOCK_DGRAM); u.bind((host,port)); s.register(u,1)
t=socket.socket(); t.bind(('198.18.0.2',19003)); t.listen(); s.register(t,1)
print('ready',flush=True)
while True:
    for key,_ in s.select():
        obj=key.fileobj
        if obj is t:
            c,_=t.accept(); s.register(c,1)
        elif obj.type == socket.SOCK_DGRAM:
            obj.recvfrom(65535)
        else:
            data=obj.recv(65535)
            if data: obj.sendall(data)
            else: s.unregister(obj); obj.close()
'''
        server = subprocess.Popen(prefix + ["python3", "-u", "-c", server_code],
                                  stdout=subprocess.PIPE, text=True)
        assert server.stdout.readline().strip() == "ready"

        # Unanswered UDP remains NEW: --ctstate NEW alone would log all 20.
        check_delta("CD_NEW", 1, lambda: udp(19001))
        check_delta("CD_NEW", 1, lambda: udp(19002))

        def tcp():
            with socket.create_connection(("198.18.0.2", 19003), timeout=2) as client:
                for _ in range(20):
                    client.sendall(b"sparring")
                    assert client.recv(8) == b"sparring"
        check_delta("CD_NEW", 1, tcp)
        check_delta("CD_NEW", 1, tcp)  # A distinct connection is not suppressed.
        check_delta("CD_NEW", 1, lambda: run("ping", "-c", "5", "-i", "0.05", "198.18.0.2"))

        # Real SYN retransmissions, with an unrelated connection-mark bit set.
        run(*prefix, "iptables", "-A", "INPUT", "-p", "tcp", "--dport", "19007", "-j", "DROP")
        run("iptables", "-t", "mangle", "-A", "OUTPUT", "-p", "tcp", "--dport", "19007",
            "-j", "CONNMARK", "--or-mark", "0x20")
        def unanswered_tcp():
            try:
                with socket.create_connection(("198.18.0.2", 19007), timeout=2.5):
                    raise AssertionError("Peer should drop SYN packets")
            except TimeoutError:
                pass
        check_delta("CD_NEW", 1, unanswered_tcp)
        saved = run("iptables-save", "-c", "-t", "mangle").stdout
        marked = next(x for x in saved.splitlines() if "--dport 19007" in x)
        assert int(marked.split(":", 1)[0][1:]) >= 2, "No retransmission exercised"
        # The logging bit must coexist with the pre-existing 0x20 bit.
        run("iptables", "-A", "OUTPUT", "-p", "udp", "--dport", "19008",
            "-m", "connmark", "--mark", "0x80000020/0x80000020", "-j", "RETURN")
        run("iptables", "-t", "mangle", "-A", "OUTPUT", "-p", "udp", "--dport", "19008",
            "-j", "CONNMARK", "--or-mark", "0x20")
        udp(19008, count=1)
        saved = run("iptables-save", "-c").stdout
        assert "[1:" in next(x for x in saved.splitlines() if "--dport 19008" in x)

        # A blocked flow is never confirmed; connmarks alone cannot deduplicate it.
        run("iptables", "-I", "OUTPUT", "1", "-p", "udp", "--dport", "19004", "-j", "CD_DROP")
        check_delta("CD_DROP_LOG", 1, lambda: udp(19004, blocked=True))
        run("iptables", "-I", "OUTPUT", "1", "-p", "udp", "--dport", "19005", "-j", "CD_REJECT")
        check_delta("CD_REJECT_LOG", 1, lambda: udp(19005, blocked=True))
        # The terminal verdict must still handle every suppressed packet.
        saved = run("iptables-save", "-c").stdout
        assert "[20:" in next(x for x in saved.splitlines() if "-A CD_DROP -j DROP" in x)
        assert "[20:" in next(x for x in saved.splitlines() if "-A CD_REJECT -j REJECT" in x)

        # Exercise rules appended after LOGGING must remain reachable.
        run("iptables", "-A", "OUTPUT", "-p", "udp", "--dport", "19006", "-j", "DROP")
        udp(19006, count=1, blocked=True)
        saved = run("iptables-save", "-c").stdout
        assert "[1:" in next(x for x in saved.splitlines() if "--dport 19006 -j DROP" in x)

        before = run("ip6tables-save", "-c").stdout
        udp(19001, family=socket.AF_INET6, target="fd00:cde::2")
        after = run("ip6tables-save", "-c").stdout
        def v6_count(value):
            return sum(int(x.split(":",1)[0][1:]) for x in value.splitlines()
                       if "-A CD_NEW " in x and "-j LOG " in x)
        assert v6_count(after) - v6_count(before) == 1
        print("PASS IPv6, block verdicts, and appended exercise rules", flush=True)
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=5)
        peer.terminate()
        peer.wait(timeout=5)
