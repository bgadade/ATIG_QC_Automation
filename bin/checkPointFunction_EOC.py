from PIL import Image
from importlib import import_module
import re
import lxml.html
from bin import constants
from bin import utils

extractCodeFromFile = lambda x: '_'.join(x.split('_')[:2])

def checkOverlap(sot, fNm, fextracted_content, argDi):

    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    errMsg = argDi.get('errMsg')

    bboxOfLastNElm = fextracted_content[pageid][contentid]['bbox']
    lwrbboxOfLastNElm = [bb[1] for bb in bboxOfLastNElm]
    uprbboxOfLastNElm = [bb[3] for bb in bboxOfLastNElm]

    for uprRight_n_1, lwrLeft_n in zip(uprbboxOfLastNElm[1:], lwrbboxOfLastNElm[:-1]):
        if uprRight_n_1 >= lwrLeft_n: return False, errMsg, '', ''
    return True, '', '', ''


def checkCMSCode(sot, fNm, fextracted_content, argDi):
    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    refVal = argDi.get('refVal')
    errMsg = argDi.get('errMsg')
    extVal = fextracted_content[pageid][contentid]['value']
    if extVal is None: return False, errMsg, "", "CMS Code"
    no_of_underscore = len(extVal.split('_'))-1
    if no_of_underscore == eval(refVal):
        return True, ""
    return False, errMsg, "", "CMS Code"

def checkAlignment(sot, fNm, fextracted_content, argDi):
    # write to handle content missing
    checkcontentid = argDi.get('contentid')
    checkpageid = argDi.get('pageid')
    checkImgNm = argDi.get('imgNm')
    compContentDe = argDi.get('comp')
    compContentid = compContentDe['contentid']
    comppageid = compContentDe['pageid']
    compOrient = compContentDe['orientation']
    errMsg = argDi.get('errMsg')
    offset = eval(compContentDe.get('offset'))

    if fextracted_content[checkpageid][checkcontentid]['value'] is None: return True, "Content Missing" + errMsg , '', ''
    if fextracted_content[comppageid][compContentid]['value'] is None: return False, "Missing Element to check alignment "+ errMsg, '', ''

    def checkLeftAlignment(checkcontBbox, compcontBbox):
        if checkcontBbox[0]<compcontBbox[0] and checkcontBbox[2]<=compcontBbox[0]:
            return True
        return False

    def checkInBetween(checkcontBbox, compcontBbox):# the lly or uly should be in between the lly and uly of compContent
        if (compcontBbox[1]<=checkcontBbox[1] and checkcontBbox[1]<=compcontBbox[3]) or (compcontBbox[1]<=checkcontBbox[3] and checkcontBbox[3]<=compcontBbox[3]):
            return True
        return False

    def checkHeight(checkcontBbox, compcontBbox):
        return compcontBbox[3]- checkcontBbox[3]

    checkcontBbox= fextracted_content[checkpageid][checkcontentid]['bbox']
    compcontBbox= fextracted_content[comppageid][compContentid]['bbox']
    if compOrient == "leftHeight":
        if checkLeftAlignment(checkcontBbox, compcontBbox) and abs(checkHeight(checkcontBbox, compcontBbox))<=offset:
            return True, ""
    elif compOrient == "left":
        if checkLeftAlignment(checkcontBbox, compcontBbox):
            return True, ""
    return False, checkImgNm+" "+errMsg, "", ""

def checkCodeWithFileName(sot, fNm, fextracted_content, argDi):
    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    deriveRef = argDi.get('deriveRef')
    deriveRef = eval(deriveRef)
    errMsg = argDi.get('errMsg')
    pdfVal = fextracted_content[pageid][contentid]['value']
    if pdfVal is None: return False, "Code with partly filename missing", ' ', deriveRef(fNm)
    if pdfVal == deriveRef(fNm):
        return True, "", "", ""
    return False, errMsg, pdfVal, deriveRef(fNm)


def compareExtText(sot, fNm, fextracted_content, argDi):
    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    refVal = argDi.get('refVal')
    errMsg = argDi.get('errMsg')
    pdfVal = fextracted_content[pageid][contentid]['value']
    if pdfVal is None: return False, "Unable to locate text", ' ', refVal
    if pdfVal == refVal:
        return True, "", "", ""
    return False, errMsg, pdfVal, refVal

def matchImage(extractedImgPath, refImgPath):
    im1 = Image.open(extractedImgPath)
    im2 = Image.open(refImgPath)

    if list(im1.getdata()) == list(im2.getdata()):
        return True
    return False


def compareExtImg(sot, fNm, fextracted_content, argDi):
    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    refImgPath = argDi.get('refVal')
    errMsg = argDi.get('errMsg')
    imgN = refImgPath.split('/')[-1].split('.')[0]
    extractedImgPath = fextracted_content[pageid][contentid]['value']
    if extractedImgPath is None: return False, imgN+" Image not found", ' ', imgN
    if matchImage(extractedImgPath, refImgPath):
        return True, "", "", ""
    return False, imgN+" "+errMsg, 'img', imgN

