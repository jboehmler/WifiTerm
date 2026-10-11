from pdb import set_trace
#import logging
if not logging:
    logging = lambda *args, **kwargs: None

def is_obj(obj, testtype, strict = True):
    logging.debug(f"obj: {obj}, type:  {type(obj)}, testtype: {type(testtype)}, strict: {strict}")
    set_trace()
    if type(obj) is testtype:
        return True

    if strict:
        logging.debug(f"{obj} is NOT a <{testtype}>, type is <{type(obj)}>.")
        raise TypeError

    return False

def is_dict(obj, strict = True):
    return is_obj(obj, dict, strict)
