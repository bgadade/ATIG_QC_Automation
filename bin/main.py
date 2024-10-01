import subprocess
from bin import constants
import lxml
import lxml.html
import re
from bin import utils
import pandas as pd
from lxml import etree
import json
import xlrd
import pickle
import os
import glob
import copy
import string
pdf2htmlExePath=constants.pdf2htmlExePath
from bin import convertPdf
inpPath=constants.inpPath
outPath=constants.outPath
from importlib import import_module
import numpy as np
from bin import pdfExtractionUtils as pdfExtUtils
from os.path import abspath, dirname, join
from PIL import Image
import math

from bin import extractTableWrapper as tblExtWrap

def convertToHtml(inpFile,outFile):
    output=subprocess.check_output([pdf2htmlExePath,inpFile,outFile],shell=True)
    return output

def queryXml(tree,sel,text=False, textFontSize=False):
    lstElm=tree.xpath(sel)
    diElm={}
    for elm in lstElm:
        bboxStr=elm.xpath("normalize-space(.//@bbox)")
        bbox=tuple([float(elm) for elm in bboxStr.split(',')])
        if text:
            textf = "".join(elm.xpath('.//text()'))
            textf = re.sub('\n+', '', textf)
            if textFontSize:
                textFont, textSize = "", ""
                if elm.tag == "textline":
                    textFont = elm.xpath('.//text')[0].xpath("normalize-space(.//@font)")
                    textSize = elm.xpath('.//text')[0].xpath("normalize-space(.//@size)")
                diElm[bbox] = (elm.tag, [textf.strip(), textFont, textSize])
            else:
                diElm[bbox] = (elm.tag, textf.strip())
            # text = "".join(elm.xpath('.//text()'))
            # text = re.sub('\n+', '', text)
            # diElm[bbox]=text.strip()
        else:
            diElm[bbox] = (elm.tag,lxml.html.tostring(elm)) # should we write logic here for text extraction, helpful for all children extraction part
    return diElm



def applyFilter(parsed,filter,filters):
    fltNm=filter['name']
    fltOrdBy=filter.get('order_by')
    fltOrdTyp=filter.get('reverse')
    fltDi=filters[fltNm]
    if fltDi["type"] == 'txtLn':
        res= getContentInTxtLnBound(parsed, upper=fltDi["param"][0],lower=fltDi["param"][1])
    elif fltDi["type"] == 'tagPos':
        res= getContentByTagPos(parsed, **{fltDi["subType"]: fltDi["param"]})
    elif fltDi["type"] == 'coord':
        res= getContentInCoordBound(parsed)
    if fltOrdBy=='x':
        return sorted(res,key=lambda tup:tup[0],reverse=fltOrdTyp)
    return res



def getContentMult(parsed,diBound):
    diBoundC={k:None for k,v in diBound.items() if k not in ["filters"]}
    for k,bound in diBound.items():
        if k in ["filters"]:
            continue
        if bound["type"]=='txtLn':
            res=getContentInTxtLnBound(parsed,upper=bound["param"][0], lower=bound["param"][1])
            diBoundC[k] = [tup[1] for tup in res]
        elif bound["type"] == 'tagPos':
            if 'filter' in bound:
                fltRes=applyFilter(parsed,bound['filter'],diBound['filters'])
                res = getContentByTagPos(fltRes, **{bound["subType"]: bound["param"]})
            else:
                res=getContentByTagPos(parsed,**{bound["subType"]:bound["param"]})
            diBoundC[k] = res[1]
        elif bound["type"] == 'coord':
            res=getContentInCoordBound(parsed)
            diBoundC[k]=res[1]
    return diBoundC

def getContentInTxtLnBound(parsed,upper=None,lower=None):
    v=[tup[1] for tup in parsed]
    if not(upper or lower):
        return parsed
    if upper and lower:
        ix1=v.index(upper)+1
        ix2=v.index(lower)
        return parsed[ix1:ix2]
    elif upper and not lower:
        ix1 = v.index(upper) + 1
        return parsed[ix1+1:]
    elif not upper and lower:
        ix2 = v.index(lower)
        return parsed[:ix2]


def getContentInCoordBound(parsed,bbox=None,upper=0,lower=None,right=None,left=None):
    pass

