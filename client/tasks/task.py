from pylib import logconfig
from pylib.logconfig import logging

import threading
from time import sleep

from pprint import pformat

from pylib.datalib import DataLib

ENDTIMEOUT = 10 #secs
## Task description
# loopfunc - the actual code run by the task thread
# taskfunc - the code run as the unique code if used in the taskloop.py
# taskloop.  If used in the taskloop, taskfunc is called with a DataLib at:
#     Task.datadict:'loop:task:data'
#
# Init
#
#  task takes a DataLib as its argument
#  task only has access to the Task's DataLib class instance
#  task should never try to control Task except through global task functions
#
#  this example func uses 'cnt' entry in DataLib to store current count
#  between calls
#  if 'cnt' is not in DataLib on first call, initialize it to zero
#  each call increments the cnt and prints it

#  task loop only has access to the Task's DataLib for data
#  task should never try to control Task except through global task functions
#  General task loop flow is:
#    Start
#        init section that calls <init_func> if not None
#    Loop
#        loop section that repeats if loop.lock has been locked with <start_loop>
#        <code>
#        <task func> run external code
#        <code>
#        wait_resume <- blocks Loop, controlled by <pause> and <resume> external functions
#        <code>
#    <end_loop> allows loop to break
#    close section that calls <close_func> if not None
#    clean up from loop
#    End
#    
#  Set up a task to run the function assigned to func within a loop.
#  By default, unless paused, the loop begins the main loop when started.
#  func will be called with an argument of self inside loop.
#  Loop can be started and paused by convenience events.
#  Function to return true or false.


