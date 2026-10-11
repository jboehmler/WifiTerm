import logging

import re
import os
from datetime import datetime
from pprint import pformat

from pylib.tables import maketable

HEXCHAR = None
# HEXCHAR = "X"
RECVTIMEOUT = 1

"""
https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv411uart_port_t
enum uart_port_t

    UART peripheral number.

    Values:

    UART_NUM_0 = 0x0

    UART_NUM_1 = 0x1

    UART_NUM_MAX
"""

BAUDRATES = ("9600", "19200", "38400", "74880", "76800", "115200")

"""
https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv418uart_word_length_t
enum uart_word_length_t

    UART word length constants.

    Values:

    UART_DATA_5_BITS = 0x0

        word length: 5bits

    UART_DATA_6_BITS = 0x1

        word length: 6bits

    UART_DATA_7_BITS = 0x2

        word length: 7bits

    UART_DATA_8_BITS = 0x3

        word length: 8bits

    UART_DATA_BITS_MAX = 0x4
"""
DATABITS = ("5", "6", "7", "8")
"""
https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv416uart_stop_bits_t
enum uart_stop_bits_t

    UART stop bits number.

    Values:

    UART_STOP_BITS_1 = 0x1

        stop bit: 1bit

    UART_STOP_BITS_1_5 = 0x2

        stop bit: 1.5bits

    UART_STOP_BITS_2 = 0x3

        stop bit: 2bits

    UART_STOP_BITS_MAX = 0x4
"""
STOPBITS = ("invalid", "1", "1.5", "2")
"""
https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv413uart_parity_t
enum uart_parity_t

    UART parity constants.

    Values:

    UART_PARITY_DISABLE = 0x0

        Disable UART parity

    UART_PARITY_EVEN = 0x2

        Enable UART even parity

    UART_PARITY_ODD = 0x3

        Enable UART odd parity
"""
PARITY = ("none", "invalid", "even", "odd")
FLOWCTRL = ("disable", "RTS", "CTS", "enable")

"""Command prototypes
def cmd_cmdname(cmdobj, cmdname, cmdargs):
    #Normal command

@hidden
def cmd_cmdname(cmdobj, cmdname, cmdargs):
    #Command that will not show in the normal help.

@canexit
def cmd_exit(cmdobj, cmdname, cmdargs):
    #Command that will exit command processing but not the program.
    print("Exiting...")
    return False

@canquit
def cmd_cmdname(cmdobj, cmdname, cmdargs):
    #Command that will quit command processing and the program.
    print("Exiting...")
    return False


        self.set_wifitermconfig()
        self.wifiterm_config = {
            "ssid": None,
            "psk": None,
            "baud": None,
            "databits": None,
            "stopbits": None,
            "parity": None,
        }
    def set_wifitermconfig(self):
        self.add_cmdsetdata(
            {
                "wifiterm_config": self.wifiterm_config,
            }
        )
"""


def is_emptylist(vallist):
    return len(vallist) == 0


def get_errormsgs(errorstrlist):
    print_errs = []
    for errstr in errorstrlist:
        try:
            if errstr[0:5] != "QERR_":
                print_errs.append(errstr)
        except IndexError:
            pass
    return print_errs


def print_errormsgs(errorstrlist):
    errormsgs = []
    if is_emptylist(errorstrlist):
        return errormsgs
    errormsgs = get_errormsgs(errorstrlist)
    for errstr in errormsgs:
        print(errstr)
    return errormsgs


def check_argcnt(cmdname, cmdargs, reqargs, comp="=="):
    """check_argcnt compare count of cmdargs list to reqargs
    Return list of error message strings.  If string begins with 'QERR_', don't print.
    """
    retlist = []
    logging.debug(f"cmdname:  <{cmdname}>")
    logging.debug(f"reqargs:  <{reqargs}>")
    logging.debug(f"comp:  <{comp}>")
    logging.debug(f"pre-check cmdargs:  <{pformat(cmdargs)}>")
    if cmdargs is None:  # this override allows for zero reqargs and comp to be used
        logging.debug(f"cmdargs is None.")
        cmdargs = []

    try:
        numargs = len(cmdargs)
    except TypeError:
        logging.debug(f"Invalid cmdargs type <{type(cmdargs)}>")
        return ["QERR_"]

    logging.debug(
        f"cmdname:  <{cmdname}>, reqargs:  <{reqargs}>, comp:  <{comp}>\r\ncmdargs:\r\n{pformat(cmdargs)}"
    )
    validargcnt = False
    match comp:
        case "==":
            if numargs == reqargs:
                validargcnt = True
                return retlist
        case "<":
            if numargs < reqargs:
                validargcnt = True
                return retlist
        case ">":
            if numargs > reqargs:
                validargcnt = True
                return retlist
        case "<=":
            if numargs <= reqargs:
                validargcnt = True
                return retlist
        case ">=":
            if numargs >= reqargs:
                validargcnt = True
                return retlist
        case "!=":
            if numargs != reqargs:
                validargcnt = True
                return retlist
        case _:  # handle bad comparison operator
            logging.warning(f"Unknown comparison operator <{comp}>")
            retlist.append(f"QERR_Unknown comparison operator <{comp}>")
            return retlist
    logging.debug(f"post-check cmdargs:  <{pformat(cmdargs)}>")
    if validargcnt:
        return retlist

    logging.debug(
        f"Check of number of args <{numargs}>, comp <{comp}>, required args <{reqargs}> FAILED,\r\n  cmdargs <{pformat(cmdargs)}>"
    )
    retlist.append(
        f"QERR_Number of cmdargs <{numargs}> is not {comp} required args <{reqargs}>"
    )
    return retlist