def getContentByTagPos(parsed,upper=None,lower=None,nthTop=None,nthBtm=None,head=None,tail=None):
    if nthTop:
        return parsed[nthTop-1]
    elif nthBtm:
        return parsed[-nthBtm]
    elif head:
        return parsed[:head]
    elif tail:
        return parsed[-tail:]
    elif not(upper or lower):
        return parsed
    elif upper and lower:
        return parsed[upper+1:lower]
    elif upper and not lower:
        return parsed[upper+1:]
    elif not upper and lower:
        return parsed[:lower]

def parseTree(tree,selKey='textline',pageNo=1,sort=True,text=False, textFontSize=False):
    diTags = queryXml(tree, constants.diSel[selKey].format(int(pageNo)),text=text, textFontSize=textFontSize)
    if sort:
        srt = sorted(zip(diTags.keys(), diTags.values()), key=lambda tup: (-tup[0][1],tup[0][0]))
        return srt
    return diTags

def convertMultiple(lstFiles):

    diOut={}
    for f in lstFiles:
        inpFile=inpPath+f+'.pdf'
        output=convertPdf.convert_pdf_doc(inpFile)
        diOut[f]=output
    return diOut

def cleanContents(di):
    for k in ["RX_BIN","RX_PCN","RX_GRP"]:
        if di[k]:
            di[k]="".join(di[k]).split(":")[1].strip()
        else:
            di.pop(k)
    return di

def findPgTag(tree):
    return len(tree.xpath("//page"))

def parseMultiple(diXml,pages=None,selKey='textline',text=True, sort=True, textFontSize=False):
    diParsed = {}
    for f,xml in diXml.items():
        tree = lxml.html.fromstring(xml)
        numOfPages=findPgTag(tree)
        pageDi={}
        if pages:
            for pgNo in pages:
                parsed = parseTree(tree,selKey=selKey,pageNo=pgNo,text=text,sort=sort, textFontSize=textFontSize)
                pageDi.update({pgNo:parsed})
        else:
            for pgNo in range(1,numOfPages+1):
                parsed = parseTree(tree,selKey=selKey,pageNo=pgNo,text=text, sort=sort, textFontSize=textFontSize)
                pageDi.update({pgNo:parsed})
        diParsed.update({f:pageDi})
    return diParsed

def extractData(diParsed):
    diData = {}
    for f, diTag in diParsed.items():
        lang = getFParts(f, type='lang')
        pg1=diTag[1]
        di = getContentMult(pg1, constants.diBound[lang])
        di = cleanContents(di)
        diData.update({f: di})
    return diData


def getFParts(fNm,type=None):
    fParts=dict(zip(['lang_comp_code', 'lang', '_'], re.split('_([A-Z]+)_', fNm)))
    if type:
        return fParts[type]
    return fParts

def validateMultiple(lstFiles,diInpData):
    lstValidation = []
    refDf = cleanRefDf(constants.refDf)
    for f in lstFiles:
        fParts=getFParts(f)
        if fParts['lang']=='E':
            compCdCol='ENGLISH_COMPONENT_CODE'
            cmsCdCol='ENGLISH_CMS_CODE'
        elif fParts['lang']=='SP':
            compCdCol = 'SPANISH_COMPONENT_CODE'
            cmsCdCol = 'SPANISH_CMS_CODE'
        diRefData=dict(refDf.loc[refDf[compCdCol]==fParts['lang_comp_code'],['RX_BIN','RX_PCN','RX_GRP',compCdCol,cmsCdCol]].iloc[0])
        diRefData=standardiseKeys(diRefData,stdKey="inpVal")
        diInpDataF=standardiseKeys(diInpData[f],stdKey="inpVal")
        lstValidation.append(validateData(f,fParts['lang_comp_code'],diRefData,diInpDataF))
    dfValidation=pd.DataFrame(lstValidation)
    return dfValidation

def main(lstFiles):
    diOut=convertMultiple(lstFiles)
    diParsed=parseMultiple(diOut)
    diInpData=extractData(diParsed)
    dfValidation=validateMultiple(lstFiles,diInpData)
    summ=getSummStats(dfValidation,['status'])
    dfJson=dfValidation.rename(columns=constants.outJsnKeysMap)
    lstDict=[dict(tup[1]) for tup in dfJson.iterrows()]
    jsn={'data':lstDict,'stats':summ}
    return jsn
    dfOutput = dfValidation.rename(columns=constants.outputColMap)
    # dfOutput.to_excel(constants.outputFilePath,index=False)

