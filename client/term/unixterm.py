from pylib.logconfig import logging

from pylib import asciiinfo
from term.osterm import OSTerm
from pylib.keys import CONTROLC

# ************************** Class TermIOTask **************************
class UnixTerm(OSTerm):
    import select

    import sys, tty, termios

    # ************************** Defaults **************************
    def __init__(self):
        super().__init__()  # initialize OSTerm but then change below

        self.name = 'UnixTerm'
        self.hasmodes = True  # most OSTerm children don't have modes, only unix
        self.rawmode = False  # initialize as readline mode
        self.keytimeout = self.KEYTIMEOUT
        self.lineend = "\n"
        self.printfunc = self.custom_print

        self.stdin = self.sys.stdin.fileno()
        self.print_termios_flags()
        logging.debug("Saving termios settings.")
        logging.debug("Save tcgetattr")
        self.oldts = self.termios.tcgetattr(self.stdin)  # save current term settings

        # Save a reference to the original built-in print function
        self.built_in_print = print

        self.set_readline()


    # ************************** Configuration **************************

    # ************************** Status methods **************************
    def print_termios_flags(self):
        """Retrieves and decodes termios flags for a file descriptor."""
        try:
            attrs = self.termios.tcgetattr(self.stdin)
        except self.termios.error as e:
            self.print(f"Error getting termios attributes: {e}")
            return

        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs

        flag_types = {
            'c_iflag (Input)': iflag,
            'c_oflag (Output)': oflag,
            'c_cflag (Control)': cflag,
            'c_lflag (Local)': lflag,
        }

        constants = [name for name in dir(self.termios) if name.isupper() and not name.startswith('__')]

        for flag_type, value in flag_types.items():
            logging.debug(f"--- {flag_type}: {value} (raw value) ---")
            found_flags = []
            for const_name in constants:
                try:
                    const_value = getattr(self.termios, const_name)
                    # Check for bitwise match, excluding constants that are masks (like CSIZE)
                    if const_value and (value & const_value) == const_value:
                        # Heuristic check to avoid printing masked values as flags (e.g. CS8 when CSIZE is the mask)
                        is_mask_component = False
                        for mask_name in ['CSIZE', 'CBAUD', 'CIBAUD', 'CRTSCTS', 'CNEW_RTSCTS']:
                            if hasattr(self.termios, mask_name):
                                mask_value = getattr(self.termios, mask_name)
                                if (mask_value & const_value) == const_value and mask_value != const_value:
                                    is_mask_component = True
                                    break
                        if not is_mask_component:
                            found_flags.append(const_name)
                except TypeError:
                    continue # Ignore non-integer constants

            if found_flags:
                flagstr = ""
                for flag in sorted(found_flags):
                    flagstr += ' ' + flag
                logging.debug(f"{flagstr}")
            else:
                logging.debug("* No specific flags set or recognized constants found.")

    # https://python.plainenglish.io/cool-trick-override-the-built-in-print-in-python-3a56f73b4256
    # Custom print function
    def custom_print(self, *args, **kwargs):
        logging.debug(f"custom_print start:")
        logging.debug(f"args:  <{args}>")
        logging.debug(f"kwargs:  <{kwargs}>")

        # see if 'end' was passed in
        logging.debug(f"try kwargs['end']")
        try:
            logging.debug(f"try kwargs['end'] = <{asciiinfo.ascstr(kwargs['end'])}>")

        except KeyError:
            # no end specified (normal), use default for mode
            logging.debug(f"KeyError lineend = <{asciiinfo.ascstr(self.lineend)}>")
            kwargs['end'] = self.lineend
            logging.debug(f"KeyError kwargs['end'] = <{asciiinfo.ascstr(kwargs['end'])}>")

        logging.debug(f"args:  <{args}>")
        logging.debug(f"kwargs:  <{kwargs}>")
        self.built_in_print(*args, **kwargs)
        logging.debug(f"custom_print end")


    # ************************** Control methods **************************
    # return True if in raw mode
    def set_rawmode(self):
        logging.debug("set_rawmode")
        logging.debug("Current termios settings")
        self.print_termios_flags()
        logging.debug("set to raw")
        self.tty.setraw(self.stdin)
        logging.debug("tty.setraw termios settings")
        self.print_termios_flags()
        logging.debug("set self.lineend = <\\r\\n>")
        self.lineend = "\r\n"
        endline = self.lineend
        logging.debug(f"set_rawmode endline = <{asciiinfo.ascstr(endline)}>")
        logging.debug("set to rawmode")
        self.rawmode = True
        logging.debug("Changed to raw mode")
        return True

    # return True if in readline mode
    def set_readline(self):
        logging.debug("set_readline")
        logging.debug("Current termios settings")
        self.print_termios_flags()
        #self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.tcattr)
        self.termios.tcdrain(self.stdin)
        logging.debug("Restore termios settings")
        self.termios.tcsetattr(self.stdin, self.termios.TCSANOW, self.oldts)
        self.print_termios_flags()
        logging.debug("set self.lineend = <\\n>")
        self.lineend = "\n"
        endline = self.lineend
        logging.debug(f"set_readline endline = <{asciiinfo.ascstr(endline)}>")
        logging.debug("set to readline")
        self.rawmode = False
        logging.debug("Changed to readline")
        return True

    # ************************** Interaction methods **************************
    def get_key(self):
        logging.debug("UnixTerm get_key")
        getkeystr = None
        try:
            rlist, wlist, elist = self.select.select( [ self.stdin, ], [], [], self.keytimeout,)
            if rlist:
                try:
                    if self.rawmode:
                        logging.debug(f"UnixTerm get_key rawmode")
                        getkeystr = self.sys.stdin.read(1)
                    else:
                        logging.debug(f"UnixTerm get_key readline")
                        getkeystr = self.sys.stdin.readline()

                    logging.debug(f"UnixTerm getkeystr = <{asciiinfo.ascstr(getkeystr)}>")

                except KeyboardInterrupt:
                    return(CONTROLC)

            else:
                logging.debug(f"UnixTerm NO KEY get_key returned None")
                return None

        except KeyboardInterrupt:
                    return(CONTROLC)

        logging.debug(f"UnixTerm return getkeystr:  <{getkeystr}>")
        asciiinfo.logdebug_ascstr(getkeystr)
        return getkeystr


def Test():
    unixterm = UnixTerm()
    unixterm.check()
    unixterm.Test()


# to test, be in parent directory of term, use python3 -m term.unixterm
if __name__ == "__main__":  # a little test
    from pylib import logconfig

    #logconfig.init('debug', logconfig.FORMAT1)
    logconfig.init('critical', logconfig.FORMAT1)

    Test()
