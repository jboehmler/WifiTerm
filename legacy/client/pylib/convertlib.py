import logging

def is_valid(data):
    """Validate data is a non-None type.
    template for use:
    -----------------
    data = is_valid(zz)
    if data is None:
        return(None)
    zz = data
    """
    logging.debug(f"data type:  <{type(data)}>")
    if data is None or len(data) < 1:
        logging.debug(f"Bad data:  <{data}>")
        logging.debug(f"Returning None.")
        return None
    logging.debug(f"Returning:  <{data}>")
    return data


def datatoascstr(strdata):
    """
    Take a string or list of strings as strdata and create the appropriate string to send to the WifiTerm.
    Return string
    """
    data = is_valid(strdata)
    if data is None:
        return None
    strdata = data
    logging.debug(f"strdata type:  <{type(strdata)}>")
    if len(strdata) < 1:
        print("Send command requires a string to send.")
        return None
    sendstr = " ".join(strdata) if type(strdata) == list else strdata
    logging.debug(f"sendstr:  <{sendstr}>")
    return sendstr


def bytestoascstr(bytedata):
    """Return bytes data as utf-8 (ascii) string."""
    data = is_valid(bytedata)
    if data is None:
        return None
    bytedata = data
    return bytedata.decode("utf-8")


def ascstrtobytes(ascstr):
    """Return a utf-8 (ascii) string as a bytes object."""
    data = is_valid(ascstr)
    if data is None:
        return None
    ascstr = data
    return ascstr.encode("utf-8")


# converts an ascii character to hex string of four chars 0xXX
def ascchartohexchar(ascchar, hexprefix=None):
    data = is_valid(ascchar)
    if data is None:
        return None
    ascchar = data
    sendstr = ""
    hexstr = hex(ord(ascchar))
    logging.debug("Processing ascchar [{}]  <{}>".format(hexstr, str(ascchar)))
    if len(hexstr) < 4:
        logging.debug("Before fix short hexstr:  <{}>".format(hexstr))
        hexstr = "0x0" + hexstr[-1]
        logging.debug("After fix short hexstr:  <{}>".format(hexstr))
    logging.debug("Adjust hexprefix <{}>, hexstr:  <{}>".format(hexprefix, hexstr))
    if hexprefix:  # if hexprefix is None, then 0 before x stays
        logging.debug("Inserting hexprefix <{}>".format(hexprefix))
        hexstr = hexprefix + hexstr[1:]
    logging.debug("hexstr:  <{}>".format(hexstr))
    return hexstr


# converts an ascii character string (such as comes from termread)
#  to hex char per digit, for example 'be\n' returns '0x620x650x0a'
def ascstrtohexstr(ascstr, hexprefix=None):
    data = is_valid(ascstr)
    if data is None:
        return None
    ascstr = data
    hexstr = ""
    logging.debug("Starting ascii string conversion to hex...")
    for ascchar in ascstr:
        logging.debug("ascchar <{}>, hexprefix:  <{}>".format(str(ascchar), hexprefix))
        hexstr += ascchartohexchar(ascchar, hexprefix)
        logging.debug("hexprefix:  <{}>, hexstr:  <{}>".format(hexprefix, hexstr))
    logging.debug("hexprefix:  <{}>, hexstr:  <{}>".format(hexprefix, hexstr))
    logging.debug("Done ascii string conversion to hex.")
    return hexstr


# Note:  a hexchar is XxXX
# return None on conversion failure
#   account for None versus a tuple when using the return value
# prefixes is a list of allowed Px where P is the prefix
#   if prefixes is None, don't do prefix checking
def hexchartoascchar(hexstr, prefixes=None):
    data = is_valid(hexstr)
    if data is None:
        return None
    hexstr = data
    if len(hexstr) != 4:  # a hexstr must be of form XxXX
        logging.debug("hexchartoasc: invalid hexstr len error: {}.".format(len(hexstr)))
        return None

    if hexstr[1] != "x":  # a hexstr's second char must be an 'x'
        logging.debug("hexchartoasc: hex no x error:  {}.".format(hexstr))
        return None

    if prefixes is None or hextype in prefixes:
        logging.debug("hexchartoasc: decode hex:  <{}>".format(hexstr))
        hextype = hexstr[0]
        logging.debug("hexchartoasc: hextype:  <{}>".format(hextype))
        sint = int(
            hexstr[2:4], 16
        )  # note that this line decodes XxXX hex format string
        logging.debug("hexchartoasc: sint:  <{}>".format(sint))
        if not sint:
            logging.debug("hexchartoasc: sint error:  {}.".format(sint))
            return None
        schar = chr(sint)
        logging.debug(
            "hexchartoasc: hexstr:  <{}>, int:  [{}], char:  <{}>".format(
                hexstr[:4], str(sint), schar
            )
        )
        return (schar, hextype)
    return None


