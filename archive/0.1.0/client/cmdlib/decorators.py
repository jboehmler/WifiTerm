## @package decorators
# Defines decorators to modify function properties during function definitions.
#
# CmdProc - A basic command line interface.  Provides a prompt and the user types in commands.
#   Uses commands defined as Python functions, described below, in a Python module file.
#   Basic flow
#   Start
#     |
#  Pre processing
#     |
# Outer Loop<--------------Further processing
#     |                          |
#     +<---------------------    |
#     |                     |    |
#  cmdloop < User command   |    |
#     |                     |    |
#  cmdfunc                  |    |
#     | Return              |    |
#     V                     |    |
#     +----------+-------><None> |
#     V          V               | 
#     |          |               |
#   <True>    <False>------------+
#     |                          |
#     |                          |
#  canquit?-------------------<False>
#     |
#   <True>
#     |
#  Post processing
#     |
#    End
#
#
# Command function prototype
# A command function is defined as cmd_xxxxx where xxxxx is the cmdname such as "test" as in:
#    @decorator (only used if default flags, visible in help and continue getting commands is not desired)
#    def cmd_test(cmdobj, cmdname, cmdargs):
#       <code here>
#       return True/False/None
# 
# As a function is defined, it can have its return behavior modified by the settings of two flags,
#    h visible and canquit.
#    visible:
#      True - command is visible in help.
#      False - command is "hidden".
#    canquit:
#      None - get next command.
#      False - don't quit, exit.
#      True, do quit.
#
#    There are two sets of the flags, attributes on the function itself set by decorators (see below) and
#    those stored in the CmdSet.  These can be considered "hints" for intended operation by the function.
#    When adding the function to a CmdSet as a CmdObj, the CmdSet's functions by default will
#    copy the function flags.  However, if needed, the flags can be overidden when calling the CmdSet
#    function handling adding the function to the CmdSet.
#
#    The effect is that if the CmdSet's canquit is False and the function returns a True, the resultant
#    return will be False and cause an exit rather than a quit.
#
# Help for functions can be defined in the function definition by using the doc string ''' or """.
#    The first line of the doc string is the "short" help.  If the doc string is a single line,
#    the long help will be the same as the short help.
#    If the doc string has multiple lines, then the long help is the short help followed by the
#    following line ended lines.
#    Example short help only doc string:
#    '''Get the square of x and y.'''
#    
#    Example short and long help doc string:
#    '''Get the square of x and y.
#       Get result of (x + y)*(x + y)
#       Command:  square <x> <y>'''

#    Short help:
#    Get the square of x and y.

#    Long help:
#    Get the square of x and y.
#    Get result of (x + y)*(x + y)
#    Command:  square <x> <y>
#    
#
# Use of a decorator allows for the specification of flags while writing the definition.
# The options are:
#   No decorator - after command function runs, loop for next input.
#   @hidden - do not list the command in the help.  Makes command "hidden."
#   @canexit - exit the command input loop for further processing but should keep getting commands.
#     Returns False, don't quit.  Mostly transaction commands?
#   @canquit - exit but also should stop the current command input loop.
#     Returns True, quit.  Finish program or maybe change CmdProcs for a different set of commands.
#
# Decorators can be used (and combined) to set the flags.
# 
# No decorator - no flags set, default flags visible = True, canquit = None will be set and used.
# def cmd_cmdname(cmdobj, cmdname, cmdargs):
#     # Normal command that will show in help and continuing getting commands.
#
#
# hidden decorator - visible flag set to False, canquit not affected (see combining decorators).
# @hidden
# def cmd_hidname(cmdobj, cmdname, cmdargs):
#     # Command that will not show in the normal help.
# 
#
# canexit decorator - canquit set to False, visible flag not affected.
# @canexit
# def cmd_exitname(cmdobj, cmdname, cmdargs):
#     # Command that will exit command processing but not the program.
#     print("Exiting...")
#     return False
# 
# 
# canquit decorator - canquit set to True, visible flag not affected.
# @canquit
# def cmd_quitname(cmdobj, cmdname, cmdargs):
#     #Command that will quit command processing and the program.
#     print("Quitting...")
#     return True
#
# 
# hidden canexit decorator - hidden command can exit but not quit.
# @hidden
# @canexit
# def cmd_cmdname(cmdobj, cmdname, cmdargs):
#     #Normal command - note no return
# 
# 
# 
# Example of basic command line interpreter
# def command_line():
#     import cmdlib.basecmds as basecmds
# 
#     cli = CmdProc("CLI")
#     cmdset = cli.get_cmdset()
#     basecmds.init(cmdset) # supplies basic commands like help
#     # cmdset.add_cmdsmodule(<another commands file>) # add more custom commands
#
#     retval = cli.cmdloop()
#     print("test:  cli.cmdloop ended with <{}>.".format(retval))
#     if retval == True:
#         print("Call to quit program.")
#     elif retval == False:
#         print("Call to exit cmd loop.")
#     else:
#         print("Invalid retval <{}>.".format(retval))
#         raise ValueError(f"Main loop exited with an invalid value <{retval}>.")

