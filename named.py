import os
import shlex
import subprocess


def spawn(cmd):
    os.mkfifo("toto")
    with open("toto", "w") as f:
        process = subprocess.Popen(shlex.split(cmd), stdout=f)
    process.wait()
    os.unlink("toto")

spawn("stdbuf -o0 python test.py")
