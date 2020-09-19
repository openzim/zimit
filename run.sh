#!/bin/bash
URL="$1"

wb-manager init capture
uwsgi uwsgi.ini &> /dev/null &

#/browser/browser_entrypoint.sh /browser/run.sh &
#if [[ -n "$PROXY_CA_FILE" && -f "$PROXY_CA_FILE" && -n "$PROXY_HOST" ]]; then
#    rm -rf "$HOME/.pki/nssdb"
#    mkdir -p "$HOME/.pki/nssdb"
#    certutil -d "$HOME/.pki/nssdb" -N
#    certutil -d "sql:$HOME/.pki/nssdb" -A -t "C,," -n "Proxy" -i "$PROXY_CA_FILE"
#    rm "$PROXY_CA_FILE"
#fi

#mkdir ~/.config/
#mkdir ~/.config/google-chrome
#touch ~/.config/google-chrome/First\ Run

export QT_X11_NO_MITSHM=1

node index.js "$@"

NAME=${NAME:=zimfile}


warc2zim --url $URL --name $NAME --output=/output ./collections/capture/archive/*.warc.gz