def validateData(fileNm,lang_comp_code,diRefData,diInpData):
    failureKeys=[]
    di={'status':'Pass','remark':'','lang_comp_code':lang_comp_code,'qa_analyst':"","file_name":fileNm}
    if diRefData.keys()==diInpData.keys():
        for k in diRefData.keys():
            if not diRefData[k]==diInpData[k]:
                failureKeys.append(k)
                di['status']='Fail'
    if failureKeys:
        di['remark']='Validation failed for: {0}'.format(','.join(failureKeys))
    return di

def cleanRefDf(refDf):
    inpColMap=constants.inpColMap
    diRename={}
    for inpCol in [col.lower().strip() for col in refDf.columns]:
        for stdCol,lstInpCol in inpColMap.items():
            if inpCol in [col.lower().strip() for col in lstInpCol]:
                diRename[inpCol]=stdCol

        refDf=refDf.rename(columns=diRename)
    return refDf

def standardiseKeys(di,stdKey):
    newKeys=[utils.mapStdValues(key,[stdKey]) for key in di.keys()]
    return dict(zip(newKeys,di.values()))

def getSummStats(df,aggCols):
    summ=df.groupby(aggCols)['file_name'].agg(['count']).to_dict()
    return summ


#-------------------------- Checking Credentials -------------------------------------#

def validateCredentials(_name,_password,_domain):
    role=''
    if _domain ==None:
        _domain = ""
    credentialsPath = "../config/credentials.json"
    with open(credentialsPath) as json_data:
        credentialsData = json.load(json_data)
    for i in credentialsData:
        user = i['userName']
        password = i['password']
        domain = i["domain"]
        role = i['role']
        if user == _name  and password == _password and domain ==_domain:
            if role == 'admin':
                msg = 'Successfully logged in as admin'
                return role
            else:
                msg = 'Successfully logged in as user'
                return role
    msg = 'Invalid Credentials'
    return msg


#-------------------------- Reading File -------------------------------------#
def getFileJSON(filename):
    credentialsPath = "../config/" + filename
    with open(credentialsPath) as json_data:
        data = json.load(json_data)
    return data


def setJSONData(data,filename):
    with open("../config/"+filename,'w') as outfile:
        try:
            outfile.write(json.dumps(data,indent=True))
        except Exception as e:
            print(e)


def addCredentials(data):
    credentialsPath = "../config/credentials.json"
    with open(credentialsPath) as json_data:
        originalData = json.load(json_data)
    originalData.append(data)
    #print("originalData:",originalData)
    with open(credentialsPath,'w') as outfile:
        try:
            outfile.write(json.dumps(originalData,indent=True))
        except Exception as e:
            print(e)


def createPickle(token, filename, year):
    st = {"PlanYear": ["PlanYear", "Plan year"]}
    file = inpPath + filename
    excelData = {}
    workbook = xlrd.open_workbook(file)
    for idx, sheet in enumerate(workbook._sheet_names):
        df = pd.read_excel(open(file, 'rb'), sheet_name=sheet).fillna('')
        df.columns = df.columns.str.replace('/', '_')
        planYearCol = [col for col in df.columns if col in st['PlanYear']][0]
        df.rename(columns={planYearCol: list(st.keys())[0]}, inplace=True)
        excelData[sheet] = df.loc[df['PlanYear'] == int(year)].reset_index(drop="True")
    sot = {'excelData':excelData, 'year':year}
    with open('../tmp/'+token+'SOT.pkl', 'wb') as fp:
        pickle.dump(sot, fp)


# -------------------------- Mayank Kumar ------------------------------ #
#------------------- Image Extraction Code ---------------- #

def mapCoord(elm):
    return math.floor((elm/72)*150)

def mapCoordBbox(Bbox,offset):
    Bbox[1]+=offset
    Bbox[3]-=offset
    return [mapCoord(elm) for elm in Bbox]

def uLefttoLLeft(imgBbox,yMax):
    x1,y1,x2,y2=imgBbox
    y1=yMax-y1
    y2=yMax-y2
    return (x1,y2,x2,y1)


def translateBbox(pdfBbox,yMax):
    imgBbox=mapCoordBbox(pdfBbox,0)

    newImgBbox=list(uLefttoLLeft(imgBbox,yMax))
    if newImgBbox[0]==newImgBbox[2]:
        newImgBbox[0]-=1
        newImgBbox[2]+=1
    if newImgBbox[1]==newImgBbox[3]:
        newImgBbox[1]-=1
        newImgBbox[3]+=1
    return tuple(newImgBbox)

