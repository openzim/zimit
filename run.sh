#!/bin/bash
URL="$1"

wb-manager init capture
uwsgi uwsgi.ini &

/browser/browser_entrypoint.sh /browser/run.sh &

node index.js "$URL"

NAME=${NAME:=zimfile}

stat /output

warc2zim --url $URL --name $NAME --output=/output ./collections/capture/archive/*.warc.gz


