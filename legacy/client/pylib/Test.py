# to test, be in parent directory of term, use python3 -m term.unixterm
if __name__ == "__main__":  # a little test
    from pylib import logconfig

    from pylib.datadict import Test as datadict_Test
    from pylib.tasks import Test as tasks_Test
    from pylib.iotask import Test as iotask_Test

    logconfig.set_loglevel('info')
    print(f"***********************")
    print(f"Starting DataDict Test.")
    print(f"***********************")
    datadict_Test()
    print()
    print(f"***********************")
    print(f"Starting Tasks Test.")
    print(f"***********************")
    tasks_Test()
    print()
    print(f"***********************")
    print(f"Starting IOTasks Test.")
    print(f"***********************")
    iotask_Test()
    print()