def cropMultiBoxes(fNm, inpFileNm,lstBbox,inpDir=constants.imageDir,outDir=constants.imageDir):
    inpfileNmNoExt=inpFileNm.split('.png')[0]
    inpFilePath=inpDir+fNm+'/'+inpFileNm
    outExt='.png'
    im=Image.open(inpFilePath)
    if not os.path.exists(outDir+inpfileNmNoExt):
        os.makedirs(outDir+inpfileNmNoExt)
    for bBox in lstBbox:
        bBox=list(bBox)
        outFilePath=outDir+inpfileNmNoExt+'/'+str(bBox)+outExt
        xMax = im.size[0]
        yMax = im.size[1]
        newBbox=translateBbox(bBox,yMax)
        outImg=im.crop(newBbox)
        try:
            print('outfilePath==> {0}'.format(outFilePath))
            outImg.save(outFilePath,"PNG")
        except Exception as e:
            print(e.__str__())
            pass
    im.close()


def pdfToImg(fNm, stPage, enPage):
    fPath=constants.inpPath+fNm+'.pdf'
    absFPath = abspath(join(dirname(__file__), fPath))
    outPath=constants.imageDir+fNm
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    absOutPath=abspath(join(dirname(__file__), outPath, fNm))
    pdfToImgToolPath=abspath(join(dirname(__file__),constants.pdfToImgToolPath))
    subprocess.check_call('"%s" -png -f %s -l %s %s %s ' % (pdfToImgToolPath, stPage, enPage, absFPath,absOutPath))
#------------------- Image Extraction Code End---------------- #

def findPageForText(fDictPageText, text, font, size, offset, startFrom=1):
    totalPages = len(fDictPageText.keys())
    ctr = -1
    for pageNo in range(startFrom, totalPages+1):
        bbox, textonPageWithFontAndSize = list(zip(*fDictPageText[pageNo]))
        if size:
            textonPageWithFontAndSize = [elmTypeNValTup[1] for elmTypeNValTup in list(textonPageWithFontAndSize)]
            looking_for = [text, font, size]
        else:
            textonPageWithFontAndSize = [elmTypeNValTup[1][:2] for elmTypeNValTup in list(textonPageWithFontAndSize)]
            looking_for = [text, font]

        get_indexes = lambda looking_for_, xs: [i for (y, i) in zip(xs, range(len(xs))) if looking_for_ == y]

        if looking_for in textonPageWithFontAndSize:
            indexes = get_indexes(looking_for, textonPageWithFontAndSize)
            if ctr+len(indexes)>= eval(offset):
                i = eval(offset)-ctr-1
                return pageNo, bbox[indexes[i]]
            else:
                ctr += len(indexes)

    return None, None # handle None in lower segment


def pageLocator(fDictPageText, pageLocatorDict, docType, docYear):
    pageMap = {}
    for pageid, pageDesc in pageLocatorDict[docType][docYear].items():
        if "pageIndex" in pageDesc:
            pageMap[pageid] = {}
            pageMap[pageid]['mapTo'] = [sorted(fDictPageText.keys())[pageDesc["pageIndex"]]]
            pageMap[pageid]['purpose'] = pageDesc["purpose"]

        elif "fromFindText" in pageDesc and "toFindText" in pageDesc :#as per design from will alway have to, so not putting check for that
            startfrom = 1
            for textDetailDic in pageDesc["fromFindText"]:
                if startfrom is None: pageMap[pageid] = {'mapTo':None}; break
                startfrom, startTextBB = findPageForText(fDictPageText, textDetailDic['text'], textDetailDic['font'], textDetailDic['size'],textDetailDic['offset'], startFrom=startfrom)
            if startfrom is None: pageMap[pageid] = {'mapTo': None}; continue
            toend = startfrom
            for textDetailDic in pageDesc["toFindText"]:
                if toend is None: pageMap[pageid] = {'mapTo':None}; break
                toend, endTextBB = findPageForText(fDictPageText, textDetailDic['text'], textDetailDic['font'],
                                            textDetailDic['size'], textDetailDic['offset'], startFrom=toend)
            if toend is None: pageMap[pageid] = {'mapTo': None}; continue
            pageMap[pageid] = {}
            pageMap[pageid]['mapTo'] = list(range(startfrom, toend+1))[:3]
            pageMap[pageid]['purpose'] = pageDesc["purpose"]
            pageMap[pageid]['startTextBB'] = startTextBB
            pageMap[pageid]['endTextBB'] = endTextBB

    return pageMap

