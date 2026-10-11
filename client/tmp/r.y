#!/usr/bin/python3

from time import time, sleep
import c

if __name__ == "__main__":
    cnt = 0
    t0 = time()
    while True:
        try:
            print(f"Start test:")
            c.test()
            cnt += 1
            t1 = time()
            print(f"End test:  <{cnt}> times over <{t1 - t0}> secs")
            sleep(1)
        except KeyboardInterrupt:
            break
    t1 = time()
    print(f"Repeated <{cnt}> times in <{t1 - t0}> seconds.")
