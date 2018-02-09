# -*- coding: utf-8 -*-

import threading
import time

s = ''

l = threading.Lock()


def a():
    global s

    for z in 'abcdefg':
        time.sleep(0.01)
        l.acquire()
        s += z
        l.release()


def b():
    global s

    for z in 'opqrst':
        time.sleep(0.01)
        s += z


t1 = threading.Thread(target=a)

t2 = threading.Thread(target=b)

t1.start()

t2.start()

time.sleep(0.1)

print s
