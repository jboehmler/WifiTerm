import logging
import inspect

logging.critical(f"Start logconfig import...")
LOGGER = logging.getLogger()
logging.critical(f"import set LOGGER to:  {LOGGER}.")

LEVELNO = LOGGER.getEffectiveLevel()
logging.critical(f"import set LEVELNO to:  {LEVELNO}.")

# Logging needs to be configured before local imports to enable logging to file.
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.debug)
# logging.basicConfig(format='%(levelname)s:%(message)s', filename = 'sslclient.log', level=logging.INFO)
# DEFAULT is the format string used by basicConfig with none set
#FORMATS = {
#    "DEFAULT": "%(levelname)s:%(name)s:%(message)s",
#    "FORMAT0": "%(levelname)s:%(filename)s:%(funcName)s:%(lineno)d:\t%(message)s",
#    "FORMAT1": "%(levelname)s:%(threadName)s:%(filename)s:%(funcName)s:%(lineno)d:\t%(message)s",
#    "FORMAT2": "%(levelname)s:%(filename)s:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s",
#    "FORMAT3": "%(asctime)s:%(levelname)s:%(filename)s:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s",
#    "FORMAT4": "%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s",
#}
FORMAT_DEFAULT = "%(levelname)s:%(name)s:%(message)s"
FORMAT0 = "%(levelname)s:%(filename)s:%(funcName)s:%(lineno)d:\t%(message)s"
FORMAT1 = "%(levelname)s:%(threadName)s:%(filename)s:%(funcName)s:%(lineno)d:\t%(message)s"
FORMAT2 = "%(levelname)s:%(filename)s:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s"
FORMAT3 = "%(asctime)s:%(levelname)s:%(filename)s:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s"
FORMAT4 = "%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(threadName)s:%(funcName)s:%(lineno)d:\t%(message)s"

FORMATSTR = logging.BASIC_FORMAT
LOGIT = True
LOGITPRINTER = logging.critical
FORMATMAXLEN = 50

# ---- from Google for "Write a Python debug decorator using functools.wraps that logs a function's name and its arguments upon execution."
# Alt one-line code:  print(f"Calling {inspect.stack()[0].function} with args: {locals()}")

#decorator
def debug_logger(func):
    def wrapper(*args, **kwargs):
        # Format arguments into readable strings
        args_str = ", ".join(repr(a) for a in args)
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
        all_params = ", ".join(filter(None, [args_str, kwargs_str]))

        # Print the function name and arguments
        print(f"[CALLING] {func.__name__}({all_params})")

        return func(*args, **kwargs)

    # Manually preserve the original function name and docstring
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

#decorator
def start_logger(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Format positional arguments
        args_str = ", ".join(repr(a) for a in args)

        # Format keyword arguments
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())

        # Combine both for printing
        #all_params = ", ".join(filter(None, [args_str, kwargs_str]))
        all_params = ", ".join([args_str, kwargs_str])

        print(f"[CALLING] {func.__name__}({all_params})")

        # Execute the actual function
        return func(*args, **kwargs)
    return wrapper

# func_log('test_funclog1', **locals())  #other method
def startlog():
    #signature:  func_log('func_name')
    if not LOGGER.isEnabledFor(logging.INFO):  #save stack work if not needed
        return

    logging.debug(f"func_log  vars:{vars()}")
    frame = inspect.currentframe().f_back
    callerstr = inspect.stack()[1].function
    locvars = frame.f_locals
    logging.info(f"func_log  Caller <{callerstr}> Starting with args:  {locvars}")

def test_funclog(one, two, three, dict1 = 'one', dict2 = 2):
    from pdb import set_trace
    logging.debug(f"test_funclog  local vars:{vars()}")
    logging.debug(f"test_funclog  local locals:{locals()}")
    startlog()
    set_trace()
    newone = 1
    newtwo = '2'
    newdict = { 'one': 1, 'two': 'two' }
    logging.debug(f"test_funclog additions  vars:{vars()}")
    logging.debug(f"test_funclog additions  locals:{locals()}")
    startlog()

