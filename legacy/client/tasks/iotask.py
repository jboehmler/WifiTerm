from pylib import logconfig
from pylib.logconfig import logging

from time import sleep
from pprint import pformat

from pylib.datalib import DataLib
from tasks import itask, otask

# ************************** Class IOTask **************************
class IOTask:
    # ************************** Defaults **************************
    def __init__(self, taskname, input_func, output_func):
        '''
        Create two tasks that asynchronously fill and empty two queues:
        o run a function to retrieve data and put into an input Queue (recv function inside recv task)
        o recv function gets data and puts it into the IOTask recv Queue
        o run a function to get data from a Queue and process it (send function inside send task)
        o send function gets data from the IOTask send Queue and outputs it
        o functions are run as tasks in parallel
        o both tasks share a task dictionary and each has its own dictionary under the keys recvdict and senddict
        Task controls affect both tasks simultaneously

        Each IOTask is created with a default function and loop with thread controls.  The task can then
        run the default function or a custom one in the default loop or a custom one.

        The set_taskloop, set_taskfunc, and set_taskdata functions should be used to customize each task.
        If desired, a custom task loop or function can be created using def_taskloop and/or def_taskfunc(self)
        as examples.

        IOTask:
            sendtask
                main -> put -> sendq -> output_func(output_func(data)) -> sink
            recvtask
                main <- get <- recvq <- recvfunc(input_func()) <- source

        input_func() - returns data from source or None
        output_func(data) - returns True or False
        '''

        logging.debug(f"IOTask __init__")
        self.name = taskname # name for the IOTask itself
        logging.debug(f"Create IOTask {self.name} input_func <{input_func}> sendfunc <{output_func}>.")

        self.itask = itask.ITask("ITask", input_func)
        self.otask = otask.OTask("OTask", output_func)

        self.datadict = {
        }
        self.datalib = DataLib(self.name, self.datadict)
        logging.debug(f"IOTask <{self.name}> __init__ Task self.datalib.")
        self.datalib.log_datalib()
        self.iotask_isready()

    # ************************** Configuration **************************
    # set subtask properties
    def set_iofunc(self, func, task = 'both'):
        logging.debug(f"IOTask Task <{self.name}> set_iofunc task <{task}>.")
        if task == 'input' or task == 'both':
            self.itask.set_inputfunc(func)

        if task == 'output' or task == 'both':
            self.otask.set_outputfunc(func)

        return True

    def set_iodata(self, key, data, task = 'both'):
        logging.debug(f"IOTask Task <{self.name}> set_iotask key <{key}> data <{data}> task <{task}>.")
        if task == 'input' or task == 'both':
            self.itask.set_taskdata(key, data)

        if task == 'output' or task == 'both':
            self.otask.set_taskdata(key, data)

        return True


    # ************************** Status methods **************************
    def get(self):
        data = self.itask.get()
        return data

    def put(self, data):
        retval = self.otask.put(data)
        return retval

    def iotask_isready(self, exception = True):
        logging.debug(f"IOTask Check if tasks initialized.")
        if self.itask.itask_isready(exception):
            logging.debug(f"ITask recvtask is ready")
            recvready = True
        else:
            logging.debug(f"ITask recvtask is NOT ready")
            recvready = False

        if self.otask.otask_isready(exception):
            logging.debug(f"OTask sendtask is ready")
            sendready = True
        else:
            logging.debug(f"OTask sendtask is NOT ready")
            sendready = False

        ready = recvready and sendready
        if ready:
            return True

        logging.critical(f"IOTask Task <{self.name}> is NOT ready recvready <{recvready}> sendready <{sendready}>.")
        if exception:
            raise RuntimeError

        return False

    # ************************** Control methods **************************
    def start(self, task = 'both'):
        # task can be 'recv', 'send', or 'both'
        logging.debug(f"IOTask Task <{self.name}> start task <{task}>.")
        if task == 'recv' or task == 'both':
            recvstarted = self.itask.start()

        if task == 'send' or task == 'both':
            sendstarted = self.otask.start()

        sleep(1) #give tasks time to start
        taskstarted = recvstarted and sendstarted
        if taskstarted:
            logging.debug("Tasks started.")
            return True

        logging.critical(f"IOTask Task <{self.name}> is NOT started recvstarted <{recvstarted}> sendstarted <{sendstarted}>.")
        if exception:
            raise RuntimeError
        return False

    def pause(self, task = 'both'):
        # task can be 'recv', 'send', or 'both'
        logging.debug(f"IOTask Task <{self.name}> pause task <{task}>.")
        if task == 'recv' or task == 'both':
            self.itask.pause()

        if task == 'send' or task == 'both':
            self.otask.pause()

    def resume(self, task = 'both'):
        # task can be 'recv', 'send', or 'both'
        logging.debug(f"IOTask Task <{self.name}> resume task <{task}>.")
        if task == 'recv' or task == 'both':
            self.itask.resume()

        if task == 'send' or task == 'both':
            self.otask.resume()

    def end(self, task = 'both'):
        # task can be 'recv', 'send', or 'both'
        logging.debug(f"IOTask Task <{self.name}> end task <{task}>.")
        if task == 'recv' or task == 'both':
            recvend = self.itask.end()

        if task == 'send' or task == 'both':
            sendend = self.otask.end()

        taskend = recvend and sendend
        if taskend:
            logging.debug("Tasks stopped.")
            return True

        logging.critical(f"IOTask Task <{self.name}> is NOT ended recvend <{recvend}> sendend <{sendend}>.")
        if exception:
            raise RuntimeError
        return False