def pageLocatorWrapper(diTagsText, pageLocatorDict, docTypeAndYear):
    pageLocatorRes = {}
    for fNm, fDictPageText in diTagsText.items():
        res = pageLocator(fDictPageText, pageLocatorDict, docTypeAndYear[0], docTypeAndYear[1])
        pageLocatorRes.update({fNm:res})
    return pageLocatorRes

def extractTextContentFromPage(fDictPageFigText, flocated_page, contentLocatorDet, contentAbsltLoc):
    contentAbsIndex = eval(contentLocatorDet['contentIndex'])
    mappedInpPageNoList = flocated_page[contentLocatorDet['pageId']]['mapTo']
    if contentAbsIndex is None:
        if contentAbsltLoc[contentLocatorDet['refContentid']] is None: return None, None, None
        contentAbsIndex = contentAbsltLoc[contentLocatorDet['refContentid']]+eval(contentLocatorDet['offsetNum'])
    #assuming always mapped to single page. Also can simply append the next page sorted xml to run query
    if isinstance(contentAbsIndex, list):
        extContent = [fDictPageFigText[mappedInpPageNoList[0]][idx] for idx in contentAbsIndex]
        bboxVal = [cont[0] for cont in extContent]
        extractedVal = [cont[1][1] for cont in extContent]
    else:
        if contentAbsIndex > len(fDictPageFigText[mappedInpPageNoList[0]]) - 1: return None, None, None
        extContent = fDictPageFigText[mappedInpPageNoList[0]][contentAbsIndex]
        bboxVal = extContent[0]
        extractedVal = extContent[1][1]

    if contentAbsIndex == -1 : contentAbsIndex = len(fDictPageFigText[mappedInpPageNoList[0]])-1
    return bboxVal, extractedVal, contentAbsIndex

def elmInSearchregion(fDictPageFig, searchRegion):
    bboxL, elmTypeL  = list(zip(*fDictPageFig))
    elmInRegion = [bbox for bbox in bboxL if searchRegion[0]<=bbox[0] and searchRegion[2]>=bbox[0]  and searchRegion[1]<=bbox[1] and searchRegion[3]>=bbox[1]  and searchRegion[0]<=bbox[2] and searchRegion[2]>=bbox[2]  and searchRegion[1]<=bbox[3] and searchRegion[3]>=bbox[3]]
    print(elmInRegion)
    return elmInRegion

def extractImgContentFromPage(fNm,pagesInFile, fDictPageFig, flocated_page, contentLocatorDet):

    mappedInpPageNoList = flocated_page[contentLocatorDet['pageId']]['mapTo']
    totalPageInFile = pagesInFile
    justPgNo = utils.lJustPgNo(mappedInpPageNoList[0], totalPageInFile)
    imgFNm = '{0}-{1}.png'.format(fNm, justPgNo)
    # bbox in given region from all the fig element of the page
    searchRegion = eval(contentLocatorDet['regionBbox'])
    ix = eval(contentLocatorDet['ix'])
    elmList = elmInSearchregion(fDictPageFig[mappedInpPageNoList[0]], searchRegion)
    if ix > len(elmList) - 1: return None, None
    bboxForImg = elmList[ix]
    cropMultiBoxes(fNm, imgFNm, [bboxForImg], outDir=constants.outDir)
    croppedImageLoc = constants.outDir + imgFNm.split('.png')[0] + '/' + str(list(bboxForImg)) + '.png'
    return bboxForImg, croppedImageLoc


