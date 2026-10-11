#!/usr/bin/python3

"""Credit to:
https://www.electricmonk.nl/log/2018/06/02/ssl-tls-client-certificate-verification-with-python-v3-4-sslcontext/
"""
import logging

from time import sleep
from pprint import pformat

import termtask
import ssltasks

from cmdproc import CmdProc

CRLF = "\r\n"
ESCKEY = chr(0x1B)
CONTROLC = chr(0x03)
TASKGETTIMEOUT = 0.01
SSLRECVTIMEOUT = 0.01


def send_cmdmode(cmdmode, sslconn):
    if cmdmode:
        logging.debug(f"send escapes to switch wifiterm to command mode")
        sslconn.sendtask.put(f"<CMD MODE>{CRLF}")
    else:
        logging.debug(f"send escapes to switch wifiterm to command mode")
        sslconn.sendtask.put(f"<RAW MODE>{CRLF}")

# def test(host = "localhost"):
def app_main(host="wifiterm"):
    import cmdlib.sslsendrecv as sslsendrecv
    import cmdlib.basecmds as basecmds
    import cmdlib.hidcmds as hidcmds
    import cmdlib.cfgcmds as cfgcmds
    import cmdlib.usrcmds as usrcmds

    logging.debug("Starting terminal...")
    print("Starting terminal...\r")

    logging.critical(f"Starting test with host <{host}>...")
    print(f"Starting test with host <{host}>...")
    ssl_tasks = ssltasks.init()
    ssl_tasks.is_ready()
    logging.debug("Pause tasks initial start.")
    ssl_tasks.pause()
    logging.debug("Done pause tasks initial start.")
    if host == "wifiterm":
        ssl_tasks.sslconn.init(
            "192.168.4.1",
            443,
            "192.168.4.1",
            "keys/wifiterm/ca.pem",
            "keys/wifiterm/client.pem",
            "keys/wifiterm/client.key",
        )
    else:
        ssl_tasks.sslconn.init(
            "127.0.0.1",
            8443,
            "127.0.0.1",
            "keys/localhost/ca.crt",
            "keys/localhost/client.crt",
            "keys/localhost/client.key",
        )
    ssl_tasks.sslconn.log_hostdata()
    logging.critical(f"Starting SSL connection with <{host}>...")
    print(f"Starting SSL connection with <{host}>...")
    ssl_tasks.sslconn.connect()
    print(f"Server Certificate:\r\n{pformat(ssl_tasks.sslconn.get_peercert())}\r\n")

    logging.debug("Starting SSL tasks...")
    ssl_tasks.start()

    logging.debug("Setting up command processor...")
    cli = CmdProc()
    cmdset = cli.get_CmdSet()
    sslsendrecv.init(cmdset, ssl_tasks)
    basecmds.init(cmdset)

    cmdset.add_cmdsmodule(hidcmds, visible=False)
    cmdset.add_cmdsmodule(cfgcmds, visible=True)
    cmdset.add_cmdsmodule(usrcmds, visible=True)

    logging.debug("Initializing terminal tasks...")
    term = termtask.term_init()

    logging.debug("term tasks initialized.")
    print("Terminal ready.")
    print("Entering initial command mode...")

    logging.debug("Starting terminal tasks...")
    term.start()

    logging.debug("Entering main loop.")
    retstr = ""
    cmdret = None
    cmdmode = True
    prevmode = False  # to force command mode to do mode change stuff
    term.set_readline()
    while True:
        if cmdmode != prevmode:  # stuff to do first time mode changes
            if cmdmode:  # process new command mode
                logging.debug("Changing to command mode.")
                logging.debug("set term readline")
                term.set_readline() # make prints work right
                logging.debug("Pause term tasks.")
                term.pause()
                print("In command mode.")
                logging.debug("Print command help.")
                print("help or (h) for help.")
                print("exit or (e) returns to serial.")
                print("quit or (q) ends the program.")
                # term.sendtask.put(
                #    "Break <ESC> key received\r\nEntering command mode...\r\n"
                # )
                send_cmdmode(cmdmode, sslconn)
                cmdstr = "COMMAND MODE"
            else: # process new raw mode
                # keep readline mode to make prints work right
                logging.debug("Changing to raw mode.")
                logging.debug("set term readline")
                term.set_readline() # make prints work right
                logging.debug("Print serial help.")
                print()
                print("SERIAL MODE:  All keys typed will go directly to device console.")
                print("Press <ESC> key to switch back to command mode.")
                print("Press <ESC> q <ENTER> to exit program.")
                logging.debug("set term rawmode")
                term.set_rawmode() # now switch to raw terminal, prints done
                logging.debug("In raw mode.")
                logging.debug("Start term tasks.")
                term.run()
                send_cmdmode(cmdmode, sslconn)
                cmdstr = "RAW MODE"
            prevmode = cmdmode
            logging.debug(f"{cmdstr}")

        if cmdmode: # command mode
            cmdret = None
            cmdret = cli.nextcmd()
            logging.debug(f"cli.nextcmd ended with <{pformat(cmdret)}>.")
            # logging.debug(f"cli.mainloop ended with <{pformat(cmdret)}>.")
            logging.debug(f"command mode sslconn.recvtask.get({SSLRECVTIMEOUT})")
            retstr = sslconn.recvtask.get(SSLRECVTIMEOUT)
            logging.debug(f"sslconn get retstr:  <{retstr}>\r\n")
            # send response to terminal
            if retstr:
                logging.debug(f"command print retstr:  <{retstr}>\r\n")
                print(f"{retstr}")
            if cmdret is None:
                continue
            elif cmdret == True:
                logging.debug("Call to quit program.")
                logging.debug("Call to exit wifiterm loop.")
                break
            elif cmdret == False:
                # sleep(10)
                logging.debug("Entering raw mode.")
                cmdmode = False
            else:
                print("Invalid cmdret <{}>.".format(cmdret))

        else: # raw mode
            retstr = term.recvtask.get(TASKGETTIMEOUT)
            logging.debug(f"term get retstr:  <{retstr}>\r\n")
            if retstr and retstr[0] == ESCKEY:
                logging.debug("Break <ESC> key received\r\n")
                print("Break <ESC> key received\r\nEntering command mode...\r\n")
                cmdmode = True
                continue
            # retstr is not part of a break sequence, send to wifiterm
            if retstr:
                logging.debug(f"term put retstr:  <{retstr}>\r\n")
                sslconn.sendtask.put(retstr)
            # get response from wifiterm
            logging.debug(f"raw mode sslconn.recvtask.get({SSLRECVTIMEOUT})")
            retstr = sslconn.recvtask.get(SSLRECVTIMEOUT)
            logging.debug(f"sslconn get retstr:  <{retstr}>\r\n")
            # send response to terminal
            if retstr:
                logging.debug(f"term put retstr:  <{retstr}>\r\n")
                term.sendtask.put(retstr)

    logging.debug(f"Stopping tasks.")
    term.stop()
    term.set_readline()
    sslconn.tasksstop()
    logging.debug(f"Closing SSL connection.")
    print(f"Closing SSL connection.")
    sslconn.close()
    logging.debug("End of app_main")
    print(f"Terminal closed.  Press key to return to prompt.")
    # print(f"Terminal closed.")


if __name__ == "__main__":
    # print(f"Running <{__name__}>")
    app_main('localhost')