def init(loglevel = None, formatstr = None, filename = None):
    logit(f"init Start initialization...")
    # running init with no args runs default logging.basicConfig
    logit(f"init args loglevel <{loglevel}> filename <{filename}>.")
    logitformatstr('formatstr', formatstr, 'init')

    logit(f"init list all initialized loggers.")
    # Get all initialized loggers including their names
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]

    # Optional: Include the root logger itself
    all_loggers = [logging.getLogger()] + loggers
    print(all_loggers)

    logbreak(f"init")
    # removing all handlers makes basicConfig work again
    logit(f"init remove old handlers to enable basicConfig...")
    remove_handlers()
    logit(f"init old handlers removed.")

    logbreak(f"init")
    # set default logging config
    logit(f"init run basicConfig with all defaults...")
    logging.basicConfig()
    logit(f"init basicConfig was run with all defaults.")

    logbreak(f"init")
    logit(f"init set new args loglevel <{loglevel}> filename <{filename}>.")
    logitformatstr('formatstr', formatstr, 'init')

    logbreak(f"init")
    logit(f"init setting new args...")
    argsdone = {}
    if loglevel:
        logit(f"init set log level to:  {loglevel}.")
        set_loglevel(loglevel)
        argsdone['loglevel'] = loglevel
    else:
        logit(f"init loglevel is UNSET.")

    if formatstr:
        logit(f"init setting format to formatstr...")
        logitformatstr('formatstr', formatstr, 'init')
        set_logformat(formatstr)
        argsdone['formatstr'] = formatstr
    else:
        logit(f"init formatstr is UNSET.")

    if filename:
        logit(f"init set file name to:  {filename}.")
        set_logformat(filename)
        argsdone['filename'] = filename
    else:
        filename = "UNSET"
        logit(f"init file name is UNSET.")

    if argsdone:
        logit(f"init new args set:  {argsdone}.")
    else:
        logit(f"init no new args set.")


    logbreak(f"init")
    logit(f"init get final settings...")
    logit(f"init get log levels...")
    set_logitoff()
    loglevel, levelname = get_loglevels()
    set_logiton()
    logit(f"init get format...")
    formatter = logging.root.handlers[0].formatter
    FORMATSTR = formatter._fmt
    logit(f"init final settings loglevel {loglevel} levelname {levelname} filename {filename}.")
    logitformatstr('FORMATSTR', FORMATSTR, 'init')

    logbreak(f"init")
    logit(f"init basicConfig done.")
    logit(f"init args set {argsdone}.")
    logit(f"init log level:  {loglevel}.")
    logit(f"init log level name:  {levelname}.")
    logit(f"init file name:  {filename}.")
    logitformatstr('log format', FORMATSTR, 'init')
    logit(f"init End initialization.")

def logbreak(caller = None):
    if caller is None:
        caller = "UNSET"
    onelogit(f"{caller} ...")

def set_logit(truefalse):
    global LOGIT
    LOGIT = truefalse

def set_logitprinter(logprinter):
    global LOGITPRINTER
    LOGITPRINTER = logprinter

def onelogit(printstr):
    LOGITPRINTER(printstr)

def logit(printstr):
    if LOGIT:
        onelogit(printstr)

def set_logiton():
    logit(f"set_logiton pre LOGIT {LOGIT}.")
    set_logit(True)
    logit(f"set_logiton post LOGIT {LOGIT}.")

def set_logitoff():
    logit(f"set_logitoff pre LOGIT {LOGIT}.")
    set_logit(False)
    logit(f"set_logitoff post LOGIT {LOGIT}.")

def logitformatstr(strname, formatstr, caller = None):
    if caller is None:
        caller = 'UNSET'

    if formatstr is None:
        onelogit(f"{caller} {strname} is UNSET.")
        return formatstr

    if len(formatstr) > FORMATMAXLEN:
        logit(f"{caller} {strname}:")
        logit(f"{caller} {formatstr}.")
    else:
        logit(f"{caller} {strname}:  <{formatstr}>")

    return formatstr

def get_loglevel():
    levelno = LOGGER.getEffectiveLevel()
    logit(f"get_loglevel log level:  {levelno}.")
    return levelno

def get_loglevelname(levelno = None):
    if levelno is None:
        logit(f"get_loglevelname getting current log level.")
        levelno = get_loglevel()

    levelname = logging.getLevelName(levelno)
    logit(f"get_loglevelname log level {levelno} name {levelname}.")
    return levelname

def get_loglevels():
    logit(f"get_loglevels")
    loglevel = get_loglevel()
    levelname = get_loglevelname(loglevel)
    return (loglevel, levelname)

