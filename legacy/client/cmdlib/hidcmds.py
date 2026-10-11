import logging

from time import sleep

from cmdlib.decorators import hidden, canquit, canexit
from pylib.tables import maketable

LOGLEVEL = logging.DEBUG
logging.basicConfig(
        #format="%(levelname)s:%(threadName)s:%(filename)s:%(funcName)s:%(message)s",
        #filename="libhidcmds.log",
        #filemode="w",
    level=LOGLEVEL,
)

"""Command prototype
def cmd_cmdname(cmdobj, cmdname, cmdargs):

cmdobj object provides access to the def and cmdset data objects
"""

"""
Done.  Tested.
"""

@hidden
def cmd_showcmdset(cmdobj, cmdname, cmdargs):
    cmdset = cmdobj.cmdset
    cmdlist = cmdset.list_allcmds()

    helpcols = [["Command"], ["Visible"], ["CanQuit"]]
    for cmdname in cmdlist:
        visible = cmdset.cmdname_isvisible(cmdname)
        canquit = cmdset.cmdname_canquit(cmdname)
        logging.debug(
            f"cmdname <{cmdname}>, visible <{visible}>, canquit <{canquit}>"
        )
        helpcols[0].append(cmdname)
        helpcols[1].append(str(visible))
        helpcols[2].append(str(canquit))
    print(maketable(helpcols))

# def cmd_showsslq(cmdobj, cmdname, cmdargs):
# fixed string test send commands
@hidden
def cmd_tsend(cmdobj, cmdname, cmdargs):
    """
    Send a string type message of "john"
    """
    # sendstr = "john"  # "john"
    sendstr = "God is great!"  # "God is great!"
    print(f"{sendstr}")

@hidden
def cmd_tsendt(cmdobj, cmdname, cmdargs):
    """
    Send a T type message of "john"
    """
    # sendstr = "Tx6aTx6fTx68Tx6e"  # "john"
    sendstr = "Tx47Tx6fTx64Tx20Tx69Tx73Tx20Tx67Tx72Tx65Tx61Tx74Tx21"
    print(f"{sendstr}")

@hidden
def cmd_tsendx(cmdobj, cmdname, cmdargs):
    """
    Send an X type message of "john"
    """
    # sendstr = "Xx6aXx6fXx68Xx6e"  # "john"
    sendstr = "Xx47Xx6fXx64Xx20Xx69Xx73Xx20Xx67Xx72Xx65Xx61Xx74Xx21"
    print(f"{sendstr}")

@hidden
def cmd_tsendm(cmdobj, cmdname, cmdargs):
    """
    Send a mixed T and X type message of "john"
    """
    # sendstr = "Tx6aXx6fXx68Tx6e"  # "john"
    print(f"{sendstr}")

@hidden
def cmd_sendstr(cmdobj, cmdname, cmdargs):
    """
    Send an unhexed type message of data in cmdargs.  Note, no hex prefix.
    """
    logging.debug(f"Sending string <{str(cmdargs)}>.")
    sslsendrecv.send_str(cmdobj, cmdargs)
    """
    sleep(1)
    logging.debug("Receiving string recvstr.")
    recvstr = sslsendrecv.recv(cmdobj)
    logging.debug(f"Received response <{recvstr}>.")
    print(f"Response:  <{recvstr}>.")
    """

@hidden
def cmd_recvstr(cmdobj, cmdname, cmdargs):
    logging.debug("Receiving string recvstr.")
    recvstr = sslsendrecv.recv(cmdobj)
    logging.debug(f"Received response <{recvstr}>.")
    print(f"Response:  <{recvstr}>.")

@hidden
def cmd_sendhext(cmdobj, cmdname, cmdargs):
    """
    Send an T type message of data in cmdargs
    """
    sslsendrecv.send_hex(cmdobj, "T", cmdargs)

@hidden
def cmd_sendhexx(cmdobj, cmdname, cmdargs):
    """
    Send an X type message of data in cmdargs
    """
    sslsendrecv.send_hex(cmdobj, "X", cmdargs)

@hidden
def cmd_recvhex(cmdobj, cmdname, cmdargs):
    """
    Send an T type message of data in cmdargs
    """
    logging.debug("Receiving string recvstr.")
    recvdata = sslsendrecv.recv_hex(cmdobj)
    logging.debug(f"Received response <{recvdata}>.")
    print(f"Response:  <{recvdata}>.")

@hidden
def cmd_test(cmdobj, cmdname, cmdargs):
    """Command that will make esp8266 print the string sent as cmdarg."""
    logging.debug(f"cmd_exit:  cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, cmdargs)
