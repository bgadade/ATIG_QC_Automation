import json
import pandas as pd
from bin import constants
def readFile(path, type, sheetIndex = 0, headerIndx = 0,colAsStr=False): #Todo: include read word file functionality.
    if headerIndx !=0:
        headerIndx = headerIndx - 1

    if type == "xlsx":
        inputFile = pd.read_excel(open(path, "rb"), sheet_name= sheetIndex, skiprows = headerIndx)
        if colAsStr:
            lenLstCols = len(inputFile.columns.tolist())
            diConverter = {col: str for col in range(lenLstCols)}
            inputFile = pd.read_excel(open(path, "rb"), sheet_name=sheetIndex, skiprows=headerIndx,converters=diConverter,  na_values = ["na", "n/a", "None", "none", "Na"])
        inputFile.columns = inputFile.columns.str.strip()  # remove spaces from column names
        inputFile.columns = inputFile.columns.str.lower()  # converting inputDF columns to lowercase.
        return inputFile
    elif type == "json":
        with open(path) as json_data:
            configFile = json.load(json_data)
            return configFile
    else:
        raise AssertionError("Unsupported file format!", type)

def mapStdValues(inpVal,lstStdKey):
    for stdKey in lstStdKey:
        stdKeyVal=constants.std[stdKey]
        if isinstance(stdKeyVal,dict):
            for key,inp in stdKeyVal.items():
                if inpVal.lower().strip() in [elm.lower().strip() for elm in inp]:
                    return key
        elif isinstance(stdKeyVal,list):
            if inpVal.lower().strip() in [elm.lower().strip() for elm in stdKeyVal]:
                return stdKey
    return inpVal

def lJustPgNo(pgNo, numOfPage):
    return str(pgNo).zfill(len(str(numOfPage)))