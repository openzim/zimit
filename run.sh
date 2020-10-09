#!/bin/bash

output_dir="/output"
chmod a+w $output_dir

res=1

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

redis-server &> /dev/null &

wb-manager init capture
uwsgi $curr/uwsgi.ini &> /dev/null &

# needed for chrome
export QT_X11_NO_MITSHM=1

cleanup() {
  # if not keeping, delete temp dir
  if [[ -z $keep ]]; then
    echo "Removing temp dir $tmpdir"
    rm -rf $tmpdir
  fi
  exit $res
}

trap cleanup SIGINT
trap cleanup SIGTERM

su zimit -c "node $curr/index.js $cmd"

res="$?"

popd

cleanup

