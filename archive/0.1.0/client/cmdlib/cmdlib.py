## @package cmdlib
# Basic command processor
# 
# class CmdObj:
# class CmdSet:
# class CmdProc:

import logging

from pprint import pformat

from pylib.datadict import DataDict
import cmdlib.decorators as cmd_decs

def make_cmdsdict(modname):
    # Return an imported commands module as a cmd dict.
    # {<func name>: <func object>, ... }
    cmdsdict = {}
    vars_dict = vars(modname)
    # print(vars_dict)
    logging.debug("Commands:")
    for key, val in vars_dict.items():
        logging.debug("key <{}>, val <{}>.".format(key, val))
        if key[:4] == "cmd_": # If key is cmd_xxxxx
            logging.debug("key <{}>, val <{}>.".format(key, val))
            logging.debug("key[:4] <{}>, val <{}>.".format(key[:4], val))
            newkey = key[4:] # Make newkey the xxxxx part of key
            logging.debug("newkey <{}>, val <{}>.".format(key, val))
            cmdsdict[newkey] = val
    return cmdsdict


class CmdObj:
    # Wraps a command function (see above) with data needed to show help, what happens on return, etc.
    # Used to hold information about how to access a command.
    # CmdObjs are generally stored in a CmdSet.  See CmdSet below.
    # Often used by CmdSet itself to add funcs to CmdSet.
    #
    # funcdict - a dictionary in datadict owned by the command for its func to store data between calls.
    # if cmdset is set, CmdObj is "owned" by CmdSet and will have access to the CmdSet wide datadict.
    # if cmdset is None, CmdObj is not part of a CmdSet and functions using a CmdSet datadict could fail.
    # Normal flow:
    # Create CmdObj( name, func, cmdset=None, funcdict=None)

    # def __init__(self, name, func, cmdset=None, funcdict=None):
    def __init__(self, name, func, cmdset = None):
        logging.debug(f"CmdObj __init__.")
        logging.debug(f"Creating CmdObj name <{name}> func {func} cmdset {cmdset}.")
        self.name = name  # Every CmdObj must have a unique name
        self.func = func # def function to call for this CmdObj

        self.cmdset = cmdset
        assert self.cmdset is None, f"(CmdObj name <{name}> not owned by a CmdSet.)"

        # Command's local persistent data as a dictionary
        # Create DataDict as a CmdObj property datadict for 
        self.datadict = DataDict()
        self.funcdict_datadict = DataDict()  # Create datadict for data to be passed to func
        self.help_datadict = DataDict()  # Create datadict and set an obj reference directly to it

        # Put DataDict for func into DataDict under "funcdict" key and add to datadict in key funcdict
        self.datadict.set("funcdict", self.funcdict_datadict) # Add obj reference to datadict[funcdict] too

        # Put DataDict for func into DataDict under "funcflags" key
        # Create DataDict both as an object property funcflags_datadict and add to datadict in key funcflags
        self.funcflags_datadict = DataDict()  # Create datadict and set an obj reference directly to it
        self.datadict.set("funcflags", self.funcflags_datadict) # Add obj reference to datadict[funcflags] too

        # Put DataDict for func into DataDict under "help" key
        # Create DataDict both as an object property help_datadict and add to datadict in key help
        self.datadict.set("help", self.help_datadict) # Add obj reference to datadict[help] too
        self.help_datadict.add_dict( { "shorthelp": "", "longhelp": "", } ) # Initialize to no help

    # Generally called by cmd_func to put CmdObj name into func's cmdargs.
    # Put actual command name at position in the cmdargs list given by calling function as cmdargs.
    # Doesn't modify CmdObj.
    def insert_name(self, cmdargs, pos=0):
        logging.debug(
            f"insert_name pre-change:  name <{self.name}>, pos <{pos}>, cmdargs <{cmdargs}>"
        )
        cmdargs.insert(pos, self.name)
        logging.debug(
            f"insert_name post-change:  name <{self.name}>, pos <{pos}>, cmdargs <{cmdargs}>"
        )
        return cmdargs

    # Gets function flags if set by cmd_decs.
    def get_funcflags(self):
        # Get funcflags from CmdObj funcflags_datadict.  MAY NOT BE THE SAME AS ON FUNCTION.
        # If visible flag not set, return as invalid None>.
        # If get_funcflags is followed by set_funcflags
        #   visible == None will set CmdObj funcflags to default.
        visible = None
        canquit = None # Set an arbitrary value in case visible flag None or not present
        try:
            visible = self.funcflags_datadict.get("visible")

        except (AttributeError, KeyError):
            # visible flag was NOT present
            # Return visible as invalid None and canquit as arbitrary value None
            return visible, canquit

        # If we got here, visible flag was present
        try:
            canquit = self.funcflags_datadict.get("canquit")

        except (AttributeError, KeyError):
            # Since flag should be set, signify flags likely not initialized even if visible was valid
            visible = None # Return an invalid value

        return visible, canquit

    # Use func definition to set funcflags_datadict, does not modify function attributes
    # Return the current visible, canquit
    def set_funcflags(self, visible=True, canquit=None):
        # Get flags from func and put in self.datadict under key funcflags{"visible": val, "canquit": val}
        func = self.func
        getvisible, getcanquit = cmd_decs.get_funcflags(func)
        # Getvisible is None usually indicates flags have not been set.
        if getvisible is None:
            self.funcflags_datadict.add_dict(cmd_decs.default_funcflags_dict)

        else:
            if getvisible is not None:
                self.funcflags_datadict.set("visible", visible) # Set to arg

            if getcanquit in [ None, True, False ]:
                self.funcflags_datadict.set("canquit", canquit) # Set to arg
        return self.get_funcflags()

