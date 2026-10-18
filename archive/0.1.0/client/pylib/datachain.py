## @package datalib
#  class DataLib:

import logging

from pprint import pformat

##### Type Functions #####
def is_dict(objname, testobj, strict = True):
    logging.debug(f"objname <{dictstr(testobj)}>")
    log_testobj(objname, testobj)
    if type(testobj) is dict:
        logging.debug(f"{objname} is a dict.")
        return True

    logging.warning(f"{objname} is NOT a dict, type is <{type(testobj)}>.")
    if strict:
        raise TypeError

    return False

def isnot_dict(objname, testobj, strict = True):
    logging.debug(f"objname <{dictstr(testobj)}>")
    log_testobj(objname, testobj)
    if not type(testobj) is dict:
        logging.warning(f"{objname} is NOT a dict, type is <{type(testobj)}>.")
        return True

    logging.debug(f"{objname} is a dict.")
    if strict:
        raise TypeError

    return False

##### Dictionary Functions #####
##### All dictionary functions require dictionary name for logging
def log_dictdata(dictname, dictdata):
    logging.debug(f"dictdata name <{dictname}>:")
    #logging.debug(f"<{dictstr(dictdata)}>")
    datastr = pformat(dictdata, width = 1) # return dictdata as key:val pairs one wide
    datalist = datastr.split('\n')
    for data in datalist:
        logging.debug(f"{data}")

def log_get(dictname, dictdata, key, strict = True):
    logging.debug(f"get value from {dictname} at key <{key}> strict is <{strict}>.")
    logging.debug(f"get key <{key}> in dictdata.")
    log_dictdata(dictname, dictdata)
    try:
        val = dictdata[key]

    except KeyError:
        logging.debug(f"get key <{key}> does not exist.")
        if strict:
            logging.debug(f"get key raised KeyError.")
            raise KeyError

        logging.debug(f"not strict, set val to None.")
        val = None

    logging.debug(f"find_key key <{key}> is value <{dictstr(val)}>.")
    return val

def log_set(dictname, dictdata, key, value):
    logging.debug(f"set key <{key}> in <{dictname}> to value <{value}>.")
    dictdata[key] = value
    val = log_get(dictdata, key)
    return val

def make_keylist(keystr, delim = ':'):
    keylist = keystr.split(delim)
    return keylist

def make_keystr(keylist, delim = ':'):
    keystr = delim.join(keylist)
    return keystr

# find_keylist conditions:
# search dict is invalid
# key list is invalid
# key exists
# key doesn't exist but is the last key
# key doesn't exist but is not the last key
def find_keylist(name, dictname, dictdata, keylist, strict = True):
    # the keylist is a path of keys with values being another dict
    # ex:
    # dict = { 'one': { 'two': { 'three': <val or {}> }}}
    # [ 'one' ] > { 'two': ... }
    # [ 'one', 'two' ] > { 'three' }
    # [ 'one', 'two', 'three' ] > val or dict
    # [ 'one', 'two', 'three', 'four' ] > key doesn't exist but would be a valid new last key
    # [ 'one', 'two', 'three', 'four', 'five' ] > key 'five' doesn't exist but
    #           could not be added as a valid last key because key 'four' doesn't exist either
    # Find the key at end of list
    # Return the key and its value
    logging.debug(f"find keylist <{keylist}> in dictdata.")
    log_dictdata(name, dictdata)

    # initial return dict
    return_dict = {
            'error':  None,
            'parentdict':  None,
            'foundkeys': None,
            'key':  None,
            'val':  None,
            }

    # check if working with valid data
    if keylist == [] or not is_dict('dictdata', dictdata):
        logging.debug(f"empty args keylist <{keylist}> or dictdata.")
        log_dictdata(name, dictdata)
        if strict:
            raise ValueError

        logging.debug(f"set return parentdict dictdata.")
        logging.debug(f"set return key None.")
        logging.debug(f"set return val dictdata.")
        log_dictdata(name, dictdata)
        # either the search dict or the key list is invalid
        return {'error': 'bad data',
                'parentdict': dictdata,
                'foundkeys': None,
                'key': keylist,
                'keyval': None,
                }

    logging.debug(f"keylist keys <{keylist}.")
    keyval = dictdata
    foundkeys = []
    keyerror = False
    lastkey = None
    for key in keylist:
        if keyerror:
            # got a key error but then another key, error not at the last key
            # return not last key
            # return the whole dict because there was an invalid key
            # in the middle of the key list
            logging.critical(f'KeyError key not found and not last.')
            logging.debug(f"KeyError foundkeys <{foundkeys}> last key <{lastkey}> key <{key}> not found.")
            logging.debug(f"keylist <{keylist}> in dictdata.")
            log_dictdata(name, dictdata)
            if strict is True:
                print(f"keylist <{keylist}> in dictdata.")
                print(f"KeyError foundkeys <{foundkeys}> last key <{lastkey}> key <{key}> not found.")
                raise KeyError

            return {'error': 'KeyError key not found and not last',
                    'parentdict': dictdata,
                    'foundkeys': foundkeys,
                    'key': keylist,
                    'keyval': None,
                    }

        lastkey = key
        logging.debug(f"try to get value at <{foundkeys}> <{key}>.")
        logging.debug(f"find keylist <{keylist}> in keyval.")
        log_dictdata('keyval', dictdata)
        # keyval will either be a new dict containing more keys and/or objects or
        # a terminating object
        parentdict = keyval
        try:
            keyval = log_get(parentdict, key, strict = True)

        except KeyError:
            # key didn't exist so can be added
            keyerror = True
            keyval = None
            logging.debug(f"KeyError foundkeys <{foundkeys}> key <{key}> not found.")

        except TypeError:
            # key had value but value was not subscriptable like None so can't
            # go deeper if more keys in list
            logging.warning(f"TypeError for key <{key}> in keylist <{keylist}> in dictdata.")
            log_dictdata(name, dictdata)
            logging.warning(f"TypeError key {foundkeys[-1]} has value <{keyval}> in foundkeys <{foundkeys}>.")
            logging.warning(f"value <{keyval}> is not subscriptable, key <{key}> not found.")
            logging.warning(f"TypeError check key string or list for extra keys or parent key having a value.")
            raise TypeError

        else:
            foundkeys.append(key)
            logging.debug(f"found <{foundkeys}> value <{dictstr(keyval)}>")

    if keyerror:
        logging.debug(f"KeyError key <{key}> not found but is last.")
        # return the parentdict, foundkeys and key so that caller can work
        # handle the key within the current dict
        return {'error': 'KeyError key not found but is last',
                'parentdict': parentdict,
                'foundkeys': foundkeys,
                'key': key,
                'keyval': None,
                }

    logging.debug(f"key is <{foundkeys}> <{key}> keyval is <{dictstr(keyval)}>.")
    # return the parentdict, foundkeys and key so that caller can work
    # handle the key within the current dict
    return {'error': None,
            'parentdict': parentdict,
            'foundkeys': foundkeys,
            'key': key,
            'keyval': keyval,
            }