def validarg(arg, validargs):
    """validarg can be used as a validfunc.
    Return list of error message strings.  If string begins with 'QERR_', don't print.
    """
    retlist = []
    logging.debug(f"arg:  <{arg}>, validargs:  {pformat(validargs)}")
    if arg in validargs:
        logging.debug(f"arg:  <{arg}> in validargs:  {pformat(validargs)}")
        return retlist
    errstr = f"Validity check of arg {arg} in options {' '.join(validargs)} failed."
    logging.debug(errstr)
    retlist.append(f"QERR_{errstr}")
    return retlist


def validate_cmds(cmdargs, validfunc, validargs):
    """validate_cmds
    validfunc must return True or False
    validargs is list or tuple of ((cmdarg index, valid data), ...)
    Return list of error message strings.  If string begins with 'QERR_', don't print.
    """
    retlist = []
    logging.debug(
        f"validfunc:  {validfunc}\r\n  validargs:  {pformat(validargs)}\r\n  cmdargs:  {pformat(cmdargs)}"
    )
    if cmdargs is None or validfunc is None or validargs is None:
        logging.debug(f"QERR_Invalid None parm found.")
        return f"QERR_Invalid None parm found."
    logging.debug(f"type validargs[0]:  {type(validargs[0])}")
    # if first element is not a tuple, not nested tuples
    if isinstance(validargs[0], int):
        # make non-nested tuple into nested tuple for standard processing
        validargs = (validargs,)
        logging.debug(f"Nested validargs:  {pformat(validargs)}")
    logging.debug(f"validargs:  {pformat(validargs)}")
    for argdata in validargs:
        argindex, argvalues = argdata
        logging.debug(f"argdata:  {argdata}")
        if validfunc(cmdargs[argindex], argvalues):
            logging.debug(f"Validity check of cmdargs {cmdargs} failed.")
            retlist.append(
                f"Command option {cmdargs[argindex]} failed.  Valid options are:  {', '.join(argvalues)}"
            )
    return retlist


def send_cmd(cmdobj, cmdname, cmdargs, hexchar=HEXCHAR):
    if cmdargs is None:
        cmdargs = []
    cmdargs = cmdobj.insert_name(cmdargs)
    cmdstr = " ".join(cmdargs)
    logging.debug(f"Sending command <{cmdstr}> to wifiterm.")
    if hexchar:
        sslsendrecv.send_hex(cmdobj, hexchar, f"{cmdstr}")
    else:
        sslsendrecv.send_str(cmdobj, cmdstr)
    return cmdargs


def recv_resp(cmdobj, recvtimeout=None, hexchar=HEXCHAR):
    recvstr = None

    logging.debug(f"recv cmdobj starting.")
    if recvtimeout is None:
        recvtimetout = RECVTIMEOUT
    recvstr = sslsendrecv.recv(cmdobj, recvtimeout)
    logging.debug(f"recv cmdobj recvstr <{recvstr}>.")
    return recvstr


def basiccmd(
    cmdobj,
    cmdname,
    cmdargs,
    errmsg,
    comparison="==",
    reqargs=None,
    validfunc=None,
    validargs=None,
    hexchar=HEXCHAR,
):
    """
    Return list of error message strings.  If string begins with 'QERR_', don't print.

    cmdobj,
    cmdname,
    cmdargs,
    errmsg,
    comparison="==",
    reqargs=None,
    validfunc=None,
    validargs=None,
    hexchar = HEXCHAR,
    """
    logging.debug(f"cmdname <{cmdname}>,\r\n{pformat(cmdargs)}")
    errorstrlist = []
    if reqargs:
        errorstrlist = check_argcnt(cmdname, cmdargs, reqargs, comparison)
    if is_emptylist(errorstrlist) and validfunc and cmdargs:
        errorstrlist = validate_cmds(cmdargs, validarg, validargs)
    if errorstrlist:
        logging.debug(f"Validation failed.")
        logging.debug(errmsg)
        print(errmsg)
        print_errormsgs(errorstrlist)
        return False
    send_cmd(cmdobj, cmdname, cmdargs, hexchar)
    logging.debug(f"Validation succeeded.")
    return True


