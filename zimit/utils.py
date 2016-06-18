import os
import os.path
import shlex
import subprocess


def spawn(cmd):
    """Quick shortcut to spawn a command on the filesystem"""
    return subprocess.Popen(shlex.split(cmd))


def ensure_paths_exists(*paths):
    for path in paths:
        if not os.path.exists(path):
            msg = '%s does not exist.' % path
            raise OSError(msg)


def read_fifo(filename):
    with open(filename) as fifo:
        while os.path.exists(filename):
            yield fifo.readline()
