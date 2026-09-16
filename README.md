# Cyberdeck

Generation of operating system for the Cyberdeck based on [pi-gen](https://github.com/RPi-Distro/pi-gen).

To build it please [read the doc](pi-gen.md)

## Current image build

Cyberdeck **v1.4** uses pi-gen
[`2026-09-15-raspios-trixie-armhf`](https://github.com/RPi-Distro/pi-gen/tree/2026-09-15-raspios-trixie-armhf)
(Trixie, 32-bit). The matching repository tags are `v1.4` and
`pi-gen-2026-09-15-raspios-trixie-armhf`.
See [upstream provenance and local adaptations](UPSTREAM.md).

Edit `config`, then run `./build-docker.sh` on a Linux Docker host. Install
static QEMU and its binfmt registration on non-ARM hosts first. A native ARM
builder with a 4 KB kernel page size is upstream's supported environment;
cross-building depends on working QEMU/binfmt emulation.

On Ubuntu hosts where `qemu-user-binfmt` uses a dynamic interpreter, install:

```sh
sudo apt-get install qemu-user-static binfmt-support
sudo update-binfmts --enable qemu-arm
```

The build checks emulation inside an empty chroot before starting any stages.
If `arch-test armhf` passes but the chroot check fails, check the host's
`/proc/sys/fs/binfmt_misc/qemu-arm` registration: it must use static QEMU with
the `F` flag so the interpreter remains available inside chroots (see the
[kernel binfmt documentation](https://www.kernel.org/doc/html/latest/admin-guide/binfmt-misc.html)).
Installing QEMU only inside a Docker image does not repair the host registration.
After fixing the host, rerun the build; stage0 automatically retries an incomplete
bootstrap without requiring `clean.sh`.

The default image still ends at stage2 and exports a ZIP containing the Lite
image into `deploy/`. Native builds use `work/cyberdeck-trixie-armhf`; Docker
uses container `cyberdeck-trixie-armhf` and image `cyberdeck-pigen:trixie-armhf`.
These defaults avoid reusing Bullseye build state. Do not resume an old build
container or point `WORK_DIR` at a Bullseye root filesystem.

If Docker storage is limited, bind the build volumes to the project filesystem:

```sh
PIGEN_DOCKER_OPTS="--mount type=bind,src=$PWD/work,dst=/pi-gen/work" ./build-docker.sh
```

Allow several tens of GB for stage copies and image export, plus space in Docker's
own storage for its builder image and deployment volume. Existing build artifacts
are not automatically deleted by this upgrade.

Wi-Fi settings in `config` now create an automatically connecting NetworkManager
profile with DHCP. `WPA_COUNTRY` still sets the regulatory domain. Cloud-init is
disabled so the configured account and network settings remain in effect. The
firewall is restored by `cyberdeck-firewall.service` before networking starts,
for IPv4 and IPv6. Compact network events go immediately to `/var/log/syslog`.

### Live network events during sparring

```sh
tail -F -s 0.1 /var/log/syslog | grep --line-buffered ' net: '
```

Example (the timestamp includes the local UTC offset):

```text
2026-09-16T14:30:00.123456+02:00 cyberdeck net: ACTION=OBSERVE STATUS=NEW DIR=IN PROTO=TCP SRC=192.168.1.86 SPT=40250 DST=192.168.1.29 DPT=22 IN=wlan0
```

The first packet of a new tracked flow produces one line. A reserved connection
mark bit (`0x80000000`) suppresses retransmissions and repeated unanswered UDP
packets; established traffic, replies, and loopback traffic stay quiet. Other
connection-mark bits are preserved. This avoids the repeated `NEW` packets that
a plain `--ctstate NEW` logging rule would still print.

Here, an **event** is a new conntrack flow, not each packet or application
request. TCP connections, UDP endpoint/port tuples, and ping sessions get an
initial observation. A new flow after conntrack expiry is a new event. Activity
inside an existing SSH session or HTTP keep-alive connection needs application
logs; it does not produce another firewall line.

`ACTION=OBSERVE STATUS=NEW` means a connection attempt was seen, not that the
connection or login succeeded. `RELATED`, `INVALID`, and `UNTRACKED` describe
conntrack state. ICMP messages include `TYPE` and `CODE`; protocols without
transport ports use `SPT=- DPT=-`. `DIR` is `IN`, `OUT`, or `FWD`. Addresses and
ports are those at the filter hook, after any destination NAT. An ICMP failure
can produce a separate `RELATED` event after the initial attempt.

For a block with an explicit verdict in the log, insert an exercise rule before
the observation rule and target `CD_DROP` or `CD_REJECT`, for example:

```sh
sudo iptables -I INPUT 1 -p tcp --dport 8080 -j CD_DROP
# Undo the exercise:
sudo iptables -D INPUT -p tcp --dport 8080 -j CD_DROP
```

These produce `ACTION=DROP` or `ACTION=REJECT STATUS=BLOCKED` and always enforce
the verdict, even when repeat logs are suppressed. Use `ip6tables` for IPv6.
Plain `DROP`/`REJECT` rules do not automatically log their verdict. `LOGGING`
returns to the caller so appended training rules can execute; the default
policies remain ACCEPT.

Blocked and untracked packets cannot reliably retain a connection mark.
`hashlimit` therefore emits their first event immediately, then at most one
per ten seconds per action/state, protocol and endpoint/port tuple. The same
guard applies to related/invalid traffic. Non-TCP/UDP traffic shares a bucket
per source/destination pair, so repeated ICMP errors between the same hosts
are grouped. There is no global limiter hiding different TCP/UDP ports in a
scan. A scan with many distinct flows can still generate many lines; unlimited
event coverage and bounded output volume cannot both be guaranteed under a
flood. Kernel logging and queue capacity also limit delivery under overload.

Rsyslog writes each formatted event without a delayed batching timer and stops
processing that event before the default file rule, avoiding a second raw copy.
Other syslog messages retain their usual format. Correct timestamps depend on
the device clock being synchronized.

The rules and formatter live in `stage2/04-cyberdeck/files/`. To exercise the
rules without changing the host firewall, run this integration check on a
Linux host with root, iproute2, util-linux, iptables, Python 3 and ping:

```sh
sudo unshare --net python3 tests/check_network_logging.py stage2/04-cyberdeck/files/firewall.conf
```

`DEPLOY_ZIP` has been replaced by `DEPLOY_COMPRESSION=zip`. Boot configuration is
now under `/boot/firmware/`. The old QCOW2 helper/build option is no longer included.

Run local regression checks with `python3 -m unittest discover -s tests -v`
(NetworkManager's `nmcli` 1.42+ enables the offline Wi-Fi checks). The image build
also checks Apache and dnsmasq configuration before export.

After a successful build, test the ZIP with `unzip -t deploy/image_*-cyberdeck-lite.zip`.
On a Raspberry Pi, confirm Trixie in `/etc/os-release`, `armhf` from
`dpkg --print-architecture`, connection to `dojo`, SSH login as `cyberjutsuka`,
French keyboard/locale and Europe/Paris timezone, expected training services, and
`systemctl status cyberdeck-firewall rsyslog` plus firewall messages in
`/var/log/syslog`. Hardware boot validation is separate from build validation.

## What is it ?

Cyberdeck is the equipment for [Cyberjūtsuka サイバー述家](https://github.com/wocsa/cyberjutsu/blob/main/glossary.md#cyberjutsuka) used to practice [Cyberjūtsu サイバー述](http://github.com/wocsa/cyberjutsu).

It's like Judogi for Judoka or Karategi for Karateka.

Cyberdeck is made to provide capability to Cyberjūtsuka to practice [Cyberjūtsu サイバー述](http://github.com/wocsa/cyberjutsu) with partners through Cyberdeck via the [dojo](https://github.com/wocsa/cyberjutsu/blob/main/glossary.md#dojo).


## Command line tools available
* bash
* chroot
* nmap
* curl
* screen
* python
* ping
* dig
* nslookup
* curl
* iptables
* tcpdump
* htop
* iotop
* netcat
* openssl
* openssh
* gdb
* snmpwalk
* snmpget

## Services opened on boot

* http (port 80) apache or httpd service
* https (port 443) apache or httpd service
* ftp (port 21) pure-ftpd service
* snmp (port 161) snmpd service
* dns (port 53) dnsmasq service
* smtp (port 25) smtpd service
* telnet (port 23) telnetd service
* ssh (port 22) sshd service
* ntp (port 123) ntpd service


## default configuration by services
login: cyberjutsuka
password: hajime
### ssh

/etc/ssh/sshd_config
```
ClientAliveInterval 3600 
ClientAliveCountMax 0
PasswordAuthentication yes
PermitEmptyPasswords yes
PermitRootLogin yes
Protocol 2, 1
Port 22
AcceptEnv *
PermitTunnel yes
AllowAgentForwarding yes
AllowTcpForwarding yes
TCPKeepAlive yes
LogLevel INFO
```

### http

httpd.conf
```
<VirtualHost *:80>

  LogLevel info
  LogFormat "%h %l %u %t \"%r\" %>s %b" comm
  LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"" combined
  LogFormat "%t %h %m \"%r\"" custom
  ErrorLog ${APACHE_LOG_DIR}/error.log
  CustomLog ${APACHE_LOG_DIR}/common.log common
  CustomLog ${APACHE_LOG_DIR}/access.log combined
  CustomLog ${APACHE_LOG_DIR}/custom.log custom
  
  DocumentRoot /var/www/html

  <Location /server-status>
    SetHandler server-status
    Order allow,deny
    Allow from all
  </Location>

  <Directory />
    Options All
    AllowOverride All
    Require all granted
    Order allow,deny
  </Directory>

</VirtualHost>

```

### https

### ftp

### snmp

/etc/snmp/snmpd.conf
```

# snmpd control (yes means start daemon).
SNMPDRUN=yes

# snmpd options (use syslog, close stdin/out/err).
SNMPDOPTS='-Lsd -a -A -Lf /dev/null -u root -g root -I -smux -p /var/run/snmpd.pid '

# create symlink on Debian legacy location to official RFC path
SNMPDCOMPAT=yes

# snmptrapd control (yes means start daemon).  As of net-snmp version
# 5.0, master agentx support must be enabled in snmpd before snmptrapd
# can be run.  See snmpd.conf(5) for how to do this.
TRAPDRUN=yes

# snmptrapd options (use syslog).
TRAPDOPTS='-Lsd -a -A -p /var/run/snmptrapd.pid'


rocommunity cyberjutsu

load 16 8 4

includeAllDisks 10%
disk /boot 15000
proc httpd 100 2 #apache monitoring
proc sshd 100 2 #ssh monitoring
proc pure-ftpd 100 2 #ftp monitoring
proc dnsmasq 100 2 #dns monitoring
proc smtpd 100 2 #smtp monitoring
proc telnetd 100 2 #telnet monitoring
proc ntpd 100 2 #ntpd monitoring
file /var/log/syslog  153600
```
### telnet

### dns

### ntp

/etc/ntp.conf
```
logfile /var/log/ntpstats/ntpd
statsdir /var/log/ntpstats/
statistics loopstats peerstats clockstats
filegen loopstats file loopstats type day enable
filegen peerstats file peerstats type day enable
filegen clockstats file clockstats type day enable

# Addresses to listen on (ntpd does not listen by default)
listen on *

server 0.fr.pool.ntp.org
server 1.fr.pool.ntp.org

burst
iburst

version 1

```

## Logging to syslog

### Firewall

The image installs event logging automatically. See
[live network events during sparring](#live-network-events-during-sparring)
for event semantics and rules that log a block verdict. Extra per-port `LOG`
rules would bypass deduplication and can reintroduce duplicate entries.

```sh
sudo iptables -L LOGGING -n -v
sudo ip6tables -L LOGGING -n -v
tail -F -s 0.1 /var/log/syslog | grep --line-buffered ' net: '
```
