from json import dumps as ToJSON, loads as FromJSON
from json.decoder import JSONDecodeError

from os import sep, remove, listdir, system, get_terminal_size
from os.path import abspath, exists, isdir, isfile
from shutil import copy
from sys import argv

def cls():
    for command in ["cls", "clear"]:
        ErrorCode = system(command)
        if not ErrorCode:
            break

AIRCRAFTEXTENTSION = "acf"
BACKUPEXTENSION = "bak"
DEFAULTAIRCRAFTNAMES = ["f16", "sr22"]

ENABLECONSTANTUPDATES = True
PRINTAIRCRAFTMAPPING = False

VALIDACFPROPERTIES = [
    'model_name', 'd_e_min', 'v_approach', 'd_f_approach', 'd_p_approach', 'v_cruise', 'd_f_cruise', 'd_p_cruise',
    'spring_e_t', 'damper_e_t', 'spring_vertical', 'damper_vertical', 'spring_horizontal', 'damper_horizontal',
    'p_v', 'first_fixed', 'spring_damper', 'contact_patch', 'p_max', 'f_max', 'p_ratio_reverse', 'p_ratio_alpha',
    'p_t_v', 'd_t_v', 'p_e_v', 'b', 'c_bar', 'd_ref', 'v_ref', 'f_ref', 'm', 'j', 'p_cm_v', 'p_ac_v',
    'alpha_z_0_deg', 'dalpha_z_deg_ddf', 'c_d_0', 'dc_d_ddg', 'dc_d_ddf', 'dc_l_dalpha_deg', 'dc_l_ds',
    'c_l_max_0', 'dc_l_max_ddf', 'd2c_d_dc_l2', 'd2c_d_dc_y2', 'dc_y_ddr', 'dc_y_dbeta_deg', 'dc_y_dp_hat',
    'c_m_0', 'dc_m_dde', 'dc_m_dde_t', 'dc_m_ddf', 'dc_m_ddg', 'dc_m_ds', 'dc_m_dq_hat', 'dc_m_dalpha_deg', 
    'd2c_m_dbeta2', 'dc_l_dda', 'dc_l_ddr', 'dc_l_dbeta_deg', 'dc_l_dp_hat_0', 'dc_l_dr_hat_0',
    'ddc_l_dr_hat_0_ds', 'dc_l_dp_hat_max', 'dc_n_dda', 'dc_n_ddr', 'dc_n_dbeta_deg', 'dc_n_dp_hat', 
    'dc_n_dr_hat', 'd2c_m_dq_hat2', 'd2c_l_dp_hat2', 'd2c_n_dr_hat2', 'dc_y_dr_hat', 'ddc_l_dp_hat_0_ds'
]

BASICACFPROPERTIES = ["v_approach", "v_cruise", "p_max", "f_max", "p_ratio_reverse"]

def ErrorExit(Error: str, ReturnCode: int):
    print(f"ERROR: {Error}")
    exit(ReturnCode)

def AskUser(Prompt: str, ExpectedAnswers: str, DefaultAnswer:str = None):
    ExpectedAnswersList = ExpectedAnswers.replace("", " ").split()
    Answer = ""
    try:
        while Answer not in ExpectedAnswersList:
            Answer = input(f"{Prompt} [{'/'.join(ExpectedAnswersList)}]:>")
            if DefaultAnswer != None:
                Answer = [DefaultAnswer, Answer][Answer in ExpectedAnswersList]
                break
    except KeyboardInterrupt:
        print()
        exit(6)
    except EOFError:
        exit(6)

    return Answer

def UpdateFileList():
    global AircraftFullPaths
    global AircraftNames
    global BackupFullPaths
    global BackupNames
    global AircraftNameToPath

    AircraftFullPaths = []
    AircraftNames = []
    BackupFullPaths = []
    BackupNames = []
    AircraftNameToPath = {}

    for FileName in listdir(AircraftFolder):
        FullFilePath = AircraftFolder + sep + FileName
        if isfile(FullFilePath):
            if FileName.lower().endswith("." + AIRCRAFTEXTENTSION):
                AircraftNames += [FileName[:-len(AIRCRAFTEXTENTSION) - 1]]
                AircraftFullPaths += [FullFilePath]
                AircraftNameToPath[AircraftNames[-1]] = FullFilePath
            if FileName.lower().endswith(BACKUPEXTENSION):
                BackupNames += [FileName[:-len(AIRCRAFTEXTENTSION) - len(BACKUPEXTENSION) - 2]]
                BackupFullPaths += [FullFilePath]

