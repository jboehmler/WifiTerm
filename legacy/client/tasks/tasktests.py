# module with tests for use in Tests in task modules.

from time import sleep

# ************************** Task test functions **************************
def Test_Cycle(task, caller, msg):
    print(f"{caller}:Test_Cycle Start Test_Cycle:  <{msg}>.")
    print(f"{caller}:Test_Cycle task start paused.")
    sleep(1)
    task.start(paused = True)

    print(f"{caller}:Test_Cycle Resume started task.")
    task.resume()

    print(f"{caller}:Test_Cycle run task.")
    sleep(1)

    print(f"{caller}:Test_Cycle Pause task in loop.")
    task.pause()

    print(f"{caller}:Test_Cycle task paused.")
    sleep(1)

    print(f"{caller}:Test_Cycle resume task in loop.")
    task.resume()

    print(f"{caller}:Test_Cycle run task.")
    sleep(1)

    print(f"{caller}:Test_Cycle End task.")
    task.end()

    print(f"{caller}:Test_Cycle End Test_Cycle:  <{msg}>.")
