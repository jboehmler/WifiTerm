import logging

from tasks.qtask import QTask
from tasks.taskloop import task_loop

#outside Class so that matches taskfunc signature
def sendfunc(taskdata):
    q = taskdata.get('queue')
    output_func = taskdata.get('output_func')
    data = q.get()
    logging.debug(f"OTask sendfunc q.get data <{data}> output_func <{output_func}>")
    retval = output_func(taskdata, data)
    return retval

# ************************** Class OTask **************************
QGET_TIMEOUT = .1
QPUT_TIMEOUT = .1

class OTask(QTask):
    '''
    output_func(data) - returns data not sent or None
    '''

    # ************************** Defaults **************************
    def __init__(self, taskname, output_func):
        logging.debug(f"OTask __init__")
        logging.debug(f"QTask Task __init__")

        #def taskloop by import
        super().__init__(taskname, task_loop, sendfunc)

        logging.debug(f"OTask Task __init__")
        self.set_outputfunc(output_func)


    def set_outputfunc(self, output_func):
        logging.debug(f"OTask set_outputfunc")
        self.datalib.set('loop:task:data:output_func', output_func)

    def otask_isready(self, exception = True):
        logging.debug(f"Check if task initialized.")
        if self.task_isready(exception):
            logging.debug(f"sendtask is ready")
            sendready = True
        else:
            logging.debug(f"sendtask is NOT ready")
            sendready = False

        if self.datalib.get('loop:task:data:output_func'):
            logging.debug(f"output_func is ready")
            outputready = True
        else:
            logging.debug(f"output_func is NOT ready")
            outputready = False

        ready = sendready and outputready
        if not ready:
            logging.critical(f"Task <{self.name}> is NOT ready sendready <{sendready}> outputready <{outputready}>.")
            if exception:
                raise RuntimeError

        return ready


if __name__ == "__main__":
    from time import sleep

    #outside Class so that matches taskfunc signature
    def sendfunc(taskdata):
        q = taskdata.get('queue')
        output_func = taskdata.get('output_func')
        data = q.get()
        logging.debug(f"OTask sendfunc q.get data <{data}> output_func <{output_func}>")
        retval = output_func(taskdata, data)
        return retval

    # ************************** OTask test functions **************************
    def Test_SendFunc(taskdata, data):
        logging.debug(f"Test_SendFunc Start <{Test_SendFunc}>.")
        if data is None:
            return True

        print(f"Test_SendFunc...........................................")
        print(f"Test_SendFunc...........................................")
        print(f"Test_SendFunc:  <{data}> sent.")
        print(f"Test_SendFunc...........................................")
        print(f"Test_SendFunc...........................................")
        return True

    def Test_EndFunc(taskdata, data):
        logging.debug(f"Test_EndFunc.")
        return f"Test_EndFunc"

    def Test():
        '''
        Create and control a task that reads user input and then writes from queue.
        '''
        #  Create and control a task with a specified task function.
        print(f"OTest Start OTest.")

        print(f"OTest Create task OTest with Test_SendFunc.")
        test_task = OTask("OTest", Test_SendFunc)

        # use function defined of the OTask class
        print(f"OTest Start test Test_SendFunc.")

        print(f"OTest task start paused.")
        sleep(1)
        test_task.start(paused = True)

        print(f"OTest Resume started test_task.")
        test_task.resume()

        print(f"OTest task running.")
        print(f"OTest waiting for input.  Press q Enter to quit.")
        while True:
            data = input()
            if data == "q":
                break

            test_task.put(data)
            print(f"OTest waiting for input.  Press q Enter to quit.")
            sleep(1)

        print(f"OTest_Task task pause.")
        test_task.pause()
        print(f"OTest_Task change input func to Test_EndFunc.")
        test_task.set_outputfunc(Test_EndFunc)
        print(f"OTest_Task task resume.")
        test_task.resume()

        print(f"OTest end task.")
        while True:
            try:
                test_task.end()
                break

            except RuntimeError:
                print(f"OTest Press Enter to end.")
                sleep(1)

        sleep(1)
        print("End OTest task.")

    Test()