def contentExtractor(fNm, diOut, pagesInFile, fDictPageFigText, fDictPageFig, flocated_page, contentLocatorDict, docType, docYear):
    contentExtracted = {}
    contentAbsltLoc = {}
    contentLocatorDicAssoc = contentLocatorDict[docType][docYear]
    sortedKeys = [eval(k) for k in contentLocatorDicAssoc.keys()]
    for contentid in sortedKeys:
        contentid =str(contentid)
        pageid_for_content = contentLocatorDicAssoc[contentid]['pageId']
        if pageid_for_content not in contentExtracted:contentExtracted[pageid_for_content] = {}
        if flocated_page[pageid_for_content]['mapTo'] is None: contentExtracted[pageid_for_content].update({contentid: {'type': None, 'value': None, 'bbox': None}}); continue
        if contentLocatorDicAssoc[contentid]['type'] == "Text":
            bboxV, extractedVal, contentAbsIndex = extractTextContentFromPage(fDictPageFigText, flocated_page, contentLocatorDicAssoc[contentid], contentAbsltLoc)
            contentAbsltLoc[contentid] = contentAbsIndex
            if isinstance(extractedVal[0], list):
                extV, font, size = list(zip(*extractedVal))
                contentExtracted[pageid_for_content].update({contentid: {'type': "Text", 'value': extV,
                                                                         "font": font,
                                                                         "size": size, "bbox": bboxV}})
            else:
                contentExtracted[pageid_for_content].update({contentid:{ 'type': "Text", 'value': extractedVal[0], "font":extractedVal[1], "size":extractedVal[2], "bbox":bboxV}})

        elif contentLocatorDicAssoc[contentid]['type'] == 'Img':
            bboxV, extractedImgPath = extractImgContentFromPage(fNm, pagesInFile, fDictPageFig, flocated_page,
                                                                contentLocatorDicAssoc[contentid])
            contentExtracted[pageid_for_content].update({contentid: {'type': "Img", 'value': extractedImgPath, 'bbox':bboxV}})

        elif contentLocatorDicAssoc[contentid]['type'] == 'Table':
            mapped_page_list = flocated_page[contentLocatorDicAssoc[contentid]['pageId']]['mapTo']
            stTxlLnBbx = flocated_page[contentLocatorDicAssoc[contentid]['pageId']]['startTextBB']
            endTxlLnBbx = flocated_page[contentLocatorDicAssoc[contentid]['pageId']]['endTextBB']
            ix = eval(contentLocatorDicAssoc[contentid]['ix'])
            diTbl = tblExtWrap.extractTableMultiple(fNm, diOut, pgLst=mapped_page_list, stTxlLnBbx=None, endTxlLnBbx=None, ix=ix)
            tblExtWrap.debugDiTbl(diTbl)
            if constants.combineDf:
                fnlTbl = tblExtWrap.combineDfs(diTbl)
                dfHtm, dfTxt = tblExtWrap.debugDf(diTbl, fnlTbl)
            contentExtracted[pageid_for_content].update(
                {contentid: {'type': "Table", 'value': fnlTbl}})

    return contentExtracted

def contentExtractorWrapper(diOut, pagesInFile, diTagsFigAndText, diTagsFigs, located_page, contentLocatorDict, docTypeAndYear):
    contentExtractorRes = {}
    for fNm, fDictPageFigText in diTagsFigAndText.items():
        res = contentExtractor(fNm, diOut,pagesInFile, fDictPageFigText, diTagsFigs[fNm], located_page[fNm], contentLocatorDict, docTypeAndYear[0], docTypeAndYear[1])
        contentExtractorRes.update({fNm: res})
    return contentExtractorRes


def applyCheckpoints(filteredSot, fNm, fextracted_content, transformationList):
    tempCheckPointRes = []
    module = import_module('checkPointFunction_EOC')
    for checkPointDict in transformationList:
        for checkPointName, checkPointDervDict in checkPointDict.items():
            for subCheckIdx, func in enumerate(checkPointDervDict["derivations"]):
                funcName = func["name"]
                funcInpDic = func["input"]
                try:
                    checkSuc, errMsg, actual, expected = getattr(module,funcName)(filteredSot, fNm, fextracted_content, funcInpDic)
                    if isinstance(checkSuc, list):
                        for subCheckIdx, suc in enumerate(checkSuc):
                            if not suc: tempCheckPointRes.append(checkPointName + '\nIssue Description:' + errMsg[subCheckIdx] +'\nActual (Output):'+ actual[subCheckIdx]+ '\nExpected (SOT):' +expected[subCheckIdx])
                    else :
                        if not checkSuc: tempCheckPointRes.append(checkPointName + '\nIssue Description:' + errMsg +'\nActual (Output):'+ actual+ '\nExpected (SOT):' +expected)
                except:
                    continue
    #        if tempCheckPointRes : res[checkPointName] = tempCheckPointRes
    #if not res: res = "Success"
    if not tempCheckPointRes:
        return tempCheckPointRes, "Success"
    else:
        return tempCheckPointRes, "Fail"

def applyVariables(filteredSot, fNm, fextracted_content,varFile):
    for layer in varFile:
        if layer['LayerName']=="Checkpoints" and layer['ProcessStage']==0:
            resVal, status = applyCheckpoints(filteredSot, fNm, fextracted_content, layer['Transformation'])
    return resVal, status

