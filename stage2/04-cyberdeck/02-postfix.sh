#!/bin/bash
debconf-set-selections <<< "postfix postfix/mailname string cyberjutsu.local"
debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
apt-get install --assume-yes postfix