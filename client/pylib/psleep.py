from time import sleep

def psleep(secs, msg, showsecs = False):
    showdone = False
    if secs > 0:
        showdone = True

    if showsecs:
        while secs > 1:
            print(f"Psleep <{secs}> secs:  <{msg}>.")
            secs -= 1
            sleep(1)

    print(f"Psleep <{secs}> secs:  <{msg}>.")
    sleep(secs)
    if showdone:
        print(f"Psleep <{msg}> DONE.")