def confirm(prompt=None, confirmstr="YES"):
    if prompt is None:
        prompt = input("CONFIRM BY TYPING YES:  >")
    confirm = input(prompt)
    if confirm == confirmstr:
        return True
    return False


def cmd_setwifi(cmdobj, cmdname, cmdargs):
    """Set the WifiTerm\'s built-in wifi SSID and password.
    Requires at least two strings to send, the wifi SSID and the password.
    Changing the SSID and password will require:
    o sending this command
    o losing connectivity to the WifiTerm
    o quitting out of this terminal
    o connecting to the new SSID using the new password
    o restarting the session.
    """
    errmsgs = check_argcnt(cmdname, cmdargs, 2, "==")
    if errmsgs:
        print("Setting the wifi requires an ssid and password.")
        print_errormsgs(errmsgs)
        return None
    wifi_ssid = cmdargs[0]
    wifi_pass = cmdargs[1]
    with open("setwifi.log", "a") as wlog:
        print(
            f"Setting WifiTerm wifi ssid to <{wifi_ssid}> and wifi password to <{wifi_pass}>"
        )
        print(
            "  Changing this setting may cause you to lose contact with the WifiTerm and need to reconnect."
        )
        print()
        if confirm("  CONFIRM THAT YOU WANT TO COMMIT THIS CHANGE BY TYPING YES:  >"):
            print(
                f"[{datetime.now()}]:  setwifi  ssid <{wifi_ssid}>  password <{wifi_pass}>  confirm response <{confirm}>",
                file=wlog,
            )
            # sslsendrecv.send_hex(cmdobj, "X", f"setwifi {wifi_ssid} {wifi_pass}")
            # sslsendrecv.send_str(cmdobj, f"setwifi {wifi_ssid} {wifi_pass}")
            send_cmd(cmdobj, cmdname, cmdargs)
            print(f"WifiTerm set to ssid <{wifi_ssid}>, password <{wifi_pass}>")
            print(
                f"WifiTerm set to ssid <{wifi_ssid}>, password <{wifi_pass}>",
                file=wlog,
            )
        else:
            print("No changes made to WifiTerm.", file=wlog)
            print("No changes made to WifiTerm.")
    return None


def cmd_getwifihist(cmdobj, cmdname, cmdargs):
    """Read the wifi configuration from the change history and display.
    No parameter required.
    """
    # [2024-03-26 12:46:00.182109]:  setwifi  ssid <God>  password <Great!>  confirm response <YES>
    # rx = "\[([^]]*)[^<]*<([^>]*)>[^<]*<([^>]*)>"
    rxstart = r"\["
    rxdate = "([^]]*)"
    rxsetwifi = "[^<]*<"
    rxssid = "([^>]*)"
    rxpassword = ">[^<]*<"
    rxpass = "([^>]*)"
    rxend = ">"
    rx = rxstart + rxdate + rxsetwifi + rxssid + rxpassword + rxpass + rxend
    hist = []
    try:
        with open("setwifi.log") as log:
            entries = []
            for line in log:
                line = line.rstrip()
                rm = re.match(rx, line)
                if rm:
                    datestr = rm.group(1)
                    ssidstr = rm.group(2)
                    passstr = rm.group(3)
                    histstr = (
                        f"date:  {datestr},  ssid:  {ssidstr},  password:  {passstr}"
                    )
                    hist.append(histstr)
            hist.reverse()
            for histstr in hist:
                print(histstr)
        if confirm("DO YOU WANT TO REMOVE THE HISTORY?  CONFIRM BY TYPING YES:  >"):
            os.remove("setwifi.log")
            print("Wifi history removed.")
    except FileNotFoundError:
        print("No wifi history found.")


def cmd_resetuartdefault(cmdobj, cmdname, cmdargs):
    """Re-initialize the UART.
    No parameter required.
    """
    hexchar = HEXCHAR
    send_cmd(cmdobj, cmdname, cmdargs, hexchar)


