from pylib.datalib import *

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

def print_method(testname, dataclass):
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


def testset(testsetmsg, dataclass):
    def print_data(startend):
        print_info(f"{startend} testset {testsetmsg} on data.")
        print_info(f"data:")
        print(f"{dictstr(dataclass.get_datadict())}")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Starting test set name <{testsetmsg}>")
    print_debug(f"data is type {type(dataclass)}.")
    keys = dataclass.keys()
    print_debug(f"keys are:")
    print_debug(f"{pformat(keys)}")
    items = dataclass.items()
    print_debug(f"items are:")
    print_debug(f"{pformat(items)}")
    print_data("Start")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing getting missing key <nokey>")
    testname = print_method("get", dataclass)
    print_func(testname, f"nokey should cause exception")
    try:  # expect exception
        retval = dataclass.get("nokey")
    except KeyError:
        print_debug(f"Got expected nokey exception.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing setting missing key <newkey>")
    testname = print_method("set", dataclass)
    print_func(testname, f"should return modified data containing <newkey> and value True.")
    retval = dataclass.set("newkey", True)
    print_assert(testname, retval, "is True", "retval")
    print_func("set", f"newkey returned <{retval}>.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing getting new key <newkey>")
    testname = print_method("get", dataclass)
    print_func(testname, f"should return contents of key <newkey> value True.")
    retval = dataclass.get("newkey")
    print_assert(testname, retval, "is True", "retval")
    print_func(testname, f"newkey returned <{retval}>.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing setting existing key <newkey>")
    testname = print_method("set", dataclass)
    print_func(testname, f"should return modified data containing <newkey> and value False.")
    retval = dataclass.set("newkey", False)
    print_assert(testname, retval, "is False", "retval")
    print_func(testname, f"newkey returned <{retval}>.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing getting changed key")
    testname = print_method("get", dataclass)
    print_func(testname, f"set key newkey should return <False>.")
    retval = dataclass.get("newkey")
    print_assert(testname, retval, "is False", "retval")
    print_func(testname, f"key newkey returned <{retval}>.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing removing existing key")
    testname = print_method("remove", dataclass)
    print_func(testname, f"remove key newkey should return <False>.")
    retval = dataclass.remove("newkey")
    print_assert(testname, retval, "is False", "retval")
    print_func(testname, f"key newkey returned <{retval}>.")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Testing removing missing key")
    testname = print_method("remove", dataclass)
    print_func(testname, f"remove key newkey should cause exception.")
    try:  # expect exception
        retval = dataclass.remove("newkey")
    except KeyError:
        print_debug(f"Got expected newkey exception.")

    print_data("End")
    print_blankline()
    logging.debug(f"...")
    print_blankline()
    logging.debug(f"...")

def Test_Data(DataClass):
    classname = DataClass.__name__

    # Run tests
    print_header(f"Start Test on DataClass {classname}")
    print_info(f'Set up Test data.')
    import pylib.testdata as td

    print_blankline()
    logging.debug(f"...")
    print_debug(f"attributes of DataClass {classname}:")
    print_debug(f"{[f for f in dir(DataClass) if "__" not in f]}")
    print_blankline()
    print_info("Start running test sets...")

    print_blankline()
    logging.debug(f"...")
    print_header(f"Run testset on new {classname}")
    dataclass = DataClass(classname)
    testset(f"{classname}", dataclass)

    print_blankline()
    logging.debug(f"...")
    print_header(f"Run testset on DataClass {classname}  explicitly set to new dictionary nokeydict")
    dataclass = DataClass(classname)
    retval = dataclass.set_datadict(td.nokeydict)
    print_func("set_data", f"nokeydict returned <{retval}>")
    testset(f"{classname} < nokeydict", dataclass)

    print_blankline()
    logging.debug(f"...")
    print_header(f"Run testset on new implicitly initialized DataClass {classname} (nokeydict)")
    dataclass = DataClass(td.nokeydict)
    testset(f"{classname} = nokeydict", dataclass)

    print_blankline()
    logging.debug(f"...")
    print_header(f"Add dict newdict to new DataClass {classname}  and run testset")
    dataclass = DataClass(classname)
    retval = dataclass.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} + newdict", dataclass)

    print_blankline()
    logging.debug(f"...")
    print_header(f"Add dict newdict to new DataClass {classname}  set to nokeydict and run testset")
    dataclass = DataClass(classname)
    retval = dataclass.set_datadict(td.nokeydict)
    retval = dataclass.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} < nokeydict + newdict", dataclass)

    print_blankline()
    logging.debug(f"...")
    print_header(f"Add dict newdict to new DataClass {classname} (nokeydict) and run testset")
    dataclass = DataClass(td.nokeydict)
    retval = dataclass.add_dict(td.newdict)
    print_func("get", f"nokeys returned <{retval}>")
    testset(f"{classname} = nokeydict + newdict", dataclass)

    print_info("End running test sets.")

    print_header(f"End Test on DataClass {classname}")

def Test():
    print(f"***********************")
    print(f"Starting DataLib Test.")
    print(f"***********************")
    Test_Data(DataLib)
    print()
    logging.debug(f"...")


if __name__ == "__main__":
    from pylib import logconfig

    logconfig.init('debug', logconfig.FORMAT0)
    Test()