#    def get_datadict(self, key):
#        return self.datadict.get(key)

#    def set_cmdset(self, cmdset):
#        self.cmdset = cmdset
#        return cmdset
#
#    def get_cmdsetdata(self, key):
#        # Get data by key from owning cmdset data dict.
#        return self.cmdset.get_data(key)

    # Add help info from func to CmdObj.
    def set_funchelp(self, defaultlong=True, shorthelp="", longhelp=""):
        # The command's docstring with strings separated by at least a carriage return
        # Is used as the function's help.
        # The first string is the short help.
        # The second string is the long help.
        # A string with # as the first non-whitespace character is ignored.
        if shorthelp:
            # Override docstring help by setting shorthelp from arg
            self.help_datadict.set("shorthelp", shorthelp)
        if longhelp:
            # Override docstring help by setting longhelp from arg
            self.help_datadict.set("longhelp", longhelp)

        docstr = self.func.__doc__
        if not docstr:
            return self.help_datadict

        # Create a list of text lines from docstr
        doclines = docstr.split("\n")
        # For each line in docstr, remove starting and trailing spaces
        # Second s.strip looks to strip a line that is only strippable chars to ""
        # Create helpdata list of stripped lines
        helpdata = [docline.strip() for docline in doclines if docline.strip(" ")]
        if shorthelp == "":
            # Load short help
            for docline in helpdata:
                if docline == "" or docline[0] == "#":  # Skip empty or comment line
                    continue

                # If arg shorthelp was empty, put line from helpdata into empty shorthelp
                else: # Use docline
                    self.help_datadict.set("shorthelp", docline)
                    break # shorthelp is only one line

        if longhelp == "":
            # Load short help
            longhelpstr = "" # make new long help string to add doclines
            for docline in helpdata:
                if docline == "" or docline[0] == "#":  # skip empty or comment line
                    continue

                else:
                    # put lines into long help string on separate lines
                    longhelpstr += f"{docline}\n"
            self.help_datadict.set("longhelp", longhelpstr) # save the longhelp string

        if (
            defaultlong # if the longhelp is to be the default for help
            and self.help_datadict.get("shorthelp") # and there is a shorthelp
            and self.help_datadict.get("longhelp") == "" # and the long help is empty
            ):
            # Set longhelp to shorthelp
            self.help_datadict.set("longhelp", self.help_datadict.get("shorthelp"))

        return self.help_datadict


