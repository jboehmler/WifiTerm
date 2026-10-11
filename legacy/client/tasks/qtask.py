from pylib import logconfig
from pylib.logconfig import logging

import threading
import queue

from pprint import pformat

from tasks.task import Task
from pylib.datalib import DataLib

# ************************** Class QTask **************************
# QGETTIMEOUT = 1
# QPUTTIMEOUT = 1
QGETTIMEOUT = .1
QPUTTIMEOUT = .1

class QTask(Task):
    '''
    Task to put and get data from a queue.  Combines the thread functionality with Queues.  The QTask
    is intended for the definition of a task function to do processing and put data in the queue or remove
    data from the queue and process it.  The class also includes get and put functions for external functions
    to interact with the queue.

    General use will be to create a task with a function that is run within the task loop.  The task
    will run and either get data from or put data into the queue.  The data in the queue can then be either
    gotten or put by another part of the program by calling the class' getq or putq function.

    The typical use will define a custom function that is to be run as a thread.  The function generally will
    process data, such as receiving text via I/O and putting it into the queue to be used by an external
    function.  The use of a thread means that even if the I/O task blocks, other threads can run and the system
    can perform other tasks or even other QTasks.

    Test_QTask after the class definition demonstrates some of the set up and features of a task by having data
    put into the queue and letting the task run.  The task gets data from the queue, manipulates it and puts
    the new data into the queue for the next pass.

    See task.py for datadict structure.
    '''

    # ************************** Defaults **************************
    def __init__(self, taskname, loopfunc, taskfunc):
        logging.debug(f"QTask Task __init__")
        super().__init__(taskname, loopfunc, taskfunc)
        logging.debug(f"QTask __init__")
        self.task_queue = self.TaskQueue(taskname)
        self.loop.taskdata.set('queue', self.task_queue)

    def queue_isempty(self):
        return self.task_queue.empty()

    def queue_hasdata(self):
        return not self.task_queue.empty()

    def get(self, timeout=QGETTIMEOUT):
        data = self.task_queue.get(timeout=timeout)
        return data

    def put(self, data, timeout=QPUTTIMEOUT):
        data = self.task_queue.put(data, timeout=timeout)
        return True


    class TaskQueue(queue.Queue):
        # ************************** Configuration **************************

        def __init__(self, taskname):
            super().__init__()
            self.name = taskname

        # ************************** Status methods **************************
        def queue_isempty(self):
            return self.empty()

        def queue_hasdata(self):
            return not self.empty()


        # ************************** Control methods **************************


        # ************************** Interaction methods **************************
        def get(self, timeout=QGETTIMEOUT):
            """called function to retrieve data in queue.Queue put in queue by "put" method
            Returns the data retrieved from the queue or None if the queue is EMPTY.
            """
            logging.debug(f"QTask <{self.name}> Starting get.")
            data = None
            try:
                data = super().get(timeout=timeout)
                logging.debug(f"QTask <{self.name}> get returned data <{pformat(data)}>.")
            except queue.Empty:
                logging.debug(f"QTask <{self.name}> recv queue EMPTY.")
            logging.debug(f"QTask <{self.name}> Ending get.")
            return data

        def put(self, data, timeout=QPUTTIMEOUT):
            """called function to put data in queue.Queue for "get" to retrieve
            Returns True if the put was successful, False if not
            """
            logging.debug(f"QTask <{self.name}> Starting put.")
            retval = False
            try:
                logging.debug(f"QTask <{self.name}> task.put queueing data <{pformat(data)}>.")
                super().put(data, timeout=timeout)
                retval = True
            except queue.Full:
                logging.debug(f"QTask <{self.name}> send queue FULL.")
            logging.debug(f"QTask <{self.name}> Ending put.")
            return retval


if __name__ == "__main__":
    from time import sleep

    from tasks.taskloop import task_loop
    from tasks.tasktests import Test_Cycle

    # ************************** QTask test functions **************************
    def Test_Func(datalib):
        print("Test_func run.")
        q = datalib.get('queue')
        cnt = q.get()
        print(f"q.get returned cnt <{cnt}>.")
        cnt += 1
        q.put(cnt)
        print(f"q.put queued cnt <{cnt}>.")
        print("Test_func return.")
        return True


    def Test():
        '''
        Create and control a task that reads and writes from queue.
        '''
        #  Create and control a task with a specified task function.
        print(f"Test Start Test.")

        print(f"Test Create task Test.")
        test_task = QTask("Test", task_loop, Test_Func)

        # use function defined of the QTask class
        print(f"Test Start test Test_Func.")

        print(f"Initialize queue with test_task.put count of zero.")
        test_task.put(0)

        print(f"Test Start Test_Cycle Test_Func.")
        Test_Cycle(test_task, 'Test', 'Test_Func')
        print(f"Test End Test_Cycle Test_Func.")

        print(f"Test End Test task.")
        sleep(1)
        print("End Test task.")

    Test()
