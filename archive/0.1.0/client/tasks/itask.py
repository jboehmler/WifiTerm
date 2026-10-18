import logging

from tasks.qtask import QTask
from tasks.taskloop import task_loop

# ************************** Class ITask **************************
QGET_TIMEOUT = .1
QPUT_TIMEOUT = .1

#outside Class so that matches taskfunc signature
def recvfunc(taskdata):
    q = taskdata.get('queue')
    input_func = taskdata.get('input_func')
    data = input_func(taskdata)
    logging.debug(f"ITask recvfunc q.put data <{data}> input_func <{input_func}>")
    if data is None:
        return False

    q.put(data)
    return True

class ITask(QTask):
    '''
    Uses a QTask with the default taskloop and recvfunc as the taskfunc.
    Recvfunc retrieves data using input_func and puts it into the QTask queue.

    Recvfunc receives Task.taskdata like a Task taskfunc.
    input_func(taskdata = None) - returns data from source or None.
    if input_func returns None, recvfunc returns False with no action
    if input_func returns data, recvfunc puts data in q and returns True
    '''

    # ************************** Defaults **************************
    def __init__(self, taskname, input_func):
        logging.debug(f"ITask __init__")
        logging.debug(f"QTask Task __init__")

        #def taskloop by import
        super().__init__(taskname, task_loop, recvfunc)

        logging.debug(f"ITask Task __init__")
        self.set_inputfunc(input_func)

    def set_inputfunc(self, input_func):
        logging.debug(f"ITask set_inputfunc")
        self.datalib.set('loop:task:data:input_func', input_func)

    def itask_isready(self, exception = True):
        logging.debug(f"Check if task initialized.")
        if self.task_isready(exception):
            logging.debug(f"recvtask is ready")
            recvready = True
        else:
            logging.debug(f"recvtask is NOT ready")
            recvready = False

        if self.datalib.get('loop:task:data:input_func'):
            logging.debug(f"input_func is ready")
            inputready = True
        else:
            logging.debug(f"input_func is NOT ready")
            inputready = False

        ready = recvready and inputready
        if not ready:
            logging.critical(f"Task <{self.name}> is NOT ready recvready <{recvready}> inputready <{inputready}>.")
            if exception:
                raise RuntimeError

        return ready

    # ************************** Private methods **************************
    # inherit def get(self, timeout=QGETTIMEOUT):

if __name__ == "__main__":
    from time import sleep

    from pylib import logconfig

    #logconfig.set_loglevel('debug')

    # ************************** ITask test functions **************************
    def Test_InputFunc(taskdata):
        print("Type something:  ", end="")
        data = input()
        logging.debug(f"Input:  <{data}> received.")
        return data

    def Test_EndFunc(taskdata):
        logging.debug(f"Test_EndFunc.")
        return f"Test_EndFunc"

    def Test():
        '''
        Create and control a task that reads user input and then writes from queue.
        '''
        SLEEPTIME = 10

        #  Create and control a task with a specified task function.
        print(f"Test Start Test.")

        print(f"Test create task Test with function Test_InputFunc.")
        test_task = ITask("Test", Test_InputFunc)

        print(f"Test task started as paused.")
        sleep(1)
        test_task.start(paused = True)

        print(f"Test resume paused test_task.")
        test_task.resume()

        print(f"Test task running while main thread sleeps for {SLEEPTIME} seconds.")
        sleep(SLEEPTIME)

        print(f"End sleep.  Test task pause.")
        test_task.pause()
        print(f"Test change input func to Test_EndFunc.")
        test_task.set_inputfunc(Test_EndFunc)
        print(f"Test task resume.")
        test_task.resume()

        print(f"Test getting input data from queue.")
        sleep(1)
        print(f"Press Enter to end.")
        datalist = []
        while True:
            data = test_task.get()

            if data is None:
                continue

            #print(f"Test got input data <{data}> from queue.")
            if data == 'Test_EndFunc':
                print(f"Test got break data <{data}> from queue.")
                break

            datalist.append(data)

        print(f"Test end task.")
        while True:
            try:
                test_task.end()
                break

            except RuntimeError:
                print(f"Press Enter to end.")
                sleep(1)

        print(f"Test print results.")
        print(f"")
        print(f"")
        print(f"Test Results...........................................")
        print(f"Test Results...........................................")
        for data in datalist:
            print(f"data:  <{data}>")

        print(f"Test Results...........................................")
        print(f"Test Results...........................................")
        print(f"")
        print(f"")

        sleep(1)
        print("End Test task.")

    Test()