def runCheckpoints(filteredSot, extracted_content, docTypeAndYear):

    for fNm, fextracted_contentDic in extracted_content.items():
        template_name = docTypeAndYear[0]
        if constants.templateDrivers.get(template_name):
            varFile = constants.templateDrivers[template_name].get('var')

        varFile = constants.configPath + varFile +'.json'
        varFile = utils.readFile(varFile, type='json')

        if varFile:
            res, status = applyVariables(filteredSot, fNm, fextracted_contentDic, varFile)

    return res, status


def pdftoImgForlocatedPage(located_page):
    for fNm, pageMap in located_page.items():
        for pageid, pageDetail in pageMap.items():
            if pageDetail['mapTo'] is not None:
                pdfToImg(fNm, pageDetail['mapTo'][0], pageDetail['mapTo'][-1])

def extractDiElmFromLocPage(diOut, located_page, selkey='imgTxtLn2', text=False, sort=True, textFontSize=False):
    pages = []
    for fNm, pageMap in located_page.items():
        for pageid, pageDetail in pageMap.items():
            if pageDetail['mapTo'] is not None: pages.extend(pageDetail['mapTo'])
    pages = list(set(pages))
    diTagsForSelKey = parseMultiple(diOut, pages=pages, selKey=selkey, text=text, sort=sort, textFontSize=textFontSize)
    return diTagsForSelKey


def validatePdfWrapper(token, listofFiles):
    validationResult = []
    with open('../tmp/' + token + 'SOT.pkl', 'rb') as fp:
    #with open('E:/QC_input/MBG_2018.pkl','rb') as fp:
        sot = pickle.load(fp)
    for idx, fNm in enumerate(listofFiles):
        filteredSot = {}
        eachFileRes = {'filename': fNm, 'SNo':idx+1}
        filteredSot['excelData'] = filterByGroupNum(sot['excelData'], fNm)
        sheetName = 'Employer Group_MBG'
        productCombination = filteredSot['excelData'][sheetName]['Product Combination (MA Only, MA-PD, MA-RDS or PDP)'][0]
        st = {'MA Only': 'EOC_MA', 'MAPD':'EOC_MA'}
        filteredSot['year'] = sot['year']
        filteredSot['docType'] = st[productCombination]
        if constants.createState:validatePdf([fNm], filteredSot); continue
        eachFileRes['comments'], eachFileRes['status'] = validatePdf([fNm], filteredSot)
        validationResult.append(eachFileRes)
    return validationResult


