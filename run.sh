#!/bin/bash

output_dir="/output"

for val in "$@"
do
  if [[ $val == "-o" ]] || [[ $val == "--output" ]]; then
    output_dir="$2"
  
  elif [[ $val == "--keep" ]]; then
    keep="1"
  fi
done

cmd="$@"

curr=$(pwd)

tmpdir=$(mktemp -d --tmpdir=$output_dir)

chmod a+rx $tmpdir

echo "output_dir: $tmpdir"

pushd $tmpdir

wb-manager init capture
uwsgi $curr/uwsgi.ini &> /dev/null &

# needed for chrome
export QT_X11_NO_MITSHM=1

su zimit -c "node $curr/index.js $cmd"

popd


# if not keeping, delete temp dir
if [[ -z $keep ]]; then
  echo "Removing temp dir $tmpdir"
  rm -rf $tmpdir
fi

