#!/bin/bash
wb-manager init capture
uwsgi uwsgi.ini &> /dev/null &

# needed for chrome
export QT_X11_NO_MITSHM=1

cmd="$@"

su zimit -c "node index.js $cmd"


