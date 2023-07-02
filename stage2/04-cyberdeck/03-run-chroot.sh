#!/bin/bash -e

echo "setting up firewall iptables logging"
cat > /etc/firewall.conf <<EOL
# Generated by iptables-save v1.8.7 on Sun Jun 25 21:59:03 2023
*mangle
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
COMMIT
# Completed on Sun Jun 25 21:59:03 2023
# Generated by iptables-save v1.8.7 on Sun Jun 25 21:59:03 2023
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -p tcp -m tcp --dport 25 -m state --state NEW -j LOG --log-prefix "New SMTP connection "
-A INPUT -p tcp -m tcp --dport 23 -m state --state NEW -j LOG --log-prefix "New TELNET connection "
-A INPUT -p tcp -m tcp --dport 161 -m state --state NEW -j LOG --log-prefix "New SNMP connection "
-A INPUT -p tcp -m tcp --dport 123 -m state --state NEW -j LOG --log-prefix "New NTP connection "
-A INPUT -p tcp -m tcp --dport 53 -m state --state NEW -j LOG --log-prefix "New DNS connection "
-A INPUT -p tcp -m tcp --sport 20 -m state --state NEW -j LOG --log-prefix "New FTP connection "
-A INPUT -p tcp -m tcp --dport 21 -m state --state NEW -j LOG --log-prefix "New FTP connection "
-A INPUT -p tcp -m tcp --dport 443 -m state --state NEW -j LOG --log-prefix "New HTTPS connection "
-A INPUT -p tcp -m tcp --dport 80 -m state --state NEW -j LOG --log-prefix "New HTTP connection "
-A INPUT -p tcp -m tcp --dport 22 -m state --state NEW -j LOG --log-prefix "New SSH connection "
-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 80 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 443 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 21 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 53 -j ACCEPT
-A INPUT -p udp -m udp --dport 123 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 161 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 23 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 25 -j ACCEPT
-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
-A INPUT -p tcp -m state --state NEW -j LOG --log-prefix "INCOMING connection "
-A OUTPUT -p tcp -m tcp --sport 20 -j ACCEPT
COMMIT
# Completed on Sun Jun 25 21:59:03 2023
# Generated by iptables-save v1.8.7 on Sun Jun 25 21:59:03 2023
*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
COMMIT
# Completed on Sun Jun 25 21:59:03 2023
EOL

echo '#!/bin/sh' > /etc/network/if-up.d/iptables
echo "iptables-restore < /etc/firewall.conf" >> /etc/network/if-up.d/iptables
chmod +x /etc/network/if-up.d/iptables

echo "configure keyboard layout"
echo '
XKBMODEL="pc105"
XKBLAYOUT="fr"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
' > /etc/default/keyboard
    
dpkg-reconfigure --frontend noninteractive keyboard-configuration

echo "configure console font size"
echo '
# CONFIGURATION FILE FOR SETUPCON

# Consult the console-setup(5) manual page.

ACTIVE_CONSOLES="/dev/tty[1-6]"

CHARMAP="UTF-8"

CODESET="guess"
FONTFACE="Terminus"
FONTSIZE="6x12"

VIDEOMODE=

' > /etc/default/console-setup

echo "rename pi user into cyberjutsuka and set password"

usermod --login cyberjutsuka pi || true
echo "cyberjutsuka:hajime" | chpasswd

echo "setting up web server apache2"
usermod -a -G www-data cyberjutsuka
chown -R -f www-data:www-data /var/www/html

sed -i 's/ServerToken OS/#ServerToken OS/' /etc/apache2/conf-enabled/security.conf
sed -i 's/#ServerToken Full/ServerToken Full/' /etc/apache2/conf-enabled/security.conf
sed -i 's/TraceEnabled Off/#TraceEnabled Off/' /etc/apache2/conf-enabled/security.conf
sed -i 's/#TraceEnabled On/TraceEnabled On/' /etc/apache2/conf-enabled/security.conf

cat > /etc/pam.d/apache <<EOL
auth required pam_unix.so
account required pam_unix.so
EOL

groupadd shadow || true
usermod -a -G shadow www-data
chown root:shadow /etc/shadow
chmod g+r /etc/shadow

cat > /etc/apache2/sites-available/001-cyberjutsu.conf <<EOL
<VirtualHost *:80>

  LogLevel info
  LogFormat "%h %l %u %t \"%r\" %>s %b" comm
  LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"" combined
  LogFormat "%t %h %m \"%r\"" custom
  ErrorLog "| /usr/bin/logger -thttp_error: -plocal6.err"
  CustomLog "| /usr/bin/logger -thttp_info: -plocal6.info" common
  CustomLog "| /usr/bin/logger -thttp_info: -plocal6.info" combined
  CustomLog "| /usr/bin/logger -thttp_info: -plocal6.info" custom
  
  DocumentRoot /var/www/html

  <Location /server-status>
    SetHandler server-status
    Options All MultiViews
    AllowOverride All
    Require all granted
    Order deny,allow
    AuthType Basic
    AuthName "private area"
    AuthBasicProvider PAM
    AuthPAMService apache
    Require valid-user
  </Location>

  <Directory />
    Dav On
    Options All MultiViews
    AllowOverride All
    Require all granted
    Order deny,allow
    AuthType Basic
    AuthName "private area"
    AuthBasicProvider PAM
    AuthPAMService apache
    Require valid-user
  </Directory>

</VirtualHost>
EOL

a2enmod dav
a2enmod dav_fs
a2enmod authnz_pam
a2dissite 000-default
a2dissite default-ssl
a2ensite 001-cyberjutsu

echo "setting up ftp server"
groupadd -f ftpgroup
usermod -a -G ftpgroup cyberjutsuka

echo "enable wireless"
rfkill unblock all