import logging

from pprint import pformat

# Decorator to mark a command function as only returning a canexit value
def canexit(func):
    set_funcflags(func, set_canquit=False)
    return func

# Decorator to mark a command function as only returning a canquit value
def canquit(func):
    set_funcflags(func, set_canquit=True)
    return func

# Decorator to make a command function have only the hidden attribute
def hidden(func):
    set_funcflags(func, set_visible=False)
    return func

default_funcflags_dict = {
            "visible": True,
            "canquit": None,
}

# Gets function flags if set by decorators.  If func flags attribute not set, set to defaults.
# Return the flags as set on the function itself.
def get_funcflags(func):
    func_name = func.__name__
    logging.debug(f"get_funcflags func <{func_name}>.")

    try:
        func_flags = func.flags # if flags attribute doesn't exist, exception raised, caught below

    except (AttributeError):
        # flags attribute doesn't exist.  Add flags attribute to func and set to defaults.
        logging.debug(f"flags attribute doesn't exist.")
        logging.debug(f"Add flags attribute to func and set to defaults <{default_funcflags_dict}>.")
        func.flags = default_funcflags_dict.copy()

    logging.debug(f"get_funcflags visible check flags <{pformat(func.flags)}>.")
    try:
        # Get visible flag.
        visible = func.flags["visible"] # if visible doesn't exist, exception raised, caught below

    except (KeyError):
        # visible flag not set, set to default.
        logging.debug(f"get_funcflags visible not set flags <{pformat(func.flags)}>.")
        func.flags["visible"] = default_funcflags_dict["visible"]


    logging.debug(f"get_funcflags canquit check flags <{pformat(func.flags)}>.")
    try:
        # Get canquit flag.
        canquit = func.flags["canquit"] # if canquit doesn't exist, exception raised, caught below

    except (KeyError):
        # canquit flag not set, set to default.
        logging.debug(f"get_funcflags canquit not set flags <{pformat(func.flags)}>.")
        func.flags["visible"] = default_funcflags_dict["visible"]


    logging.debug(f"get_funcflags return visible <{visible}> canquit <{canquit}>.")
    return visible, canquit

# Default flag values make undecorated command visible in help and won't exit or quit
# Return the func checked
def set_funcflags(func, set_visible=True, set_canquit=None):
    func_name = func.__name__
    logging.debug(f"set_funcflags func <{func_name}>.")

    # Note that if the flags func attribute doesn't exist, get_funcflags will set to defaults.
    visible, canquit = get_funcflags(func)
    logging.debug(f"set_funcflags flags set visible <{set_visible}> canquit <{set_canquit}> flags <{pformat(func.flags)}>.")

    logging.debug(f"set_funcflags visible <{visible}> canquit <{canquit}>.")
    # visible is None usually indicates flags present but not properly set. Set to defaults.
    if visible is None:
        logging.debug(f"set_funcflags visible <{visible}> is invalid None.")
        logging.debug(f"set_funcflags set func.flags to default.")
        logging.debug(f"Set to defaults <{default_funcflags_dict}>.")
        func.flags = default_funcflags_dict.copy()

    if set_visible is not None:
        logging.debug(f"set_funcflags set visible to <{set_visible}>.")
        func.flags["visible"] = set_visible # Set to arg

    if set_canquit in [ None, True, False ]:
        logging.debug(f"set_funcflags set canquit to <{set_canquit}>.")
        func.flags["canquit"] = set_canquit # Set to arg

    logging.debug(f"set_funcflags func flags <{pformat(func.flags)}.")
    # Return func flags as potentially created and modified.
    return func
