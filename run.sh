#!/bin/bash
URL="$1"

wb-manager init capture
uwsgi uwsgi.ini &> /dev/null &

# needed for chrome
export QT_X11_NO_MITSHM=1

node index.js "$@"