def show_loglevels():
    print("Showing enabled log levels.")
    logging.debug("Debug Messages enabled.")
    logging.info("Info Messages enabled.")
    logging.warning("Warning Messages enabled.")
    logging.error("Error Messages enabled.")
    logging.critical("Critical Messages enabled.")

def set_loglevel(newname):
    # newlevel can be LEVELNO if set
    #   or from logging such logging.LEVEL where LEVEL is WARNING
    # set_loglevel('debug')
    global LEVELNO
    logit(f"set_loglevel setting log level to:  <{newname}>.")

    newname = newname.upper()

    set_logitoff()
    loglevel, levelname = get_loglevels()
    newlevel = get_loglevelname(newname)
    set_logiton()

    logit(f"set_loglevel current log level:  loglevel {loglevel} levelname {levelname}.")
    logit(f"set_loglevel setting target log level:  loglevel {newlevel} levelname {newname}.")
    LOGGER.setLevel(newlevel)
    set_logitoff()
    loglevel, levelname = get_loglevels()
    set_logiton()
    logit(f"set_loglevel current log level loglevel {loglevel} levelname {levelname}.")

    logbreak('set_loglevel')
    logit(f"set_loglevel set LEVELNO to new level {loglevel}.")
    LEVELNO = loglevel
    logit(f"set_loglevel new LEVELNO:  {LEVELNO}.")
    logit(f"set_loglevel new log level loglevel {loglevel} levelname {levelname}.")
    return newlevel

def show_allhandlers():
    print(f"Showing all handlers...")
    # Iterate over all handlers and show them
    print(f"Number of handlers:  {len(LOGGER.handlers)}")
    for handler in LOGGER.handlers:
        print(f"handler:  {handler}")

def set_logformat(formatstr = None):
    global FORMATSTR

    logit(f"set_logformat set log format to:")
    logitformatstr('formatstr', formatstr, 'set_logformat')

    logbreak(f"set_logformat")
    if formatstr is None:
        logit(f"set_logformat using existing format.")
    else:
        logit(f"set_logformat set FORMATSTR to formatstr.")
        FORMATSTR = formatstr
        logitformatstr('FORMATSTR', FORMATSTR, 'set_logformat')

    logbreak(f"set_logformat")
    logit(f"set_logformat setting Formatter to FORMATSTR.")
    formatter = logging.Formatter(FORMATSTR)
    # Iterate over all handlers and set the new formatter
    logit(f"set_logformat set all handlers to FORMATSTR.")
    logit(f"set_logformat number of handlers:  {len(LOGGER.handlers)}")
    for handler in LOGGER.handlers:
        logit(f"set_logformat handler:  {handler}")
        handler.setFormatter(formatter)

    logit(f"set_logformat all handlers set to FORMATSTR.")
    logitformatstr('FORMATSTR', FORMATSTR, 'set_logformat')

    logbreak(f"set_logformat")
    logit(f"set_logformat verify all handler formats...")
    #formatter = logging.root.handlers[0].formatter
    for handler in LOGGER.handlers:
        formatter = handler.formatter
        formatstr = formatter._fmt
        logit(f"set_logformat handler:  {handler}")
        logitformatstr('formatstr', formatstr, 'set_logformat')

def set_logfile(filename, mode = 'w'):
    # Create a new file handler
    # Specify the filename and file mode ('a' for append, 'w' for write/overwrite)
    logit(f"set_logfile:  filename <{filename}> mode <{mode}>.")
    file_handler = logging.FileHandler(filename, mode)

    # Add the new file handler to the LOGGER
    logit(f"set_logfile add handler:  {file_handler}.")
    LOGGER.addHandler(file_handler)

    logit("set_logfile <This message now goes to both the console AND the new log file.>")

# https://docs.python.org/3/library/logging.handlers.html
def set_allhandlers(handler_func, handler_):
    # Iterate over all handlers and set the new formatter
    logit(f"set_allhandlers number of handlers:  {len(LOGGER.handlers)}")
    for handler in LOGGER.handlers:
        logit(f"handler:  {handler}")
        handler.setFormatter(new_formatter)

