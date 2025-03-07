from json import dumps as ToJSON, loads as FromJSON
from json.decoder import JSONDecodeError
# TODO: Check for bugs

from os.path import abspath, exists, isdir, isfile
from os import sep, remove, listdir, system
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

    AircraftFullPaths = []
    AircraftNames = []
    BackupFullPaths = []
    BackupNames = []

    for FileName in listdir(AircraftFolder):
        FullFilePath = AircraftFolder + sep + FileName
        if isfile(FullFilePath):
            if FileName.lower().endswith("." + AIRCRAFTEXTENTSION):
                AircraftNames += [FileName[:-len(AIRCRAFTEXTENTSION) - 1]]
                AircraftFullPaths += [FullFilePath]
            if FileName.lower().endswith(BACKUPEXTENSION):
                BackupNames += [FileName[:-len(AIRCRAFTEXTENTSION) - len(BACKUPEXTENSION) - 2]]
                BackupFullPaths += [FullFilePath]

def PrintError(ErrorString:str):
    global NoError
    print(ErrorString)
    NoError = False

def GetTypeName(Value):
    return str(type(Value)).split()[-1][:-1:]

GivenArguments = argv[1::]

if not GivenArguments:
    ErrorExit("Expected to recive path to google earth aircrafts", 1)

AircraftFolder = abspath(GivenArguments[0])
if not exists(AircraftFolder):
    ErrorExit("Specified directory doesn't exist", 2)
if not isdir(AircraftFolder):
    ErrorExit("Specified path is not a directory", 3)

CONFIGFILE = AircraftFolder + sep + "aircraft-mappings.json"

UnexpectedError = None
try:
    TestPathFile = f"{AircraftFolder + sep}test.test"
    TestFile = open(TestPathFile, "wt")
    TestFile.close()
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
        PrintError("ERROR: Could not decode mapping file")
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
        print(f"expected 'list' for \"backed up\" field, recived {GetTypeName(AircraftMapping['backed up'])}")
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

#print("JSON\n" + ToJSON(MappingJSON, indent = 2))
#print("\nPYTHON\n" + str(MappingJSON))
#exit()
    
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

def Help(Command:str = "general"):
    Command = Command.lower()
    if Command == "general":
        print("Available commands:")
        print("  clear              Clear the screen")
        print("  cls                Clear the screen")
        print("  exit               Stop script execution")
        print("  quit               Stop script execution")
        print("  list               Show a list of available aircrafts")
        print("  help               Show this list or full commands' descriptions")
        print("  select             Load aircraft data to a default plane")
        print("  restore            Load backups of default aircrafts to default aircrafts")
        print("\nTo view full syntax description enter HELP COMMANDNAME or COMMANDNAME /?")
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
        print("Show a list of available aircrafts")
        print("LIST")
    elif Command == "select":
        print("Load aircraft data to a default plane")
        print("SELECT [DESIRED_AIRCRAFT] [as] [DEFAULT_AIRCRAFT]\n")
        print("DESIRED_AIRCRAFT     Specify what aircraft data to copy")
        print("DEFAULT_AIRCRAFT     Specify where aircraft data will be pasted to")
        print("\nNOTE: you can skip \"as\" keyword")
    elif Command == "restore": 
        print("Load backups of default aircrafts to default aircrafts")
        print("RESTORE [AIRCRAFTNAME | all]\n")
        print("AIRCRAFTNAME         Name of any default aircraft to restore")
        print("all                  Specify to restore all backed up aircrafts")
    else:
        print(f"No information about \"{Command}\"")

def WrongArgumentAmount(ExpectedAmount):
    global NoError
    print(f"ERROR: Expected {ExpectedAmount} argument{'s'*(str(ExpectedAmount) != '1')}, got {ArgumentCount}")
    NoError = False

ShowPlanes()

print("\nTo select aircraft enter \"select [DESIRED_AIRCRAFT_NAME] as [DEFAULT_AIRCRAFT_NAME]\"")
print("Enter \"help\" for more commands\n")

