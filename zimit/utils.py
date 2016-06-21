import os
import shlex
import subprocess


def spawn(cmd, logfile=None):
    """Quick shortcut to spawn a command on the filesystem"""
    if logfile is not None:
        with open(logfile, "a+") as f:
            prepared_cmd = shlex.split("stdbuf -o0 %s" % cmd)
            process = subprocess.Popen(prepared_cmd, stdout=f)
    else:
        prepared_cmd = shlex.split(cmd)
        process = subprocess.Popen(prepared_cmd)
    process.wait()
    return process


def ensure_paths_exists(*paths):
    for path in paths:
        if not os.path.exists(path):
            msg = '%s does not exist.' % path
            raise OSError(msg)


def get_command(cmd, *params, **options):
    prepared_options = []
    for key, value in options.items():
        if value is None:
            opt = "--%s" % key
        else:
            opt = "--%s=%s" % (key, value)
        prepared_options.append(opt)

    return " ".join((cmd, " ".join(params), " ".join(prepared_options)))