# ************************** Class Task **************************
class Task:
    # ************************** Defaults **************************
    # default task function and loop defined for __init__ defaults
    def __init__(self, taskname, loopfunc = None, taskfunc = None, exception = True):
        logging.debug(f"Start Task __init__")
        logging.debug(f"Task __init__ set properties")

        logging.debug(f"Task __init__ set name to {taskname}.")
        self.name = taskname
        # set up data
        self.datadict = {
                'loop': {
                    'func': None,
                    'data': {},
                    'task': {
                        'func': None,
                        'data': {},
                        },
                    },
                }
        self.datalib = DataLib(self.name, self.datadict)


        # self.loopfunc set by set_loopfunc since val needs to be updated if changed
        # self.loopfunc used by task_isready
        self.set_loopfunc(loopfunc)

        # self.taskfunc set by set_taskfunc since val needs to be updated if changed
        # self.taskfunc used by task_isready
        self.set_taskfunc(taskfunc)

        self.loop = self.Loop(taskname, self.datalib.get('loop'))

        logging.debug(f"Task <{self.name}> __init__ Task self.datalib.")
        self.datalib.log_datalib()
        self.task_isready(exception)

    def set_loopfunc(self, loopfunc):
        self.loopfunc = self.datalib.set('loop:func', loopfunc)
        return True

    def set_taskfunc(self, taskfunc):
        self.taskfunc = self.datalib.set('loop:task:func', taskfunc)
        return True

    def set_taskdata(self, key, data):
        self.taskfunc = self.datalib.set(f'loop:task:data:{key}', data)
        return True

    def task_isready(self, exception = True):
        if self.loopfunc:
            logging.debug(f"Task <{self.name}> self.loopfunc is ready.")
            loopready = True
        else:
            logging.warning(f"Task <{self.name}> self.loopfunc is NOT ready.")
            loopready = False

        if self.taskfunc:
            logging.debug(f"Task <{self.name}> self.taskfunc is ready.")
            taskready = True
        else:
            logging.warning(f"Task <{self.name}> self.taskfunc is NOT ready.")
            taskready = False

        ready = loopready and taskready
        if not ready:
            logging.critical(f"Task <{self.name}> is NOT ready loopready <{loopready}> taskready <{taskready}>.")
            if exception:
                raise RuntimeError

        return ready

    def start(self, paused = False, exception = True):
        # return True if loop started, False if error
        logging.debug(f"Task <{self.name}> start.")

        logging.debug(f"Task <{self.name}> start pause.")
        self.pause()

        logging.debug(f"Task <{self.name}> start loop lock.")
        started = self.loop.lock()

        # set up task loop thread
        self.thread = threading.Thread(name=self.name, target=self.loopfunc,
                                       args = (self.loop,))

        logging.debug(f"Task <{self.name}> start thread.")
        self.thread.start()

        if not self.thread.is_alive():
            logging.debug(f"Task <{self.name}> start loop failed to start cnt <{startcnt}>.")
            if exception:
                raise RuntimeError
            return False

        logging.debug(f"Task <{self.name}> start thread started.")
        if paused:
            logging.warning(f"Task <{self.name}> start thread PAUSED.")
        else:
            self.resume()

        return True

    def join(self):
        self.thread.join()

    def pause(self):
        # controls task loop, setting will make task loop block at wait_resume
        # clear the run event flag to block a wait_resume - pauses loop
        logging.debug(f"Task <{self.name}> pause.")
        self.loop.set_status('paused', True)
        self.loop.ev_taskrun.clear()

    def resume(self):
        # controls task loop, setting will make task loop unblock at wait_resume
        # set the run event flag to unblock wait_resume - unpauses loop
        logging.debug(f"Task <{self.name}> resume.")
        self.loop.set_status('paused', False)
        self.loop.ev_taskrun.set()

    def end(self, exception = True):
        # return True if loop started, False if error
        logging.debug(f"Task <{self.name}> start end.")
        logging.debug(f"Task <{self.name}> end pause.")
        self.pause()
        logging.debug(f"Task <{self.name}> end loop status:")
        logging.debug(f"{self.loop_status_dict}")

        logging.debug(f"Task <{self.name}> end loop unlock.")
        ready = False
        endcnt = ENDTIMEOUT
        while endcnt:
            ready = self.loop.unlock()
            if ready:
                logging.debug(f"Task <{self.name}> end loop unlocked.")
                ready = True
                break

            endcnt -= 1
            logging.debug(f"Task <{self.name}> end loop NOT unlocked endcnt <{endcnt}>.")
            logging.debug(f"Loop <{self.name}> Wait 1 second to try again.")
            sleep(1)

        if not ready:
            logging.debug(f"Task <{self.name}> end loop NOT unlocked.")
            if exception:
                raise RuntimeError

            return False

        logging.debug(f"Task <{self.name}> end resume.")
        self.resume()

        ready = False
        endcnt = ENDTIMEOUT
        while endcnt:
            ready = not self.thread.is_alive()
            if ready:
                logging.debug(f"Task <{self.name}> thread ended.")
                ready = True
                break

            endcnt -= 1
            logging.debug(f"Task <{self.name}> end thread is still alive endcnt <{endcnt}>.")
            logging.debug(f"Loop <{self.name}> Wait 1 second to try again.")
            sleep(1)

        if not ready:
            logging.debug(f"Task <{self.name}> end thread still alive.")
            if exception:
                raise RuntimeError

            return False

        logging.debug(f"Task <{self.name}> end thread ended.")
        return True


    # ************************** Class Loop **************************
    class Loop:
        def __init__(self, name, loopdata):
            # set up loop data
            self.name = name
            self.loop_status_dict = {
                    'started':  False,
                    'running':  False,
                    'paused':   False,
                    'waiting':  False,
                    'locked':   False,
                    'ended':    False,
                    }

            self.loopdata = DataLib('loopdata', loopdata)
            self.loopdata.set('status', self.loop_status_dict)
            self.loopstatus = DataLib('loopstatus', self.loopdata.get('status'))
            self.taskfunc = self.loopdata.get('task:func')
            self.taskdata = DataLib('taskdatalib', self.loopdata.get('task:data'))
            self.ev_taskrun = threading.Event()
            self.looplock = threading.Lock()

        def set_status(self, statusstr, status):
            if statusstr in self.loop_status_dict:
                self.loopstatus.set(f'{statusstr}', status)
                return status

            logging.debug(f"set_status:  status <{statusstr}> not in status options <{self.statuslist}>.")
            raise KeyError

        def get_status(self, statusstr):
            status = self.loopstatus.get(f'{statusstr}')
            logging.debug(f"Loop <{self.name}> {statusstr}:  {status}.")
            return status

        #  set task loop to stay in loop
        def lock(self):
            logging.info(f"Start lock <{self.name}...")
            if self.get_status('locked'):
                logging.critical(f"lock trying to lock locked loop.")
                raise RuntimeError

            acquired = self.looplock.acquire(blocking = False)
            if acquired:
                logging.debug(f"Loop <{self.name}> lock acquired, set locked True.")
                self.set_status('locked', True)
                return True

            logging.debug(f"Loop <{self.name}> lock NOT acquired.")
            return False

        def wait_resume(self):
            # if pause was called, blocks task loop at this point
            # if paused, wait for resume to continue past block
            logging.debug(f"wait_resume start wait_resume.")
            logging.debug(f"wait_resume paused is <{self.get_status('paused')}>.")
            if not self.ev_taskrun.is_set():
                self.set_status('waiting', True)
                logging.debug(f"wait_resume waiting...")
            self.ev_taskrun.wait()
            self.set_status('waiting', False)
            logging.debug(f"wait_resume wait done...")

        #  set task loop to exit loop
        def unlock(self):
            logging.info(f"Start unlock <{self.name}...")
            if not self.get_status('locked'):
                logging.critical(f"unlock trying to unlock unlocked loop.")
                raise RuntimeError

            self.looplock.release()
            locked = self.looplock.locked()
            if locked:
                logging.debug(f"Loop <{self.name}> lock NOT unlocked.")
                return False

            logging.debug(f"Loop <{self.name}> lock unlocked.")
            self.set_status('locked', False)
            return True


