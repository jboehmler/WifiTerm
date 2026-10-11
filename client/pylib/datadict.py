"""@package datadict
class DataDict:
"""

import logging

from pprint import pformat

def dictstr(dictdata):
    # logging.debug(f"type of dictdata is <{type(dictdata)}>.")
    # assert type(dictdata) == dict, f"Type <{type(dictdata)}> is not a dictionary."
    return pformat(dictdata, width = 1) # return dictdata as key:val pairs one wide

def is_dict(testdict):
    logging.debug(f"is_dict testdict <{dictstr(testdict)}>")
    return type(testdict) is dict

class DataDict:
    '''
    def __init__(self, datadict=None):
        """Create a new DataDict or wrap an existing dict with DataDict methods.

        Primary purpose to prevent exceptions on getting keys that don't exist.
        Also allows for logging on dictionary operations when set to logging.debug.
        """
    def get(self, keyname):
        """Get value associated with keyname.

        Note that unlike a normal dictionary,
        using a keyname that doesn't exit simply returns None rather than causing an
        exception.
        """
    def set(self, keyname, value):
    def pop(self, keyname):
        """Remove a keyname and value from the datadict.

        Return True if keyname existed.
        Return False if keyname did not exist.
        """
    def set_datadict(self, newdict):
        """Replace datadict with new datadict."""
    def add_dict(self, newdict):
        """Add contents of another dict to the datadict.

        Add key-value pairs from another datadict to this one.  Existing ones will be overwritten.
        """
    '''
    def datadictstr(self):
        return dictstr(self.datadict)

    def set_datadict(self, newdict):
        """Replace datadict with new datadict.

        Return final datadict.

        If newdict is {newdict}, set_datadict to {newdict}.
        If newdict is None, set_datadict to empty dictionary {}.
        If newdict is not dict but datadict is, leave datadict unchanged.
        Assert if neither newdict nor current self.datadict are dicts.
        """
        try:
            logging.debug(f"Before set_datadict\ndatadict:\n{self.datadictstr()}")

        except AttributeError:
            logging.debug(f"Before set_datadict datadict not initialized.  datadict set to empty.\ndatadict:\n{{}}.")

        logging.debug(f"set_datadict newdict.\nnewdict:\n{dictstr(newdict)}")
        if type(newdict) is dict: # set to {} or {newdict}
            logging.debug(f"set_datadict datadict to newdict.")
            self.datadict = newdict
        elif newdict is None:
            logging.debug(f"set_datadict datadict to empty dict.")
            self.datadict = {}
        elif type(self.datadict) is dict:
            logging.debug(f"set_datadict datadict unchanged.")
        else:
            assert False, f"set_datadict bad vals datadict <{self.datadict}> newdict <{newdict}>."

        logging.debug(f"After set_datadict\ndatadict:\n{self.datadictstr()}")
        return self.datadict

    def __init__(self, initdict = None):
        """Create a new DataDict or wrap an existing dict with DataDict methods.

        Primary purpose to prevent exceptions on getting keys that don't exist.
        Also allows for logging on dictionary operations when set to logging.debug.
        """
        logging.debug(f"DataDict __init__.")
        self.datadict = None # Force newdict in set_datadict(newdict) to be a dict to avoid assert
        logging.debug(f"Initializing DataDict with initdict.\ninitdict:\n{dictstr(initdict)}")
        self.set_datadict(initdict)

    def get(self, keyname):
        """Get value associated with key keyname.

        Return value from key keyname or None.

        Note that unlike a normal dictionary, using a key that doesn't exist simply returns None
        rather than raising an exception.
        """
        logging.debug(f"get value of <{keyname}> from datadict.\ndatadict:\n{self.datadictstr()}")
        try:
            logging.debug(f"get return <{keyname}>:  <{self.datadict[keyname]}>.")
            return self.datadict[keyname]

        except KeyError:
            logging.debug(f"get key <{keyname}> does not exist.")

        logging.debug(f"get key <{keyname}> not successful, returning None.")
        return None

    def set(self, keyname, value):
        """Set key keyname to value.

        Return value from key keyname.
        """
        logging.debug(f"set key <{keyname}> to value <{value}> in datadict.\ndatadict:\n{self.datadictstr()}")
        self.datadict[keyname] = value
        logging.debug(f"get key <{keyname}> value <{self.datadict.get(keyname)}> in datadict.\ndatadict:\n{self.datadictstr()}")
        return self.datadict

    def pop(self, keyname):
        """Remove key keyname and value from the datadict.

        Return value if keyname existed.
        Return None if keyname did not exist.
        """
        logging.debug(f"Before pop datadict.\ndatadict:\n{self.datadictstr()}")
        if self.get(keyname) is None:
            logging.debug(f"pop key <{keyname}> does not exist.")
        else:
            logging.debug(f"pop key <{keyname}> val <{self.datadict.get(keyname)}>.")

        val = self.datadict.pop(keyname, None)
        logging.debug(f"After set datadict.\ndatadict:\n{self.datadictstr()}")
        return val

    def get_datadict(self):
        """Return datadict as dict or None.
        """
        logging.debug(f"get_datadict return datadict {self.datadict} or None.")
        if is_dict(self.datadict):
            logging.debug(f"get_datadict returning: datadict.\ndatadict:\n{self.datadictstr()}")
            return self.datadict
        return None

    def add_dict(self, newdict):
        """Add contents of another dict to the datadict.

        Return updated datadict.
        Add key-value pairs from another datadict to this one.  Existing ones will be overwritten.
        """
        logging.debug(f"Add contents of new dict:\n{pformat(newdict)}\nto existing datadict.\ndatadict:\n{self.datadictstr()}")
        if is_dict(newdict):
            self.datadict.update(newdict)
            logging.debug(f"Updated datadict.\ndatadict:\n{self.datadictstr()}")
        return self.datadict

    def keys(self):
        keydict = self.datadict
        logging.debug(f"keys keydict.\nkeydict:\n{self.datadictstr()}")
        keys = keydict.keys()
        logging.debug(f"keys keys.\n{pformat(keys)}")
        logging.debug(f"keys return keys.\n{pformat(keys)}")
        return keys

    def items(self):
        keydict = self.datadict
        logging.debug(f"keys keydict.\nkeydict:\n{self.datadictstr()}")
        items = keydict.items()
        logging.debug(f"items items.\n{pformat(items)}")
        logging.debug(f"items return items.\n{pformat(items)}")
        return items


