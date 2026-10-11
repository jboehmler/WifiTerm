#!/usr/bin/python3

import logging

# Logging needs to be configured before local imports to enable debug.log file
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.info)
# logging.basicConfig(format='%(levelname)s:%(message)s', filename = 'sslclient.log', level=logging.INFO)
FORMAT1 = "%(levelname)s:%(threadName)s:%(filename)s:%(funcName)s:\t%(message)s"
FORMAT2 = "%(levelname)s:%(filename)s:%(threadName)s:%(funcName)s:\t%(message)s"

# LOGLEVEL = logging.INFO
LOGLEVEL = logging.DEBUG

logging.basicConfig(
    format=FORMAT2,
    # filename="debug.log",
    # filemode="w",
    level=LOGLEVEL,
)

import queue
import threading

from pprint import pformat

QGETTIMEOUT = 1
QPUTTIMEOUT = 1


def new_event():
    new_ev = threading.Event()
    new_ev.clear()  # clear event by default
    return new_ev


class Task:
    def __init__(self, taskname):
        """
        Create a task with a lock, event, and included dictionary for task data.
        Event is used to start and pause task.
        """
        self.name = taskname
        self.taskloop = None
        self.taskfunc = None
        self.thread_lock = threading.Lock()
        # self.thread_lock.acquire()  #lock task in loop by default
        self.ev_run = threading.Event()
        self.ev_run.clear()  # pause task by default
        self.thread = None
        self.taskdata_dict = {}

    def set_pause(self):
        self.ev_run.clear()

    def set_run(self):
        self.ev_run.set()

    def is_paused(self):
        if self.ev_run.is_set():
            return False
        return True

    def is_running(self):
        return self.ev_run.is_set()

    def run_wait(self):
        self.ev_run.wait()

    def set_taskloop(self, taskloop_func):
        """
        Use a custom task loop.
        """
        self.taskloop = taskloop_func

    def set_taskfunc(self, taskfunc):
        """
        Task function assigned can be run within default loop.
        Default loop allows for starting and pausing.
        """
        self.taskfunc = taskfunc

    def set_taskdata(self, taskdata_dict):
        self.taskdata_dict = taskdata_dict

    def set_event(self, eventname):
        logging.debug(f"<{eventname}>")
        self.taskdata_dict[eventname].set()

    def clear_event(self, eventname):
        logging.debug(f"<{eventname}>")
        self.taskdata_dict[eventname].clear()

    def add_event(self, eventname):
        self.taskdata_dict[eventname] = threading.Event()
        self.clear_event(eventname)
        logging.debug(f"<{eventname}>")
        return self.taskdata_dict[eventname]

    def event_isset(self, eventname):
        logging.debug(f"<{eventname}>: <{self.taskdata_dict[eventname].is_set()}>")
        # logging.debug(f"event_isset taskdata_dict:  <{pformat(self.taskdata_dict)}>")
        return self.taskdata_dict[eventname].is_set()

    def def_taskloop(self):
        """
        Set up a task to run the function assigned to taskfunc within a loop.
        Loop can be started and paused by convenience events.
        Function to return true or false.
        """
        logging.debug("Task started.")
        logging.debug("Starting taskloop.")
        self.taskdata_dict["cnt"] = (
            0  # dict dummy entry for def_taskfunc dummy function to update
        )
        if self.is_paused():
            logging.debug("Waiting on initial pause.")
            self.run_wait()  # see if task is to stop temporarily
        while not self.thread_lock.acquire(blocking=False):
            logging.debug("Start loop.")
            if self.taskfunc():
                logging.debug("taskfunc returned True.")
            else:
                logging.debug("taskfunc returned False.")
            if self.is_paused():
                logging.debug("Waiting on taskloop pause.")
                self.run_wait()  # see if task is to stop temporarily
            logging.debug("End loop.")
        logging.debug("Ending taskloop.")
        logging.debug("Task ended.")

    def def_taskfunc(self):
        """
        Dummy task function to run in taskloop.
        Runs, updates taskdata_dict[cnt] with ++ then returns True.
        """
        logging.debug("def_taskfunc start")
        cnt = self.taskdata_dict["cnt"]
        logging.debug(f"taskdata_dict[cnt] is:  <{cnt}>")
        cnt += 1
        self.taskdata_dict["cnt"] = cnt
        logging.debug(f"taskdata_dict[cnt] is now:  <{cnt}>")
        logging.debug("def_taskfunc end")
        return True

    def config(self, taskloop_func=None, taskfunc=None, taskdata_dict=None):
        """
        Set up a task framework to customize task.
        If None, taskloop  = def_taskloop.
        If None, taskfunc = def_taskfunc.
        If None, taskdata_dict is an empty dict that will get an [eventname] key added for event data if threading events are used.
        """
        self.taskloop = taskloop_func
        if taskloop_func is None:
            logging.debug("set taskloop_func to default")
            self.taskloop = self.def_taskloop
        self.taskfunc = taskfunc
        if taskfunc is None:
            logging.debug("set taskfunc to default")
            self.taskfunc = self.def_taskfunc
        if taskdata_dict:
            logging.debug(f"set taskdata_dict to:\n<{pformat(taskdata_dict)}>")
            self.taskdata_dict = taskdata_dict
        self.thread = threading.Thread(target=self.taskloop, name=self.name)

    def start(self, runnow=None):
        """
        Start a task with option to pause before free running.
        runnow == True skips initial start up pause
        """
        self.thread_lock.acquire()
        if runnow is None:
            pass
        elif runnow:
            self.set_run()
        else:
            self.set_pause()
        self.thread.start()

    def stop(self):
        self.thread_lock.release()
        if self.is_running():
            return
        self.set_run()


