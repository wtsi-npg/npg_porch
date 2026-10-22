#!/bin/bash

set -eo pipefail
set -x

APP_USER=${APP_USER:? The APP_USER environment variable must be set}

cat > "/etc/sudoers.d/$APP_USER" << EOF
$APP_USER ALL= NOPASSWD: /usr/sbin/service postgresql start
$APP_USER ALL= NOPASSWD: /usr/sbin/service postgresql restart
$APP_USER ALL= NOPASSWD: /usr/sbin/service postgresql stop
EOF