class CmdSet:
    # Used to store commands' CmdObjs by the defined command name.
    #     cmds_datadict - all command objs as a dict of key(name):  val(CmdObj)
    #                     Used by CmdProc to access all commands and functions.
    # 
    # CmdSet - cmdsdatadict:  DataDict { key1: CmdObj1, key2: CmdObj2 ... keyn: CmdObjn }
    #        |
    #        - visible:  list of commands where self.visible is True
    #        |
    #        - canquit
    # 
    # visible:  True if the command is visible in a help listing.
    # canexit:  True if the command returning True should exit command processing.
    # canquit:  True if the command returning True should exit command processing
    # and end program.

    def __init__(self, name):
        logging.debug(f"Start CmdSet name <{name}>.")
        # self.globals = globals_builtin_needs_to_be_called_here
        # print(self.globals)
        self.name = name
        self.cmds_datadict = DataDict()
        self.viscmd_list = []  # List of visible cmd names for fast lookup
        self.canquit_list = []  # List of cmd names that can break loop for fast lookup
        self.altnames_datadict = DataDict()
        self.data_datadict = DataDict() # Data to be used by command set and its child command funcs

        self.func_datadict = DataDict()
        self.data_datadict.set("func", self.func_datadict)

    def cmdname_isvisible(self, cmdname):
        return cmdname in self.viscmd_list

    def cmdname_canquit(self, cmdname):
        return cmdname in self.canquit_list

    def set_cmdname(self, cmdname, cmdobj):
        logging.debug("set_cmdname cmdname <{}> cmdobj <{}>.".format(cmdname, cmdobj))
        if self.get_cmdobj(cmdname):
            raise RuntimeError(
                "set_cmdname:  cmdname <{}> for CmdObj <{}> already exists in CmdSet <{}>.".format(
                    cmdname, cmdobj.name, self.name
                )
            )
            return None

        logging.debug("set_cmdname cmdname <{}> does not already exist.".format(cmdname))
        logging.debug("set_cmdname adding cmdname <{}>.".format(cmdname))
        #cmdobj.name = cmdname
        self.cmds_datadict.set(cmdname, cmdobj)
        logging.debug("set_cmdname added cmdname <{}>.".format(cmdname))
        return True

    # Get list of all commands visible = None - all, True - only visible, False - only hidden.
    # Convenience function for list_cmds(visible = None, sorted).
    def list_allcmds(self, sorted = True):
        self.list_cmds(visible = None)

    # Get list of commands visible = None - all, True - only visible, False - only hidden
    def list_cmds(self, visible = True, sorted=True):
        # List all the commands, even those with visible set to False.
        allcmdlist = list(self.cmds_datadict.keys())
        if visible is None:
            # Return all cmds, visible and hidden
            cmdlist = allcmdlist
        elif visible == False:
            # Return only hidden cmds
            cmdlist = [cmd for cmd in allcmdlist if cmd not in self.viscmd_list]
        else:
            # Return only visible cmds
            cmdlist = [cmd for cmd in allcmdlist if cmd in self.viscmd_list]

        if sorted:
            cmdlist.sort()

        return cmdlist

    def get_cmdobj(self, cmdname):
        logging.debug("cmd:  looking for cmdname <{}>.".format(cmdname))
        cmdobj = self.cmds_datadict.get(cmdname)
        if cmdobj is None:
            logging.debug("cmd:  cmdname <{}> not found.".format(cmdname))
            return None

        logging.debug(
            "cmd:  cmdname resolved to cmdobj <{}>.".format(cmdobj.name)
        )
        return cmdobj

    def add_cmdobj(
        self, cmdobj, cmdname=None, funcdict=None, visible=None, canquit=None
    ):
        # Add a CmdObj to the cmdset as cmdname.
        # By default, it also sets the command as visible and unable to quit the program.
        # The funcdict in cmdobj can be used to provide data external to the function
        # for use.
        logging.debug(f"add_cmdobj args cmdobj <{cmdobj}>, cmdname <{cmdname}>")
        logging.debug(f"  funcdict <{funcdict}>, visible <{visible}>, canquit <{canquit}>")
        # Get list of ALL commands
        logging.debug("add_cmdobj to cmds {}.".format(self.list_allcmds()))

        logging.debug(f"add_cmdobj cmdname is <{cmdname}> cmdobj is <{cmdobj}>.")
        if cmdname is None:
            # Don't override command name, use name in arg cmdobj
            logging.debug("add_cmdobj cmdname not given as arg.")
            cmdname = cmdobj.name
            logging.debug(f"add_cmdobj cmdname not specified, look in given cmdobj.name <{cmdobj.name}>")

        logging.debug(f"add_cmdobj set cmdname = <{cmdname}> cmdobj is <{cmdobj}>.")
        retval = self.set_cmdname(cmdname, cmdobj)
        if retval is None:
            logging.warning(f"add_cmdobj:  setting cmdname <{cmdname} FAILED.")
        logging.debug(f"add_cmdobj:  set cmdname to <{cmdname}.")

        # Take ownership of the cmdobj
        logging.debug(f"Try to get cmdobj.cmdset.")
        cmdset = cmdobj.cmdset
        # If cmdset is not owned.
        if cmdset is None:
            logging.debug(f"cmdobj is not owned, own it.")
            logging.debug(f"Set cmdobj.cmdset to self <{pformat(self)}>.")
            cmdobj.cmdset = self
            logging.debug(f"cmdobj.cmdset set to self <{pformat(self)}>.")

        else:
            logging.debug(f"Try else cmdobj.cmdset is <{cmdset}>.")
            if cmdset != self:
                logging.debug(f"CmdObj <{cmdname}> is already owned by CmdSet <{cmdset.name}>.")
                raise AttributeError(f"CmdObj <{cmdname}> is already owned by CmdSet <{cmdset.name}>.")

        logging.debug(f"Ownership of cmdobj.cmdset is <{cmdobj.cmdset}>.")

        logging.debug(f"Get func flags from func <{cmdobj.func.__name__}>.")
        visible, canquit = cmd_decs.get_funcflags(
            cmdobj.func
        )

        logging.debug(f"Set func flags on CmdObj <{cmdobj.name}>.")
        # Set the flags on the CmdObj
        cmdobj.set_funcflags(
            visible, canquit
        )

        # Update the flags' lists with the cmdname as applicable
        if visible:
            logging.debug("Made cmdname <{}> visible.".format(cmdname))
            self.viscmd_list.append(cmdname)

        if canquit:
            # Works because only canquit == True needs to be in list to AND with cmd return
            # canexit will return a False but not None, so will end cli but not quit
            logging.debug("Made cmdname <{}> canquit.".format(cmdname))
            self.canquit_list.append(cmdname)

        logging.debug(f"add_cmdobj <{cmdname}> done.")
        return cmdobj

    def add_cmdfunc(
        self,
        cmdname,
        func,
        funcdict=None,
        visible=None,
        canquit=None,
    ):
        # Add a command function directly to the command dictionary.
        # 
        # It creates a CmdObj automatically and then adds it to the cmsdict.
        # Note also that externally known data can be added for the function through
        # the funcdict.
        # See also:  add_cmdobj for the function def prototype.
        logging.debug("add_cmdfunc pre-add {}.".format(self.list_allcmds()))
        # Get list of ALL commands
        # def __init__(self, name, func, cmdset=None, funcdict={}):
        cmdobj = CmdObj(
            cmdname, func
        )  # Note missing visible, canquit added below
        cmdobj.set_funchelp()

        # cmd_functions can be defined without flags, set at least the defaults
        # def add_cmdobj(self, cmdobj, cmdname=None, funcdict={}, visible=None, canquit=None):
        self.add_cmdobj(cmdobj, cmdname, funcdict, visible, canquit)
        # Get list of ALL commands
        logging.debug("add_cmdfunc post-add {}.".format(self.list_allcmds()))
        return cmdobj

    def add_cmdsdict(
        self,
        cmdsdict,  # cmdsdict of { "name", func }
        funcdict={},
        visible=None,
        canquit=None,
    ):
        for key, val in cmdsdict.items():
            self.add_cmdfunc(
                key, val, funcdict=funcdict, visible=visible, canquit=canquit
            )

    def add_cmdsmodule(
        self,
        modulename,  # Module containing functions def cmd_*
        funcdict={},
        visible=None,
        canquit=None,
    ):
        cmdsdict = make_cmdsdict(modulename)
        self.add_cmdsdict(cmdsdict, funcdict, visible, canquit)

    # Creates an alternative command name for an existing, defined command name.
    # 
    # Useful for creating a shortcut such as 'h' for cmd_help.
    def add_altname(self, cmdname, altname, visible=None, canquit=None):
        # Get list of ALL commands
        logging.debug("add_altname pre-add list_allcmds {}.".format(self.list_allcmds()))
        namedcmdobj = self.get_cmdobj(cmdname)  # Get CmdObj for existing cmdname
        if namedcmdobj is None:
            logging.critical(f"add_altname namecmdobj <{namedcmdobj}>.")
            raise ValueError(f"add_altname cmdname <{cmdname}> CmdObj not found.")
        if visible is None:
            visible = self.cmdname_isvisible(cmdname)
        if canquit is None:
            canquit = self.cmdname_canquit(cmdname)
        altcmdobj = self.add_cmdobj(
            namedcmdobj, cmdname=altname, visible=visible, canquit=canquit
        )

        logging.debug("add_altname pre-add cmdname <{}> altname_<{}> altnames_datadict <{}>.".format(cmdname, altname, self.altnames_datadict.keys()))
        self.altnames_datadict.set(altname, namedcmdobj.name)
        logging.debug("add_altname post-add cmdname <{}> altname_<{}> altnames_datadict <{}>.".format(cmdname, altname, self.altnames_datadict.keys()))

        logging.debug("add_altname post-add list_allcmds {}.".format(self.list_allcmds()))
        return altcmdobj

    def get_altname(self, cmdname):
        return self.altnames_datadict.get(cmdname)

    def get_cmddict(self, cmdname):
        # Return command information as a dict so that it can be added to another CmdSet
        cmdobj = {
            "cmdname": cmdname,
            "cmdobj": self.get_cmdobj(cmdname),
            "visible": self.cmdname_isvisible(cmdname),
            "canquit": self.cmdname_canquit(cmdname),
        }
        return cmdobj

    def add_cmddict(self, cmdobj):
        # Add a command using the dict returned by get_cmdobj.
        return self.add_cmdobj(
            cmdobj["cmdobj"],
            cmdobj["cmdname"],
            cmdobj["visible"],
            cmdobj["canquit"],
        )