def validatePdf(listOfFileName, filteredSot):
    """
    :param listOfFileName: List of fileName with .pdf extension
    :return: json object with the validation result
    """

    # remove .pdf extension from the list of filename
    lstFiles = [i.split('.pdf')[0] for i in listOfFileName]

    # convert all input files to xml
    if constants.createState:
        diOut = convertMultiple(lstFiles)
        with open(constants.pklPathDiOut+"_"+lstFiles[0]+".pkl", 'wb') as handle:
            pickle.dump(diOut, handle, protocol=pickle.HIGHEST_PROTOCOL)
        diTagsText_Font = parseMultiple(diOut, selKey='textline', text=True, sort=True,textFontSize=True)  # {'f1':{1:[((ulx,uly,lrx,lry):rect),((1,2,3,4):rect)]}}
        with open(constants.pklPathDiTagsText_Font+"_"+lstFiles[0]+".pkl", 'wb') as handle:
           pickle.dump(diTagsText_Font, handle, protocol=pickle.HIGHEST_PROTOCOL)

        pagesInFile = len(diTagsText_Font[lstFiles[0]].keys())

        located_page = pageLocatorWrapper(diTagsText_Font, constants.pageLocator,
                                          [filteredSot['docType'], filteredSot['year']])
        pdftoImgForlocatedPage(located_page)
        diTagsFigs = extractDiElmFromLocPage(diOut, located_page, selkey='fig', text=False, sort=True, textFontSize=False)
        with open(constants.pklPathDiTagsFigs+"_"+lstFiles[0]+".pkl", 'wb') as handle:
            pickle.dump(diTagsFigs, handle, protocol=pickle.HIGHEST_PROTOCOL)
        # diTagsFigAndTextWithFont = extractDiElmFromLocPage(diOut, located_page, selkey='imgTxtLn2', text=True, sort=True, textFontSize=True)
        # with open(constants.pklPathDiTagsFigAndTextWithFont, 'wb') as handle:
        #    pickle.dump(diTagsFigAndTextWithFont, handle, protocol=pickle.HIGHEST_PROTOCOL)

        return

    elif constants.useState:

        with open(constants.pklPathDiOut+"_"+lstFiles[0]+".pkl", 'rb') as handle:
           diOut = pickle.load(handle)

        # extracting text from all files
        with open(constants.pklPathDiTagsText_Font+"_"+lstFiles[0]+".pkl", 'rb') as handle:
            diTagsText_Font = pickle.load(handle)

        pagesInFile = len(diTagsText_Font[lstFiles[0]].keys())

        located_page = pageLocatorWrapper(diTagsText_Font, constants.pageLocator,
                                          [filteredSot['docType'], filteredSot['year']])
        with open(constants.pklPathDiTagsFigs+"_"+lstFiles[0]+".pkl", 'rb') as handle:
            diTagsFigs = pickle.load(handle)
        # with open(constants.pklPathDiTagsFigAndTextWithFont, 'rb') as handle:
        #   diTagsFigAndTextWithFont = pickle.load(handle)
    else:
        diOut = convertMultiple(lstFiles)
        diTagsText_Font = parseMultiple(diOut, selKey='textline', text=True, sort=True,
                                        textFontSize=True)  # {'f1':{1:[((ulx,uly,lrx,lry):rect),((1,2,3,4):rect)]}}
        pagesInFile = len(diTagsText_Font[lstFiles[0]].keys())

        located_page = pageLocatorWrapper(diTagsText_Font, constants.pageLocator,
                                          [filteredSot['docType'], filteredSot['year']])
        pdftoImgForlocatedPage(located_page)
        diTagsFigs = extractDiElmFromLocPage(diOut, located_page, selkey='fig', text=False, sort=True,
                                             textFontSize=False)
        diTagsFigAndTextWithFont = extractDiElmFromLocPage(diOut, located_page, selkey='imgTxtLn2', text=True,
                                                           sort=True, textFontSize=True)

    print(located_page)



    # extracting all the fig and textline in sorted order




    # passing pageLocated to contentLocator
    extracted_content = contentExtractorWrapper(diOut, pagesInFile, diTagsText_Font, diTagsFigs, located_page, constants.contentLocator, [filteredSot['docType'], filteredSot['year']])
    print(extracted_content)

    validation_result, status = runCheckpoints(filteredSot, extracted_content, [filteredSot['docType'], filteredSot['year']])
    return validation_result, status

def getGroupNumber(pdfFileName):
    # getting the group number from PDF filename
    # UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059 --> group number = 16174
    return pdfFileName.split('_')[2]

def filterByGroupNum(mbg, pdfFileName):
    # filtering mbg dict by group number
    groupNumber = getGroupNumber(pdfFileName)
    filteredDic = {}
    for sheet, df in mbg.items():
        filteredDic[sheet] = df.loc[df['Group Number'] == groupNumber].reset_index(drop="True")
    return filteredDic


# convert outputdata to Excel file
def exportReviewedData(reviewdJson,token, keys):
    #print(reviewdJson)
    outputFiles = []
    df = pd.DataFrame(reviewdJson, columns=keys)
    cols_for_wrap = ['comments']
    outputFile = "Output_" + token  # Todo: manage multiple users for same file
    xlsxWriter = pd.ExcelWriter('../UI/static/output/' + outputFile + '.xlsx', engine='xlsxwriter')
    df.to_excel(xlsxWriter, sheet_name='Sheet1', index=False)
    workbook = xlsxWriter.book
    worksheet = xlsxWriter.sheets['Sheet1']
    wrap_format = workbook.add_format({'text_wrap': True})
    wrap_format.set_align('vjustify')
    # dictionary to map column number to alphabet order use by excel
    d = dict(zip(range(26), list(string.ascii_uppercase)))
    for col in df.columns.get_indexer(cols_for_wrap):
        excel_header = d[col] + ':' + d[col]
        worksheet.set_column(excel_header, 60, wrap_format)
    filename_col = df.columns.get_indexer(['filename'])[0]
    excel_header = d[filename_col] + ':' + d[filename_col]
    worksheet.set_column(excel_header, 65)
    xlsxWriter.save()
    return outputFile

if __name__=='__main__':
    files = ['UHEX18PP4071919_003_13521_GRP_EOC_28062018_160123']
    # files = ['UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059']
    validatePdf(files, filteredSot)
    # files = [os.path.splitext(os.path.basename(path))[0] for path in glob.glob('{0}*.pdf'.format(constants.inpPath))]
    jsn=main(files)
    #print(json.dumps(jsn))