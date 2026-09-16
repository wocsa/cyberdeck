#!/bin/bash -e

echo "setting up firewall iptables logging"
cat > /etc/firewall.conf <<EOL
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:LOGGING - [0:0]

# Log packets traversing the host, then preserve the existing accept-all behavior.
-A INPUT -j LOGGING
-A OUTPUT -j LOGGING
-A FORWARD -j LOGGING
-A LOGGING -j LOG --log-prefix "iptables: " --log-level 4
-A LOGGING -j ACCEPT
COMMIT
EOL

# Route kernel LOG target messages to the traditional syslog file.  The
# package's default rules may already do this, but keep it explicit for the
# firewall image.
install -d -m 0755 /etc/rsyslog.d
cat > /etc/rsyslog.d/20-iptables.conf <<'EOL'
kern.*                                                  /var/log/syslog
& stop
EOL
systemctl enable rsyslog.service >/dev/null 2>&1 || true

echo '#!/bin/sh' > /etc/network/if-up.d/iptables
echo "iptables-restore < /etc/firewall.conf" >> /etc/network/if-up.d/iptables
chmod +x /etc/network/if-up.d/iptables

#SSH server allow using agent
sed -i 's/#AllowAgentForwarding yes/AllowAgentForwarding yes/g' /etc/ssh/sshd_config

#SSH allow to use agent for all addresses
mkdir -p /etc/skel/.ssh
tee /etc/skel/.ssh/config > /dev/null << 'EOF'
Host *
  ForwardAgent yes
EOF
chmod 700 /etc/skel/.ssh
chmod 600 /etc/skel/.ssh/config

echo "configure keyboard layout"
echo '
XKBMODEL="pc109"
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