def PrintError(ErrorString:str):
    global NoError
    print("ERROR:", ErrorString)
    NoError = False

def GetTypeName(Value):
    return str(type(Value)).split()[-1][:-1:]

GivenArguments = argv[1::]

if not GivenArguments:
    ErrorExit("Expected to receive directory path to google earth's aircraft", 1)

AircraftFolder = abspath(GivenArguments[0])
if not exists(AircraftFolder):
    ErrorExit("Specified directory doesn't exist", 2)
if not isdir(AircraftFolder):
    ErrorExit("Specified path is not a directory", 3)

CONFIGFILE = AircraftFolder + sep + "aircraft-mappings.json"

UnexpectedError = None
try:
    TestPathFile = f"{AircraftFolder + sep}test.test"
    TestFileExisted = exists(TestPathFile)

    TestFile = open(TestPathFile, "at")
    TestFile.close()
    
    if not TestFileExisted:
        remove(TestPathFile)
except PermissionError:
    ErrorExit("No permission to modify this directory\nUse administrative console or root", 4)
except Exception as Error:
    print(f"Unexpected error during directory check")
    Answer = AskUser("view full information?", "yn")
    UnexpectedError = Error

if UnexpectedError != None:
    if Answer == "y":
        raise UnexpectedError
    else:
        exit(5)

AircraftFullPaths:list[str] = []
AircraftNames:list[str] = []
BackupFullPaths:list[str] = []
BackupNames:list[str] = []
AircraftNameToPath:dict[str,str] = {}
UpdateFileList()

AircraftMapping:dict[str, str] = {"backed up":[]}

def LoadMappingJSON() -> JSONDecodeError | None:
    global AircraftMapping
    
    try:
        file = open(CONFIGFILE, "rt")
        AircraftMapping = FromJSON(file.read())
        file.close()
    except JSONDecodeError as Error:
        return Error

# JSON Structure
# [Default_plane] : [Default_plane | Desired_plane]
# "Backed up" : [...]

def SaveMappingJSON():
    file = open(CONFIGFILE, "wt")
    file.write(ToJSON(AircraftMapping, indent = 4))
    file.close()

def GetAircraftMapping(Question = "all"):
    global ValidDefault
    global DefaultBackedUp
    global AircraftMapping

    DefaultBackedUp = False
    if Question in ["all", "ValidDefault"]:
        DefaultPlanes = f"{', '.join(DEFAULTAIRCRAFTNAMES)}"
        ValidDefault = AskUser(f"Have you changed default aircraft settings ({DefaultPlanes})?", "yn") == "n"

    if not ValidDefault and BackupNames and Question in ["all", "DefaultBackedUp"]:
        Extension = f".{AIRCRAFTEXTENTSION}.{BACKUPEXTENSION} file"
        DefaultBackedUp = AskUser(f"Are backups with {Extension} extension valid?", "yn") == "y"

    AircraftMapping["backed up"] = []
    for name in DEFAULTAIRCRAFTNAMES:
        AircraftMapping[name] = [None, name][ValidDefault]
        if DefaultBackedUp:
            AircraftMapping["backed up"] += [name]

    SaveMappingJSON()

def AttemptMappingRestoration(RestoreTarget: str, FailExitCode: int):
    if AskUser("Attempt to restore setting?", "yn") == "y":
        GetAircraftMapping(RestoreTarget)
    else:
        print("You can edit config file manually or delete it")
        print(f"Config file path: \"{CONFIGFILE}\"")
        exit(FailExitCode)

if not exists(CONFIGFILE):
    GetAircraftMapping("all")
    SaveMappingJSON()
else:
    DecodeError = LoadMappingJSON()

    if DecodeError:
        PrintError("Could not decode mapping file")
        if AskUser("Attempt to restore settings?", "yn") == "y":
            GetAircraftMapping("all")
        else:
            if AskUser("Show JSON error?", "yn") == "y":
                print(f"{DecodeError.msg} (line {DecodeError.lineno},", end = " ")
                print(f"col {DecodeError.colno}, char {DecodeError.pos})")
                print(f"Config file path: \"{CONFIGFILE}\"")
            exit(9)
                
    for name in DEFAULTAIRCRAFTNAMES:
        if name not in AircraftMapping:
            print(f"ERROR: Defaut plane \"{name}\" mapping is not specified")
            AttemptMappingRestoration("ValidDefault", 7)
        
        elif AircraftMapping[name] not in AircraftNames:
            print("ERROR:", end = " ")
            print(f"Default plane \"{name}\" is mapped to non-existent aircraft \"{AircraftMapping[name]}\"")
            AttemptMappingRestoration("ValidDefault", 7)
        
    if "backed up" not in AircraftMapping:
        print(f"ERROR: \"backed up\" field is not specified")
        AttemptMappingRestoration("DefaultBackedip", 8)
    
    elif type(AircraftMapping["backed up"]) != list:
        print(f"expected 'list' for \"backed up\" field, received {GetTypeName(AircraftMapping['backed up'])}")
        AttemptMappingRestoration("DefaultBackedip", 8)

    for backup in AircraftMapping["backed up"]:
        if backup not in DEFAULTAIRCRAFTNAMES:
            print(f"ERROR: Expected default aircraft backup, not \"{backup}\"")
            AttemptMappingRestoration("DefaultBackedip", 8)
            break
        if backup not in BackupNames:
            print(f"ERROR: Backup of \"{backup}\" is not found")
            AttemptMappingRestoration("DefaultBackedip", 8)
            break
    