def find_keystr(name, dictname, dictdata, keystr, strict = True):
    logging.debug(f"find_key:  keystr <{keystr}>.")
    keylist = make_keylist(keystr)
    find_keylist_result = find_keylist(name, dictdata, keylist, strict = strict)
    log_dictdata('find_keylist_result', find_keylist_result)
    return find_keylist_result


class DataLib:
    def __init__(self, name, datadict = {}):
        logging.debug(f"DataLib __init__:  set name <{name}>.")
        if not is_str(name):
            logging.debug(f"DataLib __init__:  name is not a string <{name}>.")
            raise TypeError

        self.name = name
        self.datadict = None
        self.set_datadict(datadict)

    def log_datalib(self):
        log_dictdata(self.name, self.datadict)

    def set_datadict(self, newdict = {}):
        # set the DataLib datadict with a newdict
        logging.debug(f"DataLib set_datadict:  set dict newdict.")
        log_dictdata('newdict', newdict)
        if not is_dict('newdict', newdict):
            logging.debug(f"DataLib set_datadict:  newdict is not a dict.")
            logging.debug(f"DataLib set_datadict:  <{newdict}>.")
            raise TypeError

        if self.datadict is not None:
            logging.warning(f"set_datadict:  Overwriting existing DataLib datadict.")
            log_dictdata('self.datadict', self.datadict)

        self.datadict = newdict
        logging.debug(f"DataLib set_datadict:  new datadict.")
        log_dictdata('self.datadict', self.datadict)
        return self.datadict

    def datadictstr(self):
        logging.debug(f"DataLib datadictstr dict DataLib datadict.")
        log_dictdata('DataLib datadict', self.datadict)
        return self.datadict

    def find_keystr(self, keystr, strict = True):
        logging.debug(f"DataLib find_key.")
        find_keystr_result = find_keystr('self.datadict', self.datadict, keystr, strict = strict)
        return find_keystr_result

    def find_keylist(self, keylist, strict = True):
        logging.debug(f"DataLib find_keylist.")
        find_keylist_result = find_keylist('self.datadict', self.datadict, keystr, strict = strict)
        return find_keylist_result

    def get(self, keystr, strict = True):
        """Get value associated with key keystr.
        keystr can be a colon separated list of keys

        Return value from key keystr or None.
        """
        logging.debug(f"DataLib get:  value of <{keystr}> from DataLib datadict.")
        find_keystr_result = self.find_keystr(keystr, strict = strict)
        error = find_keystr_result['error']
        key = find_keystr_result['key']
        keyval = find_keystr_result['keyval']
        logging.debug(f"DataLib get:  error <{error}> value at <{key}> is <{keyval}")
        return keyval

    def set(self, keystr, value = None, strict = True):
        """Set key keystr to value.

        Return value from key keystr.
        """
        logging.debug(f"DataLib set:  set keystr <{keystr}> to value <{value}> in DataLib datadict.")
        log_dictdata('datadict', self.datadict)

        find_keystr_result = find_keystr('self.datadict', self.datadict, keystr, strict = strict)
        error = find_keystr_result['error']
        parentdict = find_keystr_result['parentdict']
        key = find_keystr_result['key']
        keyval = find_keystr_result['keyval']
        logging.debug(f"DataLib set:  error <{error}> value at <{key}> is <{keyval}")
        logging.debug(f"DataLib set:  parentdict is.")
        log_dictdata('parentdict', parentdict)

        if error is not None and 'KeyError' in error:
            logging.debug(f"DataLib set:  self.find_keystr keystr <{keystr}> got KeyError.")
            logging.debug(f"DataLib set:  key <{keystr}> doesn't exist, create it.")

        if keyval:
            logging.debug(f"DataLib set:  key <{key}> keyval <{keyval}> will be overwritten by <{value}>.")

        logging.debug(f"DataLib set:  set key <{key}> to <{value}> in parentdict.")
        # log_set sets and then gets to make sure value was set and readable,
        # returns as val
        keyval = log_set(parentdict, key, value)
        logging.debug(f"DataLib set:  log_set keystr <{keystr}> to <{keyval}> in DataLib parentdict.")
        log_dictdata('parentdict', parentdict)
        return keyval

    def remove(self, keystr, strict = True):
        """Remove key keystr and value from the DataLib datadict.

        Return value if keystr existed.
        Return None if keystr did not exist.
        """
        logging.debug(f"DataLib remove:  keystr <{keystr}> from DataLib datadict.")
        log_dictdata('datadict', self.datadict)
        find_keystr_result = find_keystr('self.datadict', self.datadict, keystr, strict = strict)
        error = find_keystr_result['error']
        parentdict = find_keystr_result['parentdict']
        foundkeys = find_keystr_result['foundkeys']
        key = find_keystr_result['key']
        keyval = find_keystr_result['keyval']
        logging.debug(f"DataLib remove:  error <{error}> value at <{key}> is <{keyval}>.")
        logging.debug(f"DataLib set:  parentdict is.")
        log_dictdata('parentdict', parentdict)

        logging.debug(f"DataLib remove:  found foundkeys <{foundkeys}> dict <{parentdict}> in DataLib datadict.")
        if error is not None and 'KeyError' in error:
            logging.debug(f"DataLib remove:  get key <{key}> got KeyError.")
            logging.warning(f"DataLib remove:  key <{key}> doesn't exist, can't remove it.")
            raise KeyError

        logging.debug(f"DataLib remove:  get key <{key}> got keyval <{keyval}>.")
        logging.warning(f"DataLib remove:  both key <{key}> and keyval <{keyval}> will be removed.")
        logging.debug(f"DataLib remove:  pop key <{key}>.")
        keyval = parentdict.pop(key)
        logging.debug(f"DataLib remove:  pop key <{key}> keyval <{keyval}>.")
        logging.debug(f"DataLib remove:  After pop <keystr> DataLib datadict.")
        log_dictdata('datadict', self.datadict)
        logging.debug(f"DataLib remove:  return keyval <{keyval}>.")
        return keyval

    def get_datadict(self):
        """Return DataLib datadict as dict or None.
        """
        logging.debug(f"DataLib get_datadict:  return DataLib datadict {self.datadict}.")
        if is_dict('self.datadict', self.datadict):
            logging.debug(f"DataLib get_datadict:  returning: DataLib datadict.")
            log_dictdata('datadict', self.datadict)
            return self.datadict

        raise TypeError(f"datadict not a dict.")

    def add_dict(self, newdict):
        """Add contents of another dict to the DataLib datadict.

        Return updated DataLib datadict.
        Add key-value pairs from another datadict to this one.  Existing ones will be overwritten.
        """
        logging.debug(f"DataLib add_dict:  before add_dict newdict datadict.")
        log_dictdata('datadict', self.datadict)
        logging.debug(f"DataLib add_dict:  Add contents of new dict.")
        log_dictdata('newdict', newdict)
        if is_dict('newdict', newdict):
            self.datadict.update(newdict)
            logging.debug(f"DataLib add_dict:  Updated DataLib datadict.")
            log_dictdata('datadict', self.datadict)
        return self.datadict

    def keys(self):
        logging.debug(f"DataLib keys:  DataLib datadict.")
        log_dictdata('datadict', self.datadict)
        keys = self.datadict.keys()
        logging.debug(f"DataLib keys:  return keys <{keys}>.")
        return keys

    def items(self):
        logging.debug(f"DataLib items:  DataLib datadict.")
        log_dictdata('datadict', self.datadict)
        items = self.datadict.items()
        logging.debug(f"DataLib items:  return items <{items}>.")
        return items