def remove_handlers():
    """
    Removes all handlers from LOGGER.
    """
    # Iterate over a copy of the handlers list to avoid issues with
    # modifying the list while iterating over it.
    logit(f"remove_handlers number of handlers:  {len(LOGGER.handlers)}")
    for handler in LOGGER.handlers[:]:
        logit(f"remove_handlers close handler:  {handler}")
        handler.close() # It's good practice to close handlers, especially file handlers.
        logit(f"remove_handlers remove handler:  {handler}")
        LOGGER.removeHandler(handler)

#def Test_set_logformat():
#    # Initial basic configuration
#    initial_format='Initial Format: %(message)s'
#    logging.basicConfig(level=logging.INFO, format=initial_format)
#    print(f"Initial format:  <{initial_format}>")
#    logging.debug("This uses the initial format")
#
#    # Change the format afterwards
#    new_format = '[%(asctime)s] %(levelname)s - %(message)s'
#    print(f"New format:  <{new_format}>")
#    new_formatter = logging.Formatter(new_format)
#
#    # Iterate over all handlers and set the new formatter
#    logging.debug(f"Number of handlers:  {len(LOGGER.handlers)}")
#    for handler in LOGGER.handlers:
#        logging.debug(f"handler:  {handler}")
#        handler.setFormatter(new_formatter)
#
#    logging.debug("This uses the new format")
#
#    print()

def Test_logconfig():
    import subprocess

    def pb():
        print(f"\n######################")

    print()  # line break after import
    pb()
    print(f"Starting Test_logconfig...")
    print(f"Test_logconfig Initialize logging...")
    init()
    print(f"Test_logconfig Initialize logging done.")

    pb()
    print(f"Test_logconfig Getting initial log levels...")
    loglevel, levelname = get_loglevels()
    print()
    print(f"Test_logconfig log levels log level {loglevel} level name {levelname}.")
    show_loglevels()

    pb()
    print(f"Test_logconfig set_logformat FORMAT0:  <{FORMAT0}>.")
    set_logformat(FORMAT0)
    print()
    print(f"Test_logconfig show log levels in new format.")
    show_loglevels()

    pb()
    print(f"Test_logconfig set_loglevel debug")
    set_loglevel('debug')
    set_logitoff()
    print(f"Test_logconfig new loglevel {get_loglevel()} levelname {get_loglevelname()}.")
    set_logiton()
    print()
    show_loglevels()

    pb()
    print(f"Test_logconfig set_logfile to debug.log.")
    set_logfile("debug.log")
    print(f"Test_logconfig Set log format for all handlers.")
    set_logformat()  # apply new format to all handlers
    print()

    show_allhandlers()
    print()

    show_loglevels()
    print()

    print(f"Test_logconfig Contents of debug.log.")
    subprocess.run(["cat", "debug.log"])

    pb()
    print(f"Test_logconfig changing logit printer should only affect logit messages.")
    print(f"Test_logconfig change logit printer to logging.info...")
    set_logitprinter(logging.info)
    print(f"Test_logconfig logit messages should now be INFO.")
    print(f"Test_logconfig non-logit messages should not be affected.")
    show_loglevels()
    print(f"Test_logconfig run get_loglevels to make logit messages.")
    loglevel, levelname = get_loglevels()
    logit(f"Test_logconfig current log level loglevel {loglevel} levelname {levelname}.")
    print()

    pb()
    print(f"Test_logconfig logit printer is INFO.")
    print(f"Test_logconfig set_loglevel to warning.")
    print(f"Test_logconfig logit INFO messages should be suppressed.")
    print(f"Test_logconfig non-logit messages should also be affected.")
    print()

    show_loglevels()
    print()

    print(f"Test_logconfig run get_loglevels to make logit messages before setting to warning.")
    loglevel, levelname = get_loglevels()
    print(f"Test_logconfig current log level loglevel {loglevel} levelname {levelname}.")
    print()

    print(f"Test_logconfig set_loglevel to warning.")
    set_loglevel('warn')
    print()

    print(f"Test_logconfig INFO log messages should now be suppressed.")
    print()

    show_loglevels()
    print()

    print(f"Test_logconfig run get_loglevels to make logit messages.")
    loglevel, levelname = get_loglevels()
    print(f"Test_logconfig current log level loglevel {loglevel} levelname {levelname}.")
    print()

    pb()
    print(f"End Test_logconfig.")


logging.critical(f"End logconfig import.")

if __name__ == "__main__":
    Test_logconfig()
