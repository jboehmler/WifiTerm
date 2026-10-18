import logging

# loop is Task.Loop object
def task_loop(loop):
    # Start
    logging.debug("task_loop Starting loop {loop.name}.")

    loop.set_status('started', True)
    # Pre-loop pause point
    # Pre-loop func run point
    if loop.get_status('paused'):
        logging.debug(f"task_loop to wait on initial pause.")

    # if paused, wait for resume, otherwise, just continue
    loop.wait_resume()
    loop.set_status('running', True)
    # Pre-loop func run point
    # Start thread.  The thread does not wait but attempts to acquire the lock immediately.
    # If the lock is already held, it returns False;
    # otherwise, it acquires the lock and returns True.
    # Effect is that loop will end if it can acquire the lock
    while not loop.lock():
        logging.debug(f"task_loop Top of loop.")
        if loop.taskfunc(loop.taskdata):  # call this task func with this Task class instance
            logging.debug(f"task_loop func returned True.")
            # maybe eventually make so a defined "True" function can be called
        else:
            logging.debug(f"task_loop func returned False.")
            # maybe eventually make so a defined "False" function can be called
        if loop.get_status('paused'):
            logging.debug(f"task_loop Waiting on pause.")
        loop.wait_resume() # if paused, wait for resume, otherwise, just continue
        logging.debug(f"task_loop Bottom of loop.")
    loop.set_status('running', False)
    logging.debug(f"task_loop Ending loop.")
    loop.set_status('ended', True)
    logging.debug(f"task_loop Task ended.")