# CONVERT to use self.datadict, self.funcdict_datadict, self.funcflags_datadict, self.help_datadict
class CmdProc:
    # Basic command processor to loop and run functions defined in its CmdDict.

    def __init__(self, name, cmdset=None):
        logging.debug(f"Start CmdProc cmdset <{cmdset}>.")
        self.name = name
        # self.cmdset = cmdset if cmdset else CmdSet('CmdProc')
        if cmdset is None:
            logging.debug(f"CmdProc else cmdset <{cmdset}>.")
            self.cmdset = CmdSet(self.name)
        else:
            logging.debug(f"CmdProc if cmdset <{cmdset}>.")
            self.cmdset = cmdset

        logging.debug(f"CmdProc self.cmdset <{self.cmdset}>.")

        self.cmdhist = []  # Future command history feature
        self.prompt = "[cmd]#> "

    def get_cmdset(self):
        cmdset = self.cmdset
        if cmdset is None:
            logging.critical(f"get_cmdset cmdset <{cmdset}>.")
            raise ValueError(f"CmdSet name cannot be None.")

        return cmdset

    # Basic cli loop to be run by program loop.
    # Returns True if cmd_loop ending is to be an overall program "quit."
    # Returns False if quitting the program is optional or the command was unknown.
    #   and cmdobj "unknown" was not defined.
    def cmd_loop(self):
        cmdret = None
        while cmdret is None:
            cmdret = self.nextcmd() # self.nextcmd returns None, stay in this loop
        # Return self.cmd == True or self.cmd == False
        return cmdret # True/False return from cmd_loop

    # CmdProc command string processor.
    # Return None  # Stay in command processing loop
    # Return False  # Command processing is done but don't end calling loop
    # Return True to signal to end program
    def call_inputlist(self, inputlist):
        # inputlist:  "<cmdname> <cmdarg0> ... <cmdargn>"
        if inputlist:
            cmdname = inputlist[0]  # Extract the command name
            cmdargs = inputlist[1:]  # Extract any command arguments
            if not (cmdargs):
                cmdargs = None
            logging.debug(
                "cmdname <{}>  cmdargs <{}>.".format(cmdname, cmdargs)
            )
            cmdobj = self.cmdset.get_cmdobj(cmdname)
            if not cmdobj: # If no cmdobj matched cmdname, use unknown cmdobj
                cmdobj = self.cmdset.get_cmdobj("unknown")
                if not cmdobj:  # If cmdobj "unknown" is not defined
                    return False  # Command processing is done but don't end program

            # print("cmd:  cmdname <{}>, cmdargs <{}>.".format(cmdname, cmdargs))
            logging.debug(
                "cmdobj.name <{}>  cmdargs <{}>.".format(cmdobj.name, cmdargs)
            )

            cmdret = cmdobj.func(
                cmdobj, cmdname, cmdargs
            )  # cmdargs is a list of arguments to the command, cmdret is the return value from the cmdfunc
            logging.debug("cmdobj.func returned cmdret <{}>.".format(cmdret))
            if cmdret is None:
                return None  # Stay in command processing loop
            # If got here, cmdret should be only True or False
            # Only if canquit is True AND cmdret is also True can return be True
            #   Return True to signal to end program
            #   Return False to exit 
            return cmdret and self.cmdset.cmdname_canquit(cmdname)
        else:
            logging.debug("No command received.")
            print("No command received.")
        return None

    def nextcmd(self, inputstr = None):
        # Return None or no return - stay in inner loop
        # Return False - exit calling loop but continue program loop
        # Return True - exit calling loop and exit program loop running calling loop
        if inputstr is None:
            try:
                logging.debug("Prompting for next command.")
                inputstr = input(self.prompt)
            except KeyboardInterrupt:
                logging.debug("Got inputstr CONTROLC")
                inputstr = "q"
        logging.debug("Got inputstr {}.".format(inputstr))
        if inputstr:
            # Get list of ALL commands
            logging.debug("cmd list > {}.".format(self.cmdset.list_allcmds()))
            logging.debug("Processing inputstr {}.".format(inputstr))
            # print(self.cmdlist)
            inputstr = inputstr.strip()
            inputlist = inputstr.split()
            return self.call_inputlist(inputlist)
        else:
            logging.debug("No input received.")
            print("No input received.")
        return None # Stay in loop calling nextcmd


def Test():
    logging.debug(f"Loading basecmds module...")
    import cmdlib.basecmds as basecmds
    logging.debug(f"Loading hidcmds module...")
    import cmdlib.hidcmds as hidcmds

    cli = CmdProc("CLI")
    cmdset = cli.get_cmdset()
    logging.debug(f"Import basecmds.")
    basecmds.init(cmdset) # import, add basecmds and set up shortcuts
    logging.debug(f"Import hidcmds.")
    cmdset.add_cmdsmodule(hidcmds, visible=False) # add cmds defined in module to CmdSet

    retval = cli.cmd_loop()
    print("test:  cli.cmd_loop ended with <{}>.".format(retval))
    if retval == True:
        print("Call to quit program.")
    elif retval == False:
        print("Call to exit main loop but continue program.")
    else:
        print("Invalid retval <{}>.".format(retval))


if __name__ == "__main__" or __name__ == "cmdproc":
    Test()
