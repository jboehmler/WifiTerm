'''
Interact directly with user via screen and keyboard
Key strokes are collected and put into Queue
'''
import logging

from pylib import asciiinfo
from pylib.keys import ESCKEY

from term.rawterm import RawTerm
from tasks.iotask import IOTask

SEND_TIMEOUT = 1
RECV_TIMEOUT = 1

# ************************** Class TermIOTask **************************
# create an IOTask with rawmode and readline methods
def InputFunc(taskdata):
    term = taskdata.get('rawterm')
    logging.debug(f"InputFunc Start")
    term = taskdata.get('rawterm')
    data = term.get_key()
    logging.debug(f"InputFunc get_key data <{asciiinfo.ascstr(data)}>")
    if data is None:
        return None

    #data = data.strip()
    logging.debug(f"InputFunc Input:  data <{asciiinfo.ascstr(data)}> received")
    return data

def OutputFunc(taskdata, data):
    logging.debug(f"OutputFunc Start")
    logging.debug(f"OutputFunc data <{asciiinfo.ascstr(data)}>")
    if data is None:
        return None

    term = taskdata.get('rawterm')
    logging.debug(f"OutputFunc term.print data <{asciiinfo.ascstr(data)}>")
    term.print(f"{data}", end = "")
    return None

def EndFunc(taskdata):
    #print(f"EndFunc <{taskdata.EndFunc}>.")
    return f"EndFunc"

class TermIOTask():
    # ************************** Defaults **************************
    def __init__(self, taskname, inputfunc = InputFunc, outputfunc = OutputFunc):
        logging.debug(f"TermIOTask __init__")

        logging.debug(f"Set up io tasks.")
        self.task = IOTask(taskname, inputfunc, outputfunc)

        logging.debug(f"Set up raw terminal.")
        self.term = RawTerm()
        self.task.set_iodata('rawterm', self.term)

# ************************** MAIN Test **************************
if __name__ == "__main__":
    from pylib import logconfig

    from time import sleep

    logconfig.init('debug', logconfig.FORMAT1)

    def Test_OutputFunc(taskdata, data):
        logging.debug(f"Test_OutputFunc Start")
        if data is None:
            return None

        term = taskdata.get('rawterm')
        term.print(f"Test_OutputFunc...........................................")
        term.print(f"Test_OutputFunc...........................................")
        term.print(f"Test_OutputFunc OutputFunc data <", end = "")
        OutputFunc(taskdata, data)
        term.print(f"> sent.")
        term.print(f"Test_OutputFunc...........................................")
        term.print(f"Test_OutputFunc...........................................")
        logging.debug(f"Test_OutputFunc end")
        return None

    # ************************* TermIOTask test functions **************************
    def TermIOTest_Task():
        '''
        Create and control a task that reads user input and then writes from queue.
        '''
        def logprint(*args, **kwargs):
            termtask.term.print(*args, **kwargs)
            logging.debug(*args, **kwargs)


        def termecho():
            termtask.term.print(f"TermIOTest_Task termecho echo data.")
            termtask.term.print(f"TermIOTest_Task termecho get data from RecvFunc queue.")
            while True:
                data = termtask.task.get()
                if data is None:
                    termtask.term.print(f"TermIOTest_Task termecho type something.  ", end = "")
                    if termtask.term.rawmode:
                        termtask.term.print(f"ESC to end:  ", end = "")
                    else:
                        termtask.term.print(f"ESC Enter to end:  ", end = "")
                    sleep(1)
                    termtask.term.print("")
                    continue

                termtask.term.print(f"TermIOTest_Task termecho got input data <{data}> from queue.")
                if ESCKEY in data:
                    break

                termtask.term.print(f"TermIOTest_Task termecho put data into SendFunc queue.")
                termtask.task.put(data)


        print(f"Starting Test_TermIOTask...")
        logging.debug(f"Starting Test_TermIOTask...")
        termtask = TermIOTask("TermIOTask", outputfunc = Test_OutputFunc)

        logprint(f"TermIOTest_Task Start tasks.")
        termtask.task.start()

        logprint(f"TermIOTest_Task task running.")
        logprint(f"TermIOTest_Task waiting for input...")

        termecho()

        logprint(f"TermIOTest_Task task pause.")
        termtask.task.pause()

        logprint(f"TermIOTest_Task set_rawmode.")
        termtask.term.set_rawmode()
        logprint(f"TermIOTest_Task task resume.")
        termtask.task.resume()

        termecho()

        logprint(f"TermIOTest_Task task pause.")
        termtask.task.pause()

        logprint(f"TermIOTest_Task set_readline.")
        termtask.term.set_readline()
        logprint(f"TermIOTest_Task task resume.")
        termtask.task.resume()

        termecho()

        logprint(f"TermIOTest_Task task pause.")
        termtask.task.pause()
        logprint(f"TermIOTest_Task change io funcs to end funcs.")
        termtask.task.set_EndFunc, 'both')
        logprint(f"TermIOTest_Task task resume.")
        termtask.task.resume()

        logprint(f"TermIOTest_Task end task.")
        logprint(f"TermIOTest_Task Press Enter to end.")

        while True:
            try:
                termtask.task.end()
                break

            except RuntimeError:
                logprint(f"Press Enter to end.")

        logprint(f"TermIOTest_Task End TermIOTest_Task task.")
        sleep(1)

        logprint("End TermIOTest_Task task.")


    TermIOTest_Task()