def ShowPlanes():
    print("Available planes:")
    if not AircraftNames:
        print("    None")
    for aircraft in AircraftNames:
        print(f"   {aircraft.upper()} {'(Default)' * (aircraft in DEFAULTAIRCRAFTNAMES)}")
    print(f"Found backups (.{AIRCRAFTEXTENTSION}.{BACKUPEXTENSION} files):")
    
    if not BackupNames:
        print("    None")
    for aircraft in BackupNames:
        print(f"   {aircraft.upper()} {'(Default)' * (aircraft in DEFAULTAIRCRAFTNAMES) * False}")

def InterpretateAircraftAsACF(AircraftName: str) -> dict[str, str]:
    file = open(AircraftNameToPath[AircraftName], "rt")
    FileLines = file.read().split("\n")
    file.close()

    FoundProprties = {}
    for line in FileLines:
        line = line.replace(" ", "")
        line = line.split("%", 1)[0] # Remove comments from the line

        if not line or "=" not in line:
            continue

        NameValueList = line.split("=", 1)
        if NameValueList[0].lower() not in VALIDACFPROPERTIES:
            continue

        FoundProprties[NameValueList[0]] = NameValueList[1]
    
    return FoundProprties

# Returns error value: True for success, False for failure
def Help(Command:str = "general"):
    Command = Command.lower()
    if Command == "general":
        print("Available commands:")
        print("  clear              Clear the screen")
        print("  cls                Clear the screen")
        print("  exit               Stop script execution")
        print("  quit               Stop script execution")
        print("  list               Show a list of available aircraft")
        print("  info               Show aircraft's property names and values")
        print("  help               Show this list or full commands' descriptions")
        print("  select             Load aircraft data to a default plane")
        print("  restore            Load backups of default aircraft to default aircraft")
        print("\nTo view full syntax description enter HELP COMMANDNAME or COMMANDNAME /?")
        print("\nExecute several commands at once with separators:")
        print("  [command1] &  [command2]...     Execute command1 and command2")
        print("  [command1];   [command2]...     Same as [command1] & [command2]...")
        print("  [command1] && [command2]...     Execute command2 if command1 is successful")
    elif Command == "help":
        print("Show command list or full command description")
        print("HELP [COMMAND_NAME]")
        print("COMMAND_NAME /?\n")
        print("COMMAND_NAME         Show description of this command")
        print("\nNOTE: If COMMAND_NAME is not specified, command list will be shown")
    elif Command in ["cls", "clear"]:
        print("Clear the screen")
        print("CLEAR")
        print("CLS")
    elif Command in ["exit", "quit"]:
        print("Stop script execution")
        print("EXIT")
        print("QUIT")
    elif Command == "list":
        print("Show a list of available aircraft")
        print("LIST")
    elif Command == "info":
        print("Show aircraft's property names and values")
        print("INFO [[AIRCRAFT_NAME] [PROPERTY_NAME]] | properties")
        print("AIRCRAFT_NAME        Specify aircraft to view properties")
        print("PROPERTY_NAME        Specify which aircraft's property (properties) to view,")
        print("                     shows basic properties (like thrust) when omitted.")
        print("properties           View list of valid property names")
    elif Command == "info properties":
        print("list of valid property names for ACF format:")
        LineLength = 0
        MaxLineLength = get_terminal_size()[0] -1
        PropertyListString = "  "
        for property in VALIDACFPROPERTIES:
            ProprertyLength = len(property) + 2
            if LineLength + ProprertyLength > MaxLineLength:
                PropertyListString = PropertyListString[:-2:] + "\n  "
                LineLength = 0
            else:
                PropertyListString += property + ", "
                LineLength += ProprertyLength
        
        print(PropertyListString[:-2:])
    elif Command == "select":
        print("Load aircraft data to a default plane")
        print("SELECT [DESIRED_AIRCRAFT] as [DEFAULT_AIRCRAFT]\n")
        print("DESIRED_AIRCRAFT     Specify what aircraft data to copy")
        print("DEFAULT_AIRCRAFT     Specify where aircraft data will be pasted to")
        print("\nNOTE: you can skip \"as\" keyword")
    elif Command == "restore": 
        print("Load backups of default aircraft to default aircraft")
        print("RESTORE [AIRCRAFTNAME | all]\n")
        print("AIRCRAFTNAME         Name of any default aircraft to restore")
        print("all                  Specify to restore all backed up aircraft")
    else:
        print(f"No information about \"{Command}\"")
        return False
    return True