def test_Task():
    """
    Test task creation with all defaults, start modes, and control.
    """
    from time import sleep

    logging.info("Create task")
    task = Task("testtask")
    logging.info("Sleep")
    sleep(1)
    logging.info("Config task")
    task.config()
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task initial start")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Start task")
    task.start()
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task in loop")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Stop task")
    task.stop()
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task to end loop")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("End of test")


def test_testfuncTask():
    """
    Create and control a task with a specified task function.
    """
    from time import sleep

    logging.info("Create task")
    task = Task("testfunctask")
    logging.info("Sleep")
    sleep(1)

    def testfunc():
        logging.debug("testfunc start")
        cnt = task.taskdata_dict["cnt"]
        logging.debug(f"taskdata_dict[cnt] is:  <{cnt}>")
        cnt += 1
        task.taskdata_dict["cnt"] = cnt
        logging.debug(f"taskdata_dict[cnt] is now:  <{cnt}>")
        logging.debug("testfunc end")
        return True

    logging.info("Config task")
    task.config(taskfunc=testfunc)
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task initial start")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Start task")
    task.start()
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task in loop")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Stop task")
    task.stop()
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task to end loop")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("End of test")


class QTask(Task):
    """
    Put and get data from a queue.
    """

    def __init__(self, taskname):
        super().__init__(taskname)
        self.queue = queue.Queue()

    def get(self, timeout=QGETTIMEOUT):
        """called function to get data put in queue by put
        Returns the data retrieved from the queue or None if the queue is EMPTY.
        """
        logging.debug("Starting get")
        data = None
        try:
            data = self.queue.get(timeout=timeout)
            logging.debug(f"task.get returned data\n<{pformat(data)}>")
        except queue.Empty:
            logging.debug("recv queue EMPTY")
        logging.debug("Ending get")
        return data

    def put(self, data, timeout=QPUTTIMEOUT):
        """called function to put data in queue for get to retrieve
        Returns True if the put was successful, False if not
        """
        logging.debug("Starting put")
        retval = False
        try:
            logging.debug(f"task.put queueing data\n<{pformat(data)}>")
            self.queue.put(data, timeout=timeout)
            retval = True
        except queue.Full:
            logging.debug("send queue FULL")
        logging.debug("Ending put")
        return retval

    def queue_isempty(self):
        return self.queue.empty()

    def queue_hasdata(self):
        return not self.queue.empty()


def test_QTask():
    """
    Create and control a task that reads and writes from queue.
    """
    from time import sleep

    def testfunc():
        logging.info("testfunc RUN.")
        data = task.get()
        logging.info(f"task.get returned data\n<{pformat(data)}>")
        data += 1
        task.put(data)
        logging.info(f"task.put queued data\n<{pformat(data)}>")
        logging.info("testfunc return.")
        return True

    logging.info("Create task")
    task = QTask("testqtask")
    logging.info("Sleep")
    sleep(1)
    logging.info("Config task")
    task.config(taskfunc=testfunc)
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task initial start")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Start task")
    task.start()
    logging.info("Sleep")
    sleep(1)
    logging.info("Initialize task counter with 0")
    task.put(0)
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("Pause task in loop")
    task.set_pause()
    logging.info("Sleep")
    sleep(1)
    logging.info("Stop task")
    task.stop()
    logging.info("Sleep")
    sleep(1)
    logging.info("Run task to end loop")
    task.set_run()
    logging.info("Sleep")
    sleep(1)
    logging.info("End of test")


if __name__ == "__main__":
    logging.info(f"Running <{__name__}>")
    logging.info(f"Running test_Task()")
    test_Task()
    logging.info(f"Running test_testfuncTask()")
    test_testfuncTask()
    logging.info(f"Running test_QTask()")
    test_QTask()