# converts a string of hex digits such as comes via ssl connection
#  any remaining chars after a non-hex char are sent as the last tuple of
#  (string, 0)
#  to char per hex digit, for example 'Tx62Tx65Tx0a' returns [("be\n", "T")]
#  'Xx62Tx65Tx0a' returns [("b", "X"), ("e\n", "T")]
#  'Xx62Tx65Tx0aextrachars' returns [("b", "X"), ("e\n", "T"), ("extrachars", "0")]

# return None on hex conversion failure of no hex digits
#   account for None versus a tuple when using the return value


def hexstrtoascdata(convstr, prefixes=None):
    data = is_valid(convstr)
    if data is None:
        return None
    convstr = data
    currtype = None
    lconvstr = len(convstr)
    logging.debug("Initial convstr:  len <{}>, convstr <{}>.".format(lconvstr, convstr))
    if (
        lconvstr < 4
    ):  # hex string should be at least one hex char of a len of four characters
        logging.debug(
            "String length to convert is too short to be a hex string: len <{}>  convstr <{}>.".format(
                lconvstr, convstr
            )
        )
        return None  # return fail
    retdata = []  # to be list of tuples of (str, typechar)
    typestr = ""  # to store converted chars for current type
    while len(convstr) > 3:  # each hex char string needs to be at least four chars
        strchunk = convstr[:4]  # make a 4 char chunk
        logging.debug(f"Convert strchunk:  <{strchunk}>")
        convdata = hexchartoascchar(
            strchunk, prefixes=prefixes
        )  # try to convert the hex char string
        if convdata is None:  # non-hex chunk string so handle the remaining chars
            logging.debug(
                f"hexstrtoasc returned None:  strchunk <{strchunk}>, <{convstr}>"
            )
            hextype = "0"
            charstr = convstr
            logging.debug(
                f"Chunk non-hex data convstr:  <{convstr}>, hextype:  <{hextype}>"
            )
            logging.debug(
                f"Created remainder hextype <{hextype}>, charstr <{charstr}> and ending hex conversion."
            )
            convstr = "done"  # len(convstr) == 4 chars so will end while loop
        else:  # hex chunk string so handle the hex char
            charstr, hextype = convdata  # get string result
            logging.debug(
                f"Chunk hex data charstr:  <{charstr}>, hextype:  <{hextype}>"
            )
        if hextype == currtype:  # if the same hex type
            typestr += charstr  # append char to in progress string
        else:  # new hextype
            if currtype is None:
                logging.debug("Initial hextype")
            else:
                logging.debug("New hextype")
                logging.debug("current return data:  <{}>".format(retdata))
                retdata.append(
                    (typestr, currtype)
                )  # put current converted string into result
                logging.debug("updated return data:  <{}>".format(retdata))
            typestr = charstr  # start new result string
            currtype = hextype  # start new hex type
            logging.debug(f"new typestr:  <{typestr}>, currtype:  <{currtype}>")
        convstr = convstr[4:]
    if typestr:
        retdata.append((typestr, currtype))
    if len(convstr) > 0:
        logging.debug("SSL hex conversion incomplete:  {}.".format(convstr))
    logging.debug("Returning data:  {}.".format(retdata))
    return retdata


def test(inputlist):
    if not inputlist:
        inputlist = ["test"]
    print("teststr:  ", teststr)
    print()
    print("test:  No hex prefix.")
    hexstr = ascstrtohex(teststr)
    print("ascstrtohex", teststr, ">", hexstr)
    asclist = hexstrtoasc(hexstr)
    print("hexstrtoasc", hexstr, ">", asclist)
    ascchar, hextype = hexchartoasc(hexstr[:4])
    print("hexchartoasc", hexstr[:4], ">", ascchar, hextype)
    hexchar = ascchartohex(ascchar)
    print("ascchartohex", ascchar, ">", hexchar)
    print()
    print("test:  hex prefix == 'T'.")
    teststr = "test"
    print("teststr:  ", teststr)
    hexstr = ascstrtohex(teststr, "T")
    print(teststr, ">", hexstr)
    asclist = hexstrtoasc(hexstr)
    print(hexstr, ">", asclist)
    ascchar, hextype = hexchartoasc(hexstr[:4])
    print(hexstr[:4], hextype, ">", ascchar)
    hexchar = ascchartohex(ascchar, "T")
    print(ascchar, ">", hexchar)
    hexmix = "0x74Tx65Tx730x74"
    print()
    print("test:  hex mixed prefixes", hexmix)
    asclist = hexstrtoasc(hexmix)
    print(hexmix, ">", asclist)


if __name__ == "__main__":
    import sys

    test(sys.argv)