# ************************** Task Test **************************
if __name__ == "__main__":
    # Test default task loop using a test function to run as a task.
    from tasks.taskloop import task_loop
    from tasks.tasktests import Test_Cycle

    def Test_Func(datalib):
        print("Start Test_Func.")

        print("Test_Func get cnt.")
        cnt = datalib.get('cnt')
        if cnt is None:  #  DataLib get of a non-existent key returns None
            print("Test_Func cnt is None, initializing to zero.")
            cnt = 0
            datalib.set('cnt', cnt)

        print(f"Test_Func current cnt:  <{cnt}>.")
        cnt += 1
        cnt = datalib.set('cnt', cnt)
        cnt = datalib.get('cnt')
        print(f"Test_Func new cnt:  <{cnt}>.")

        print("End Test_Func.")
        return True

    def Test():
        #  Create and control a task with a specified task function.
        print(f"Test Start Test.")

        print(f"Test Create task Test.")
        test_task = Task("Test", task_loop, Test_Func)

        # use function defined of the Task class
        print(f"Test Start test Test_Func.")

        print(f"Test Initialize taskdata with count of zero.")
        test_task.datalib.set("loop:task:data:cnt")

        print(f"Test Start Test_Cycle Test_Func.")
        print(f"Test Running Test_Cycle Test_Func while main thread sleeps.")
        Test_Cycle(test_task, 'Test', 'Test_Func')
        print(f"Main thread sleeping as test task runs in separate thread.")
        sleep(3)
        print(f"Test End Test_Cycle Test_Func.")

        print(f"Test Remove taskdata key <cnt>.")
        sleep(2)
        test_task.datalib.remove("loop:task:data:cnt")

        print(f"Test End Test task.")
        sleep(1)
        print("End Test task.")

    Test()