if __name__ == "__main__":
    # ************************** IOTask test functions **************************
    def Test_InputFunc(taskdata):
        data = input()
        logging.debug(f"Input:  <{data}> received.")
        return data

    def Test_OutputFunc(taskdata, data):
        logging.debug(f"Test_OutputFunc Start <{Test_OutputFunc}>.")
        if data is None:
            return None

        print(f"Test_OutputFunc...........................................")
        print(f"Test_OutputFunc...........................................")
        print(f"Test_OutputFunc:  <{data}> sent.")
        print(f"Test_OutputFunc...........................................")
        print(f"Test_OutputFunc...........................................")
        return None

    def Test_EndFunc(taskdata, data = None):
        logging.debug(f"Test_EndFunc.")
        return f"Test_EndFunc"

    def Test():
        '''
        Create and control a task that reads user input and then writes from queue.
        '''
        #  Create and control a task with a specified task function.
        print(f"Test Start Test.")

        logconfig.init('debug', logconfig.FORMAT1)

        print(f"Test Create task Test.")
        test_task = IOTask("Test", Test_InputFunc, Test_OutputFunc)

        # use function defined of the IOTask class
        print(f"Test Start test Test_Func.")

        print(f"Test task start.")
        test_task.start()

        print(f"Test task pause.")
        test_task.pause()

        print(f"Test Resume started test_task.")
        test_task.resume()

        print(f"Test task running.")
        print(f"Test waiting for input...")
        while True:
            print(f"Test echo data.")
            print(f"Test get data from InputFunc queue.")
            data = test_task.get()
            if data is None:
                print(f"Test type something, q Enter to end:")
                sleep(1)
                continue

            print(f"Test got input data <{data}> from queue.")
            if data == 'q':
                break

            print(f"Test put data into OutputFunc queue.")
            test_task.put(data)

        print(f"Test task pause.")
        test_task.pause()

        print(f"Test change io funcs to end funcs.")
        test_task.set_iofunc(Test_EndFunc, 'both')
        print(f"Test task resume.")
        test_task.resume()

        print(f"Test end task.")
        print(f"Test Press Enter to end.")

        while True:
            sleep(1)
            try:
                test_task.end()
                break

            except RuntimeError:
                print(f"Press Enter to end.")

        print(f"Test End Test task.")
        sleep(1)

        print("End Test task.")


    print(f"************************************************************")
    print(f"Running Test()")
    Test()
