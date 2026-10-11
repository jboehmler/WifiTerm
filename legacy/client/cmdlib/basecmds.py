import logging

from cmdlib.decorators import hidden, canquit, canexit
from pylib.tables import maketable

@hidden
def cmd_unknown(cmdobj, cmdname, cmdargs):
    """Handles user feedback for a command name not in cmdset."""
    logging.debug("cmdname <{}> not in cmddict".format(cmdname))
    print("Unknown command <{}>".format(cmdname))
    logging.debug("Checking for helpprompt in funcdict.")
    if (
        cmdobj.get_data("helpprompt") is None
    ):  # see if a help message is should be shown if an unknown command name is entered
        print("  Type help or h followed by <ENTER> for a list of user commands.")
    else:
        logging.debug("helpprompt not in funcdict.")


@canexit
def cmd_exit(cmdobj, cmdname, cmdargs):
    """Command that will exit command processing but not the program."""
    print("Exiting...\r\n")
    logging.debug(f"cmd_exit:  cmdargs <{cmdargs}>")
    return False


@canquit
def cmd_quit(cmdobj, cmdname, cmdargs):
    """Command that will exit command processing and the program."""
    print("Quitting...\r\n")
    logging.debug(f"cmd_quit:  cmdargs <{cmdargs}>")
    return True

def shorthelp(cmdset, visible=True):
    logging.debug("Start printing short help.")
    if visible: # help for visible command
        cmdlist = cmdset.list_cmds(visible = True)  # cmdlist - visible commands
        logging.debug("Getting short help for visible commands:  <{}>".format(cmdlist))
    else: # help for hidden command
        cmdlist = cmdset.list_cmds(visible=False)  # cmdlist - hidden commands.
        logging.debug("Getting short help for hidden commands:  <{}>".format(cmdlist))
    helpcols = [["Command"], ["Alt for"], ["Action"]]
    for cmd in cmdlist:  # cmd - is in chosen commands
        # check if is altname for a command.
        altname = cmdset.get_altname(cmd)
        altfor = ""
        if altname is not None:
            altfor = altname
        logging.debug("Get object for command:  <{}>".format(cmd))
        cmdobj = cmdset.get_cmdobj(cmd)
        cmdhelp = cmdobj.help_datadict.get("shorthelp")
        cmdhelp = cmdhelp if cmdhelp else "<No help found.>"
        logging.debug(
            f"cmdobj.name <{cmdobj.name}>, altfor <{altfor}>, cmdhelp <{cmdhelp}>"
        )
        helpcols[0].append(cmd)
        helpcols[1].append(altfor)
        helpcols[2].append(cmdhelp)
    print(maketable(helpcols))
    logging.debug("End printing short help.")


def longhelp(cmdset, cmdargs):
    logging.debug("Trying to print long help for cmdargs:  <{}>".format(cmdargs))
    try:
        cmdname = cmdargs[0]
    except IndexError:  # error getting data from cmdargs[0]
        logging.debug("IndexError for cmdargs[0].  cmdargs:  <{}>".format(cmdargs))
        return
    cmddata = cmdset.get_cmdobj(cmdname)
    if cmddata is None:
        logging.debug("Command <{}> not found.".format(cmdname))
        print("Command <{}> not found.".format(cmdname))
        return None
    logging.debug("Help for command:  {}".format(cmdname))
    print("Help for command:  {}".format(cmdname))
    print("{}".format(cmddata.help_datadict.get("shorthelp")))
    if cmddata.help_datadict.get("shorthelp") != cmddata.help_datadict.get("longhelp"):
        print("{}".format(cmddata.help_datadict.get("longhelp")))
    if cmddata.name != cmdname:
        logging.debug("Command is alternative for <{}>.".format(cmddata.name))
        print("Command is alternative for <{}>.".format(cmddata.name))


def cmd_help(cmdobj, cmdname, cmdargs):
    """List command names and their short help.

    help <command name> will print more detail on command usage if available.

    #Followed by a command name in cmdargs[0], will print long help for the command.
    """
    logging.debug(
        "help for cmdname:  <{}>  cmdargs:  <{}>".format(cmdname, cmdargs)
    )
    cmdset = cmdobj.cmdset

    if cmdargs is None:  # no help for specific command requested
        shorthelp(cmdset, visible=True)
    elif cmdargs[0] == "hidden":
        shorthelp(cmdset, visible=False)
    else:  # try to provide long help for command
        longhelp(cmdset, cmdargs)
    return None

# Add the basic help, exit and quit commands.
def init(cmdset, unknown=True, help=True, exit=True, quit=True):
    logging.debug(
        f"init:  unknown <{unknown}>  help:  <{help}>  exit:  <{exit}>  quit:  <{quit}>\r\ncmdset:  <{cmdset}>"
    )
    if unknown:
        logging.debug(f"init:  setting <unknown>")
        cmdset.add_cmdfunc(
            "unknown",
            cmd_unknown,
            visible=False,
            funcdict={
                "helpprompt": True
            },  # have unknown command provide prompt to get help
        )
    if help:
        logging.debug(f"init:  setting <help>")
        cmdset.add_cmdfunc(
            "help",
            cmd_help,
        )
        cmdset.add_altname("help", "h")
    if exit:
        logging.debug(f"init:  setting <exit>")
        cmdset.add_cmdfunc("exit", cmd_exit, canquit=False)
        cmdset.add_altname("exit", "e")
        cmdset.add_altname("exit", "x")

    if quit:
        logging.debug(f"init:  setting <quit>")
        cmdset.add_cmdfunc("quit", cmd_quit, canquit=True)
        cmdset.add_altname("quit", "q")
