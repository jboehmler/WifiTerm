import logging

import cmdlib.sslsendrecv as sslsendrecv  # module provides functions to access the send and recv functions based on the cmdobj


def cmd_ping(cmdobj, cmdname, cmdargs):
    """Command that will make wifiterm respond with pong."""
    logging.debug(f"cmd_ping:  cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, "ping")

# insert_name cmdobj.name into front of given cmdargs
def cmd_echo(cmdobj, cmdname, cmdargs):
    """Command that will echo string sent as argument."""
    cmdargs = cmdobj.insert_name(cmdargs)
    logging.debug(f"cmd_echo:  cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, cmdargs)

# insert_name cmdobj.name into front of given cmdargs
def cmd_reboot(cmdobj, cmdname, cmdargs):
    """Command that will reboot the wifiterm."""
    print("Rebooting...\r\n")
    logging.debug(f"cmd_reboot:  cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, "reboot")