def print_uartconfig(uartstr):
    logging.debug(f"uartstr <{uartstr}>")
    if uartstr is None:
        logging.debug(f"No SSL response received.")
        return None
    datalist = uartstr.split(",")
    logging.debug(f"datalist:  <{datalist}>\r\n")
    uartlist = [
        ["UART PARM", "VALUE"],
    ]
    try:
        for data in datalist:
            key, val = data.split(":")
            match key:
                case "baud":
                    uartlist.append(["baud", val])
                case "databits":
                    uartlist.append(["databits", DATABITS[int(val)]])
                case "parity":
                    uartlist.append(["parity", PARITY[int(val)]])
                case "stop_bits":
                    uartlist.append(["stopbits", STOPBITS[int(val)]])
                case "flow_ctrl":
                    uartlist.append(["flowctrl", FLOWCTRL[int(val)]])
                case _:  # handle bad comparison operator
                    logging.warning(
                        f"Unknown UART config data key <{key}>, val <{val}>"
                    )
        logging.debug(f"uartlist\r\n{pformat(uartlist)}")
        print(maketable(uartlist))
    except IndexError:
        print(f"Invalid NVS UART data.  Has data been saved?")


def cmd_getuartinfo(cmdobj, cmdname, cmdargs):
    """Command that will retrieve the UART settings.
    https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv418uart_word_length_t

    <baud:74906,databits:3,parity:0,stop_bits:1,flow_ctrl:0>
    """
    logging.debug(f"cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, "getuartinfo")
    uartstr = recv_resp(cmdobj)
    logging.debug(f"uartstr <{uartstr}>")
    print_uartconfig(uartstr)
    return None


def cmd_readuartconfig(cmdobj, cmdname, cmdargs):
    """Command that will retrieve the UART settings.
    https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv418uart_word_length_t

    <baud:74906,databits:3,parity:0,stop_bits:1,flow_ctrl:0>
    """
    logging.debug(f"cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, "readuartconfig")
    uartstr = recv_resp(cmdobj)
    logging.debug(f"uartstr <{uartstr}>")
    print_uartconfig(uartstr)
    return None


def cmd_saveuartconfig(cmdobj, cmdname, cmdargs):
    """Command that will retrieve the UART settings.
    https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv418uart_word_length_t

    <baud:74906,databits:3,parity:0,stop_bits:1,flow_ctrl:0>
    """
    send_cmd(cmdobj, cmdname, cmdargs, HEXCHAR)
    return None


def cmd_setuartsaved(cmdobj, cmdname, cmdargs):
    """Command that will retrieve the UART settings.
    https://docs.espressif.com/projects/esp8266-rtos-sdk/en/latest/api-reference/peripherals/uart.html#_CPPv418uart_word_length_t

    <baud:74906,databits:3,parity:0,stop_bits:1,flow_ctrl:0>
    """
    logging.debug(f"cmdargs <{cmdargs}>")
    sslsendrecv.send_str(cmdobj, "setuartsaved")
    return None


def cmd_setbaud(cmdobj, cmdname, cmdargs):
    """
    Set the UART baud rate in bits per second (bps).
    Requires one parameter, the baud rate."
    """
    errmsg = "Setting the UART baud rate requires a value in bits per second."
    validargs = (0, BAUDRATES)
    hexchar = HEXCHAR
    """
    cmdobj
    cmdname
    cmdargs
    errmsg
    comp
    reqargs
    validfunc
    validargs
    hexchar
    """
    basiccmd(cmdobj, cmdname, cmdargs, errmsg, "==", 1, validarg, validargs, hexchar)


def cmd_setdatabits(cmdobj, cmdname, cmdargs):
    """Set the databits length from 5 to 8 bits."
    Requires one parameter, the databits length as a digit from 5 - 8."
    """
    errmsg = "Setting the UART databits length requires a value of 5, 6, 7, 8."
    validargs = (0, DATABITS)
    hexchar = HEXCHAR
    basiccmd(cmdobj, cmdname, cmdargs, errmsg, "==", 1, validarg, validargs, hexchar)


def cmd_setstopbits(cmdobj, cmdname, cmdargs):
    """Set the number of stop bits.
    Requires one parameter, a number of stop bits from options:  1, 1.5, 2."
    """
    errmsg = "Setting the baud rate requires a value in bits per second."
    validargs = (0, STOPBITS)
    hexchar = HEXCHAR
    basiccmd(cmdobj, cmdname, cmdargs, errmsg, "==", 1, validarg, validargs, hexchar)


def cmd_setparity(cmdobj, cmdname, cmdargs):
    """Set the parity.
    Requires one parameter, a value from options:  none, odd, even.
    """
    errmsg = "Setting the parity requires a value of none, odd or even."
    validargs = (0, PARITY)
    hexchar = HEXCHAR
    basiccmd(cmdobj, cmdname, cmdargs, errmsg, "==", 1, validarg, validargs, hexchar)