#--------- Shraddha ---------
def extractFromPdfTable(pdfTextDf,sotProduct):
    isPrdHMO=True if sotProduct == 'HMO' else False
    diInpVal = {}
    module = import_module('medChartRules')
    if not isPrdHMO:
        for dic in constants.medChartJson:
            pdfRow = pdfTextDf[pdfTextDf['Services'].str.contains(dic['search'])].to_dict('records')
            if pdfRow:
                pdfRow=pdfRow[0]
                diInpVal[dic['search']] = {"In Network": {"pdfText": eval(pdfRow['In Network'])['data']}, "Out of Network": {"pdfText": eval(pdfRow['Out of Network'])['data']}}
                for func, outCol in dic['derivations'].items():
                    diInpVal[dic['search']]['In Network'][outCol], diInpVal[dic['search']]['Out of Network'][outCol] = getattr(module, func)(pdfRow,isPrdHMO)
            else:
                diInpVal[dic['search']] = {"In Network": {"pdfText":"N/A"}, "Out of Network": {"pdfText":"N/A"} }
                for func, outCol in dic['derivations'].items():
                    diInpVal[dic['search']]['In Network'][outCol], diInpVal[dic['search']]['Out of Network'][outCol] = 'N/A','N/A'
        return diInpVal

    for dic in constants.medChartJson:
        pdfRow = pdfTextDf[pdfTextDf['Services'].str.contains(dic['search'])].to_dict('records')
        if pdfRow:
            pdfRow=pdfRow[0]
            diInpVal[dic['search']] = diInpVal[dic['search']] = {"In Network": {"pdfText": eval(pdfRow['In Network'])['data']}}
            for func, outCol in dic['derivations'].items():
                diInpVal[dic['search']]['In Network'][outCol] = getattr(module, func)(pdfRow, isPrdHMO)

        else:
            diInpVal[dic['search']] = {"In Network": {"pdfText": "N/A"}}
            for func, outCol in dic['derivations'].items():
                diInpVal[dic['search']]['In Network'][outCol] = 'N/A'

    return diInpVal

def extractFromSot(diInpVal, filteredDF):
    print(filteredDF)
    diSotVal = {search:{network:{outCol: str(filteredDF.loc[filteredDF['In Network_Out of Network']== network][outCol].values[0])
                        for outCol, val in dict2.items() if outCol != 'pdfText'}
                        for network, dict2 in dict1.items()}
                        for search,dict1 in diInpVal.items()}
    return diSotVal

def getErrorsforTable(diInpVal, diSotVal):
    checkSuccess, errorMessage, actual, expected = [], [], [], []
    for search, dict1 in diSotVal.items():
        for network, dict2 in dict1.items():
            for outCol, val in dict2.items():
                if diInpVal[search][network][outCol] == 'N/A' and val!='':
                    checkSuccess.append(False)
                    errorMessage.append(search + "-" + network + "-" + outCol + "- missing in PDF")
                    expected.append(val)
                    actual.append(diInpVal[search][network][outCol])
                elif diInpVal[search][network][outCol] == 'N/A' and val == '':
                    checkSuccess.append(True)
                    errorMessage.append("")
                    expected.append("")
                    actual.append("")
                elif diInpVal[search][network][outCol] != val :
                    checkSuccess.append(False)
                    errorMessage.append(search + "-" + network + "-" + outCol + "- value mismatch")
                    expected.append(val)
                    actual.append(diInpVal[search][network][outCol])
                else:
                    checkSuccess.append(True)
                    errorMessage.append("")
                    expected.append("")
                    actual.append("")
    return checkSuccess, errorMessage, actual, expected

def xmlToText(x):
    cellVal=eval(x)
    id = cellVal['id']
    xmlData = cellVal['data']
    newCellVal={'id':id,'data':''}
    if xmlData:
        tr = lxml.html.fromstring(xmlData)
        newCellVal['data']=re.sub('\n+', '', tr.xpath('string(.)'))
    return str(newCellVal)

def tableXmltoText(pdfTableDF):
    textTableDF = pdfTableDF.applymap(xmlToText)
    return textTableDF

def compareTable(sot, fNm, fextracted_content, argDi):
    contentid = argDi.get('contentid')
    pageid = argDi.get('pageid')
    pdfTableDF = fextracted_content[pageid][contentid]['value']
    colMap = {inpCol:utils.mapStdValues(inpCol,['Services', 'In Network', 'Out of Network']) for inpCol in pdfTableDF.columns}
    pdfTableDF.rename(columns=colMap,inplace=True)
    textTableDF = tableXmltoText(pdfTableDF)
    sheetName = 'Employer Group_MBG'
    filteredDF = sot['excelData'][sheetName]
    sotProduct=filteredDF['Product (HMO, POS, LPPO, RPPO, PFFS, PDP)'].iloc[0]
    diInpVal = extractFromPdfTable(textTableDF,sotProduct)

    diSotVal = extractFromSot(diInpVal, filteredDF)
    errorMessage = getErrorsforTable(diInpVal, diSotVal)
    return errorMessage