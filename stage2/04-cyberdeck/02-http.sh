#!/bin/bash
usermod -a -G www-data cyberjutsuka
chown -R -f www-data:www-data /var/www/html

echo '<VirtualHost *:80>

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

</VirtualHost>' > /etc/apache2/sites-available/001-cyberjutsu.conf

a2dissite default
a2ensite 001-cyberjutsu