def WrongArgumentAmount(ExpectedAmount):
    global NoError
    print(f"ERROR: Expected {ExpectedAmount} argument{'s'*(str(ExpectedAmount) != '1')}, got {ArgumentCount}")
    NoError = False

def SeparateCommand(Command: str) -> list[tuple[str, bool | None]]:
    Command = Command.replace(";", "&")

    Index = 0
    MaxIndex = len(Command)
    SeparatedCommands = []
    while Index <= MaxIndex:
        ConditionalSeparatorIndex    = Command[Index::].find("&&")
        ConditionalSeparatorIndex   += Index * (ConditionalSeparatorIndex != -1)
        
        UnconditionalSeparatorIndex  = Command[Index::].find("&")
        UnconditionalSeparatorIndex += Index * (UnconditionalSeparatorIndex != -1)

        if ConditionalSeparatorIndex == -1 and UnconditionalSeparatorIndex == -1:
            break
        elif ConditionalSeparatorIndex == -1:
            # Rig indices in favour of unconditional separator if conditional one is not found
            ConditionalSeparatorIndex = UnconditionalSeparatorIndex + 1
        # if ConditionalSeparator is found, UnconditionalSeparator will be found too

        IsConditional = UnconditionalSeparatorIndex >= ConditionalSeparatorIndex
        SeparatorIndex = min(UnconditionalSeparatorIndex, ConditionalSeparatorIndex)
        SeparatedCommands += [(Command[Index:SeparatorIndex:].strip(), IsConditional)]
        
        # Skip either "&" or "&&" correctly
        Index = SeparatorIndex + 1 + IsConditional
    
    SeparatedCommands += [(Command[Index::].strip(), None)]
    
    return SeparatedCommands

ShowPlanes()

print("\nTo select aircraft enter \"select [DESIRED_AIRCRAFT_NAME] as [DEFAULT_AIRCRAFT_NAME]\"")
print("Enter \"help\" for more commands\n")

