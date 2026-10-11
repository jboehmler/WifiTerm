import logging

from pprint import pformat

from pylib import asciiinfo
from pylib.keys import CONTROLC, ESCKEY

# ************************** Class Term **************************
class OSTerm:
    import sys

    KEYTIMEOUT = 1

    # ************************** Defaults **************************
    def __init__(self):
        self.name = "OSTerm"
        self.hasmodes = False
        self.rawmode = False  # initialize as readline mode
        self.keytimeout = self.KEYTIMEOUT
        self.lineend = "\n"
        self.printfunc = print

    def has_modes(self):
        if self.hasmodes:
            logging.debug("OSTerm hasmodes is True.")
            return True

        logging.debug("OSTerm hasmodes is False.")
        return False

    def set_rawmode(self):
        logging.debug("OSTerm set_rawmode")
        if self.has_modes():
            logging.debug("OSTerm hasmodes is True and set_rawmode has not been overridden.")
            raise RuntimeError

        logging.debug("OSTerm hasmodes is False so raw mode not overridden OKAY.")
        return True

    # return True if in readline mode
    def set_readline(self):
        logging.debug("OSTerm set_readline")
        if self.has_modes():
            logging.debug("OSTerm hasmodes is True and set_readline has not been overridden.")
            raise RuntimeError

        logging.debug("OSTerm hasmodes is False so readline mode not overridden OKAY.")
        return True

    def get_key(self):
        logging.debug("OSTerm get_key has not been overridden.")
        raise RuntimeError

    def print(self, *args, **kwargs):
        self.printfunc(*args, **kwargs)

    def check_child(self):
        # Return True if check_child passes
        logging.debug(f"Starting OSTerm class check_child...")

        if self.printfunc == print:
            self.print("print is not overridden")
            self.print("Test overriding print.")
            self.print(f"test custom print should print <Custom print: testprint>.")

            def testprint(*args, **kwargs):
                print(f'Custom print:', *args, **kwargs)

            oldprint = self.printfunc
            self.printfunc = testprint
            self.print(f"testprint")
            self.printfunc = oldprint

        else:
            self.print(f"test overridden print.")
            self.print(f"testprint")

        self.print()


        self.print(f"test set_rawmode.")
        try:
            self.set_rawmode()

        except RuntimeError:
            logging.debug('test set_rawmode was not overridden.')
            return False

        self.print()

        self.print(f"test set_readline.")
        try:
            self.set_readline()

        except RuntimeError:
            logging.debug('test set_readline was not overridden.')
            return False

        self.print()

        self.print(f"test get_key.")
        try:
            self.get_key()

        except RuntimeError:
            logging.debug('test get_key was not overridden.')
            return False

        self.print()

        logging.debug(f"End OSTerm class check_child.")

        return True

    def loop_getkey(self):
        while True:
            modestr = f'Mode <none>'
            prompt = f'{modestr} press a key.  ESC ends test:  '
            self.print()
            if self.hasmodes:
                if self.rawmode:
                    prompt = f'{modestr} press a key.  ESC ends test:  '
                else:
                    prompt = f'{modestr} press a key.  ESC ENTER ends test:  '

            self.print(f"{prompt}", flush=True, end="")
            keys = self.get_key()
            if keys is None:
                self.print()
                self.print(f"Key press timed out.")
                continue

            keys_list = asciiinfo.ascstr(keys)
            asc_list = self.lineend.join(keys_list)
            self.print()
            if len(keys_list) > 1:
                self.print("You pressed:")
                self.print(f"{asc_list}")
            else:
                self.print(f"You pressed:  {asc_list}.")

            self.print(f"Check for escape key...")
            if keys[0] == ESCKEY:
                self.print()
                self.print(f"Escape received.")
                self.print(f"{modestr} test ended.")
                break

            if keys[0] == CONTROLC:
                from sys import exit
                self.set_readline()  # reset terminal output if needed
                self.print(f"Control C received.")
                self.print(f"{modestr} test ended.")
                self.print(f"Set to readline and quit.")
                exit()

    def Test(self):
        logging.debug("Starting Test...")
        self.key_timeout = 2
        self.print()

        self.print("Test default readline mode.  Press <ESC> <Enter> to end mode test.")
        self.loop_getkey()
        self.print()

        self.print("Test set_rawmode.  Press <ESC> to end mode test.")
        self.set_rawmode()
        self.loop_getkey()
        self.print()

        self.print("Test set_readline.  Press <ESC> <Enter> to end mode test.")
        self.set_readline()
        self.loop_getkey()
        self.print()

        self.print("Ending Test.")


def Term():
    import platform

    # ************************** Defaults **************************
    # import the OS correct RawTerm class as term
    OSType = platform.system().lower()
    match OSType:
        case "windows":
            logging.debug(f"term is for windows using RawTermWindows.")
            from term.winterm import RawTermWindows as term
        case "darwin":
            logging.debug(f"term is for darwin using RawTermMacCarbon.")
            from term.macterm import RawTermMacCarbon as term
        case "linux":
            logging.debug(f"term is for linux using RawTermUnix.")
            from term.unixterm import RawTermUnix as term
        case _:
            logging.warning(f"Unknown operating system <{self.OSType}>.")
            return None  # returning to prevent termclass assignment

    return term()


# to test, be in parent directory of term, use python3 -m term.osterm
if __name__ == "__main__":  # a little test
    from pylib import logconfig

    logconfig.set_loglevel('debug')

    print()
    print(f"Start testing OSTerm object with Test...")

    print(f"Create OSTerm osterm object.")
    osterm = OSTerm()

    print(f"OSTerm child class check.")
    if osterm.check_child():
        print(f"Run Test using class instance.")
        osterm.Test()

    else:
        print(f"OSTerm child class check FAILED.")

    print(f"End testing OSTerm object with Test.")
