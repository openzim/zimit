from __future__ import print_function
import os
import os.path


def read_fifo(filename):
    with open(filename) as fifo:
        while os.path.exists(filename):
            print(fifo.readline(), end='')

read_fifo("toto")