CommandList : list[tuple[str, bool | None]] = []    
while True:
    if ENABLECONSTANTUPDATES:
        print("Scanning files...", end = "\r")
        UpdateFileList()
        print("\r", " " * 40, "\r", end = "")
    
    try:
        if not CommandList:
            Command = input("Enter Command:>").lower()
            CommandList = SeparateCommand(Command)
            
            for TestElement in [("", True), ("", False), ("", None)]:
                if TestElement in CommandList:
                    HasEmptyCommand = True
                    break
            else:
                HasEmptyCommand = False

            if HasEmptyCommand:
                if len(CommandList) > 1: 
                    print(f"ERROR: Empty command after or between separators\n")
                CommandList = []
                continue
            
        Command, IsCommandConditional = CommandList.pop(0)

    except KeyboardInterrupt:
        print()
        exit(6)
    except EOFError:
        exit(6)

    if Command.isspace() or not Command:
        continue

    ArgumentList = Command.split()
    CommandName = ArgumentList[0]
    ArgumentCount = len(ArgumentList) - 1
    NoError = True
    
    if CommandName == "help":
        if ArgumentCount:
            Help(" ".join(ArgumentList[1::]))
        else:
            Help()

    elif "/?" in ArgumentList:
        Help(CommandName)

    elif CommandName in ["exit", "quit"]:
        exit()
    
    elif CommandName in ["cls", "clear"]:
        cls()

    elif CommandName == "list":
        UpdateFileList()
        ShowPlanes()

    elif CommandName == "info":
        if not ArgumentCount:
            WrongArgumentAmount("1 or more")

        RequestedProperties = ArgumentList[2::]
        if RequestedProperties:
            for property in RequestedProperties:
                if property not in VALIDACFPROPERTIES:
                    PrintError(f"Requested invalid property \"{property}\"")

        if NoError and ArgumentList[1] == "properties":
            Help("info properties")
        elif NoError and ArgumentList[1] not in AircraftNames:
            PrintError(f"\"{ArgumentList[1]}\" is not a valid aircraft or keyword")
        elif NoError:
            Properties = InterpretateAircraftAsACF(ArgumentList[1])
            
            if RequestedProperties:
                print(f"Requested propert{['y', 'ies'][ArgumentCount != 2]}", end = " ")
            else:
                print("Basic properties", end = " ")

            print(f"for \"{ArgumentList[1]}\" aircraft:")
            for PropertyName in Properties:
                if RequestedProperties and PropertyName.lower() not in RequestedProperties:
                    continue
                if not RequestedProperties and PropertyName.lower() not in BASICACFPROPERTIES:
                    continue
                
                print(f"{PropertyName} = {Properties[PropertyName]}")

    elif CommandName == "select":
        if ArgumentCount == 1:
            PrintError("No default aircraft was specified")
        if NoError and ArgumentCount not in [2, 3]:
            WrongArgumentAmount("2 or 3")

        if NoError and ArgumentList[1] not in AircraftNames:
            PrintError(f"\"{ArgumentList[1]}\" is not a valid aircraft")
        if NoError and ArgumentList[1] in DEFAULTAIRCRAFTNAMES:
            PrintError(f"Can't select default aircraft. Use restore command instead")
        if NoError and ArgumentList[2] == "as" and ArgumentCount >= 3:
            ArgumentList.pop(2)
            ArgumentCount -= 1
        if NoError and ArgumentList[2] == "as" and ArgumentCount == 2:
            PrintError("No default aircraft was specified")
        if NoError and ArgumentList[2] not in DEFAULTAIRCRAFTNAMES:
            PrintError(f"\"{ArgumentList[2]}\" is not a default aircraft")

        if NoError:
            # Divided these conditions into seperate branches (they're too long)
            if ArgumentList[2] in AircraftMapping["backed up"]:
                print(f"Not overwritting stored backup of \"{ArgumentList[2]}\"")
            elif AircraftMapping[ArgumentList[2]] != ArgumentList[2]:
                print(f"Not overwritting stored backup of \"{ArgumentList[2]}\"")
            
            elif ArgumentList[2] in AircraftMapping and AircraftMapping[ArgumentList[2]] == ArgumentList[2]:
                FullBackupPath = f"{AircraftNameToPath[ArgumentList[2]]}.{BACKUPEXTENSION}"
                copy(f"{AircraftNameToPath[ArgumentList[2]]}", FullBackupPath)
                AircraftMapping[ArgumentList[2]] = ArgumentList[1]
                if ArgumentList[2] not in AircraftMapping["backed up"]:
                    AircraftMapping["backed up"] += [ArgumentList[2]]
                print(f"Backed up default aircraft \"{ArgumentList[2]}\"")
            else:
                print("WARNING: No safe backup is possible")
                Answer = AskUser(f"Overwrite data of \"{ArgumentList[2]}\" aircraft?", "yn", DefaultAnswer = "n")
                if Answer == "n":
                    print("Cancelled operation.")
                    NoError = False
            
            if NoError:
                copy(AircraftNameToPath[ArgumentList[1]], AircraftNameToPath[ArgumentList[2]])
                print(f"Selected \"{ArgumentList[1]}\" for \"{ArgumentList[2]}\"")

    elif CommandName == "restore":
        if ArgumentCount != 1:
            WrongArgumentAmount(1)

        if NoError:
            RestoreList = [[ArgumentList[1]], AircraftMapping["backed up"]][ArgumentList[1] == "all"]
        else: 
            RestoreList = []
        for backup in RestoreList:
            if NoError and backup not in DEFAULTAIRCRAFTNAMES:
                PrintError(f"Can't restore not default aircraft data {backup}")
            if NoError and backup not in BackupNames:
                PrintError(f"No \"{backup}\" backup found")
            if NoError:
                copy(BackupFullPaths[BackupNames.index(backup)], 
                     AircraftFolder + sep + backup + "." + AIRCRAFTEXTENTSION)
                AircraftMapping[backup] = backup
                print(f"Restored backup of \"{backup}\"")
            
            if RestoreList == BackupNames:
                NoError = True

    else:
        PrintError(f"\"{CommandName}\" is not a valid command")

    if CommandList and IsCommandConditional and not NoError:
        CommandList = []
    
    if not CommandList:
        print()

    SaveMappingJSON()
    if PRINTAIRCRAFTMAPPING:
        print(AircraftMapping)
