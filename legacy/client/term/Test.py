# to test, be in parent directory of term, use python3 -m term.unixterm
def rawterm_Testloop(rawterm, mode):
    logging.debug(f"Starting rawterm_Testloop...")
    rawterm.print(f"Starting rawterm_Testloop...")

    while True:
        logging.debug(f"Waiting for key...{rawterm.lineend}")
        rawterm.print()
        rawterm.print(f"Mode <{mode}> press a key:  ", flush=True, end="")
        keys = rawterm.get_key()
        if keys is None:
            rawterm.print()
            rawterm.print(f"Key press timed out.")
            logging.debug(f"Key timeout.{rawterm.lineend}")
            continue

        asciiinfo.logdebug_ascstr(keys)
        keys_list = asciiinfo.ascstr(keys)
        asc_list = rawterm.lineend.join(keys_list)
        rawterm.print()
        if len(keys_list) > 1:
            rawterm.print("You pressed:")
            rawterm.print(f"{asc_list}")
        else:
            rawterm.print(f"You pressed:  {asc_list}.")
        logging.debug(f"Check for escape key...{rawterm.lineend}")
        if keys[0] == ESCKEY:
            rawterm.print()
            rawterm.print(f"Escape received.")
            rawterm.print()
            break

        if keys[0] == CONTROLC:
            from sys import exit
            rawterm.set_mode('readline')
            exit()

    rawterm.print(f"End rawterm_Testloop.")
    logging.debug(f"End rawterm_Testloop.{rawterm.lineend}")


if __name__ == "__main__":  # a little test
    from pylib import logconfig

    from term.rawterm import Test as rawtermTest
    from term.unixterm import Test as unixtermTest

    logconfig.set_loglevel('info')
    print(f"***********************")
    print(f"Starting unixterm Test.")
    print(f"***********************")
    unixtermTest()
    print()
    print(f"***********************")
    print(f"Starting rawterm Test.")
    print(f"***********************")
    rawtermTest()
    print()