class DataObj:
    """Used to build instances or classes that set, store, and get data from an integrated DataDict.

    Difference from inheriting is that DataDict methods such as set or get can be overridden as desired
    in child class.
    """

    def datadictstr(self):
        return dictstr(self.datadict)

    def set_datadict(self, newdict = {}):
        """Replace datadict with new datadict.

        If newdict is {}, set_datadict to empty dictionary {}.
        If newdict is {newdict}, set_datadict to {newdict}.
        Return final datadict.
        Assert if neither newdict nor current self.datadict are dicts.
        """
        return self.datadict.set_datadict(newdict)

    def __init__(self, datadict = None):
        logging.debug(f"DataObj __init__.")
        self.datadict = DataDict(datadict) # objects's local persistent data as a dictionary

    def get(self, keyname):
        """Get value associated with key keyname.

        Return value from key keyname or None.

        Note that unlike a normal dictionary, using a key that doesn't exist simply returns None
        rather than raising an exception.
        """
        return self.datadict.get(keyname)

    def set(self, keyname, value):
        """Set key keyname to value.

        Return value from key keyname.
        """
        return self.datadict.set(keyname, value)

    def pop(self, keyname):
        """Remove key keyname and value from the datadict.

        Return value if keyname existed.
        Return None if keyname did not exist.
        """
        return self.datadict.pop(keyname)

    def get_datadict(self):
        """Return datadict as dict or None.
        """
        return self.datadict.get_datadict()

    def add_dict(self, newdict):
        """Add contents of another dict to the datadict.

        Return updated datadict.
        Add key-value pairs from another datadict to this one.  Existing ones will be overwritten.
        """
        return self.datadict.add_dict(newdict)

    def keys(self):
        return self.datadict.keys()

    def items(self):
        return self.datadict.items()


