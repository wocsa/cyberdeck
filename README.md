# Cyberdeck

Generation of operating system for the Cyberdeck based on [pi-gen](https://github.com/RPi-Distro/pi-gen).

To build it please [read the doc](pi-gen.md)

## What is it ?

Cyberdeck is the equipment for [Cyberjūtsuka サイバー述家](https://github.com/wocsa/cyberjutsu/blob/main/glossary.md#cyberjutsuka) used to practice [Cyberjūtsu サイバー述](http://github.com/wocsa/cyberjutsu).

It's like Judogi for Judoka or Karategi for Karateka.

Cyberdeck is made to provide capability to Cyberjūtsuka to practice and communicate throug Cyberdeck by network.


## Command line tools available
* bash
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
LoadModule info_module modules/mod_info.so

<VirtualHost *:80> 

  ServerSignature On

  ServerTokens Full

  LogLevel info

  LogFormat "%h %l %u %t \"%r\" %>s %b" common
  LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"" combined
  LogFormat "%t %h %m \"%r\"" custom

  ErrorLog ${APACHE_LOG_DIR}/error.log
  
  CustomLog ${APACHE_LOG_DIR}/common.log common
  CustomLog ${APACHE_LOG_DIR}/access.log combined
  CustomLog ${APACHE_LOG_DIR}/custom.log custom

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
    DocumentRoot /var/www/html
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