while True:
    if ENABLECONSTANTUPDATES:
        print("Scanning files...", end = "\r")
        UpdateFileList()
        print("\r", " " * 40, "\r", end = "")
    
    try:
        Command = input("Enter Command:>").lower()
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
            Help(ArgumentList[1])
        else:
            Help()

    elif "/?" in ArgumentList:
        Help(CommandName)

    elif CommandName in ["exit", "quit", "x", "q"]:
        exit()
    
    elif CommandName in ["cls", "clear"]:
        cls()

    elif CommandName == "list":
        UpdateFileList()
        ShowPlanes()

    elif CommandName == "select":
        if ArgumentCount not in [2, 3]:
            WrongArgumentAmount("2 or 3")

        if NoError and ArgumentList[1] not in AircraftNames:
            PrintError(f"ERROR: \"{ArgumentList[1]}\" is not a valid aircraft")
        if NoError and ArgumentList[1] in DEFAULTAIRCRAFTNAMES and NoError:
            PrintError("ERROR: Default aircrafts can't be selected, use restore command instead")
        if NoError and ArgumentList[2] == "as" and ArgumentCount >= 3 and NoError:
            ArgumentList.pop(2)
            ArgumentCount -= 1
        if NoError and ArgumentList[2] == "as" and ArgumentCount == 2 and NoError:
            PrintError("ERROR: No default aircraft was specified")
        if NoError and ArgumentList[2] not in DEFAULTAIRCRAFTNAMES and NoError:
            PrintError(f"ERROR: \"{ArgumentList[2]}\" is not a default aircraft")

        if NoError:
            if ArgumentList[2] in AircraftMapping["backed up"] or AircraftMapping[ArgumentList[2]] != ArgumentList[2]:
                print(f"Not overwritting stored backup of \"{ArgumentList[2]}\"")
            elif ArgumentList[2] in AircraftMapping and AircraftMapping[ArgumentList[2]] == ArgumentList[2]:
                FullBackupPath = f"{AircraftFolder}{sep}{ArgumentList[2]}.{AIRCRAFTEXTENTSION}.{BACKUPEXTENSION}"
                copy(f"{AircraftFolder}{sep}{ArgumentList[2]}.{AIRCRAFTEXTENTSION}", FullBackupPath)
                AircraftMapping[ArgumentList[2]] = ArgumentList[1]
                AircraftMapping["backed up"] += [ArgumentList[2]]*(ArgumentList[2] not in AircraftMapping["backed up"])
                print(f"Backed up default aircraft \"{ArgumentList[2]}\"")
            else:
                print("WARNING: No safe backup is possible")
                Answer = AskUser(f"Overwrite data of \"{ArgumentList[2]}\" aircraft?", "yn", DefaultAnswer = "n")
                if Answer == "n":
                    print("Cancelled operation.")
                    NoError = False
            
            if NoError:
                FullDesiredPath = AircraftFolder + sep + ArgumentList[1] + "." + AIRCRAFTEXTENTSION
                FullDefaultPath = AircraftFolder + sep + ArgumentList[2] + "." + AIRCRAFTEXTENTSION
                copy(FullDesiredPath, FullDefaultPath)
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
                PrintError(f"ERROR: Can't restore not default aircraft data {backup}")
            if NoError and backup not in BackupNames:
                PrintError(f"ERROR: No \"{backup}\" backup found")
            if NoError:
                copy(BackupFullPaths[BackupNames.index(backup)], 
                     AircraftFolder + sep + backup + "." + AIRCRAFTEXTENTSION)
                AircraftMapping[backup] = backup
                print(f"Restored backup of \"{backup}\"")
            
            if RestoreList == BackupNames:
                NoError = True

    else:
        print(f"ERROR: \"{CommandName}\" is not a valid command")

    SaveMappingJSON()
    if PRINTAIRCRAFTMAPPING:
        print(AircraftMapping)
    print()