def Test_Data(dataclass):
    def print_debug(msg):
        print(f"DEBUG:  {msg}")

    def print_info(msg):
        print(f"INFO:  {msg}")

    def print_blankline():
        print(f"")

    def print_header(msg):
        print(f"************* {msg} *************")

    def print_func(func, msg):
        print(f"Testing func <{func}>:  {msg}")

    def print_method(testname):
        if getattr(dataclass, testname):
            print(f"Testing method <{testname}>...")
        return testname

    # maybe add eval_except to do test but raise exception on failed test.
    def print_assert(testname, testval, teststr = "", testvalstr = ""):
        print_debug(f"print_assert args testname <{testname}> testval <{testval}> teststr <{teststr}> testvalstr <{testvalstr}>")
        evalstr = f"{testval} {teststr}"
        print_debug(f"evalstr [{evalstr}].")
        result = eval(f"{evalstr}")
        if testvalstr:
            print_debug(f"Use testvalstr {testvalstr}.")
            evalstr = f"<{testvalstr}> {teststr}"
        # resultstr = f"{testvalstr} <{testvalstr}> {teststr} <{teststr}> result is <{pformat(result)}>"
        assertstr = f"testname <{testname}> [{evalstr}] is <{pformat(result)}>"
        print_debug(f"assert {assertstr}.")
        assert result, f"ASSERT FAIL {assertstr}."
        print_info(f"ASSERT SUCCESS <{assertstr}>.")

    classname = dataclass.__name__
    print_header(f"Start Test on {classname}")

    def testset(testsetmsg, data):
        def print_data(startend, data):
            print_info(f"{startend} testset {testsetmsg} on data.\ndata:\n{dictstr(data.get_datadict())}")

        print_blankline()
        print_header(f"Starting test set name <{testsetmsg}>")
        print_debug(f"data is type {type(data)}.")
        keys = data.keys()
        print_debug(f"keys are:")
        print_debug(f"{pformat(keys)}")
        items = data.items()
        print_debug(f"items are:")
        print_debug(f"{pformat(items)}")
        print_data("Start", data)

        print_blankline()
        print_header(f"Testing getting missing key <nokey>")
        testname = print_method("get")
        print_func(testname, f"nokey should error, no exception, return <None>.")
        retval = data.get("nokey")
        print_assert(testname, retval, "is None", f"retval")
        print_func(testname, f"nokey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing setting missing key <newkey>")
        testname = print_method("set")
        print_func(testname, f"should return modified data containing <newkey> and value True.")
        retval = data.set("newkey", True)
        print_assert(testname, f"type({retval})", "is dict", "retval")
        print_func("set", f"newkey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing getting new key <newkey>")
        testname = print_method("get")
        print_func(testname, f"should return contents of key <newkey> value True.")
        retval = data.get("newkey")
        print_assert(testname, retval, "is True", "retval")
        print_func(testname, f"newkey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing setting existing key <newkey>")
        testname = print_method("set")
        print_func(testname, f"should return modified data containing <newkey> and value False.")
        retval = data.set("newkey", False)
        print_assert(testname, retval["newkey"], "is False", "retval[\"newkey\"]")
        print_func(testname, f"newkey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing getting changed key")
        testname = print_method("get")
        print_func(testname, f"set key newkey should return <False>.")
        retval = data.get("newkey")
        print_assert(testname, retval, "is False", "retval")
        print_func(testname, f"key newkey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing removing existing key")
        testname = print_method("pop")
        print_func(testname, f"pop key newkey should return <False>.")
        retval = data.pop("newkey")
        print_assert(testname, retval, "is False", "retval")
        print_func(testname, f"key newkey returned <{retval}>.")

        print_blankline()
        print_header(f"Testing removing missing key")
        testname = print_method("pop")
        print_func(testname, f"pop key newkey should return <None>.")
        retval = data.pop("newkey")
        print_assert(testname, retval, "is None", "retval")
        print_func(testname, f"key newkey returned <{retval}>.")
        print_data("End", data)
        print_blankline()
        print_blankline()


    # Run tests
    print_info(f'Set up Test data.')
    import pylib.testdata as td

    print_debug(f"attributes of {classname}:")
    print_debug(f"{[f for f in dir(dataclass) if "__" not in f]}")
    print_blankline()
    print_info("Start running test sets...")
    print_blankline()

    print_header(f"Run testset on new {classname}")
    testdata = dataclass()
    testset(f"{classname}", testdata)

    print_header(f"Run testset on new {classname}")
    testdata = dataclass()
    testset(f"{classname}", testdata)

    print_header(f"Run testset on dataclass explicitly set to new dictionary nokeydict")
    testdata = dataclass()
    retval = testdata.set_datadict(td.nokeydict)
    print_func("set_data", f"nokeydict returned <{retval}>")
    testset(f"{classname} < nokeydict", testdata)

    print_header(f"Run testset on new implicitly initialized dataclass(nokeydict)")
    testdata = dataclass(td.nokeydict)
    testset(f"{classname} = nokeydict", testdata)

    print_header(f"Add dict newdict to new dataclass and run testset")
    testdata = dataclass()
    retval = testdata.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} + newdict", testdata)

    print_header(f"Add dict newdict to new dataclass set to nokeydict and run testset")
    testdata = dataclass()
    retval = testdata.set_datadict(td.nokeydict)
    retval = testdata.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} < nokeydict + newdict", testdata)

    print_header(f"Add dict newdict to new dataclass(nokeydict) and run testset")
    testdata = dataclass(td.nokeydict)
    retval = testdata.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} = nokeydict + newdict", testdata)

    print_info("End running test sets.")

    print_header(f"End Test on {classname}")

def Test():
    print(f"***********************")
    print(f"Starting DataDict Test.")
    print(f"***********************")
    Test_Data(DataDict)
    print()
    print(f"***********************")
    print(f"Starting DataObj Test.")
    print(f"***********************")
    Test_Data(DataObj)
    print()

if __name__ == "__main__":
    Test()
