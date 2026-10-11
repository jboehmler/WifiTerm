## @package cmdproc
import logging
import pylib.logconfig as logconfig

from cmdlib.cmdlib import CmdProc

def Test():
    ll = logconfig.set_loglevel("INFO")
    logconfig.show_loglevels()
    logging.debug(f"Loading basecmds module...")
    import cmdlib.basecmds as basecmds
    logging.debug(f"Loading hidcmds module...")
    import cmdlib.hidcmds as hidcmds

    cli = CmdProc("CLI")
    cmdset = cli.get_cmdset()
    logging.debug(f"Import basecmds.")
    basecmds.init(cmdset) # import, add basecmds and set up shortcuts
    logging.debug(f"Import hidcmds.")
    cmdset.add_cmdsmodule(hidcmds, visible=False) # add cmds defined in module to CmdSet

    retval = cli.cmd_loop()
    print("test:  cli.cmd_loop ended with <{}>.".format(retval))
    if retval == True:
        print("Call to quit program.")
    elif retval == False:
        print("Call to exit main loop but continue program.")
    else:
        print("Invalid retval <{}>.".format(retval))


if __name__ == "__main__" or __name__ == "cmdproc":
    Test()
