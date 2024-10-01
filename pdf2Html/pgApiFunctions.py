from bin import constants
import requests
import lxml.html
import copy
import math
import pickle
import re
import numpy as np
from sklearn.cluster import KMeans
import traceback
from bin import pdfExtractionUtils as pdfUtil
from pdf2Html import constants as const
def assignTextlinesNonTable(lstTags,pg):
    xml=assingTags(lstTags)
    textLines=wordAndTextline(xml,pg)
    textLines = [(lnTup[0], lnTup[1], pg) for lnTup in textLines]
    textLinesNonTbl=(pg,textLines)
    return textLinesNonTbl

def isSensitivity(lastLine):
    txt=''.join([chrTup[0] for lsTup in lastLine[1] for wrdTup in lsTup[0] for chrTup in
             wrdTup]).strip()
    if txt=='Sensitivity: Internal & Restricted':
        return True

def removeHeadAndFoot(diNonTblTxtLn,header=None,footer=None):
    diNonTblTxtLnCopy=copy.deepcopy(diNonTblTxtLn)
    for pgIx,pg in enumerate(diNonTblTxtLn):

        if header:
            lst=list(diNonTblTxtLnCopy[pgIx][1][0])
            lst[1]=diNonTblTxtLnCopy[pgIx][1][0][1][header:]
            diNonTblTxtLnCopy[pgIx][1][0]=tuple(lst)

        if footer:
            newFooter=footer
            if diNonTblTxtLnCopy[pgIx][1][-1][1]:
                if isSensitivity(diNonTblTxtLnCopy[pgIx][1][-1][1][-1]):
                    newFooter+=1
            lst=list(diNonTblTxtLnCopy[pgIx][1][-1])
            lst[1]=diNonTblTxtLnCopy[pgIx][1][-1][1][0:-newFooter]
            diNonTblTxtLnCopy[pgIx][1][-1]=tuple(lst)
    return diNonTblTxtLnCopy

def mergeTblAndNonTblTxtLn(lstTblTxtLn, lstNonTblTxtLn):
    if constants.pgApi:
        txtLn=[(pgTxtLnTup[0][0],sorted(pgTxtLnTup[0][1]+pgTxtLnTup[1][1],key=lambda tup:tup[0][3],reverse=True))  for pgTxtLnTup in list(zip(lstTblTxtLn, lstNonTblTxtLn))]
    else:
        txtLn = [(pg + 1, sorted(pgTxtLnTup[0][1] + pgTxtLnTup[1][1], key=lambda tup: tup[0][3], reverse=True)) for pg, pgTxtLnTup in enumerate(list(zip(lstTblTxtLn, lstNonTblTxtLn)))]
    return txtLn

def getModeVal(lstValues):
    if not lstValues:
        return 0
    di={}
    for val in lstValues:
        if val not in di:
            di.setdefault(val,[]).append(val)
        else:
            di[val].append(val)
    di={k:len(v) for k,v in di.items()}
    return sorted(list(di.items()),key=lambda tup:tup[1],reverse=True)[0][0]

def numOfClusters(lstDiff):
    return 2

def getClusters(lstDiff,clustCutoff):
    if np.std(lstDiff)<clustCutoff:
        return max(lstDiff)+0.1
    nClust=numOfClusters(lstDiff)
    lstDiffNew = lstDiff + lstDiff[-1:] * (nClust - len(lstDiff))
    kmeans = KMeans(n_clusters=nClust)
    kmeans.fit(np.array(lstDiffNew).reshape(-1, 1))
    diMean={}
    for tup in zip(lstDiff,kmeans.labels_):
        diMean.setdefault(tup[1],[]).append(tup[0])
    diMean1={k:min(lst) for k,lst in diMean.items()}
    lstMean=sorted(list(diMean1.items()),key=lambda tup:tup[1],reverse=True)
    try:
        if len(lstMean)>1:
            cutoff=lstMean[:-1][-1][1]
        else:
            cutoff = lstMean[-1][1]
        return cutoff
    except:
        traceback.print_exc()
        print(lstMean)

def wordAndTextline(xml,pg,ixCol=None):
    def assignGroup(cutOff,lst,ixTup1,ixTup2,ixPrev,ixNxt,isClust=False):
        lstGrpBrk = []
        for ix, tups in enumerate(zip(lst[0:-1], lst[1:])):
            tup1, tup2 = tups[ixTup1], tups[ixTup2]
            if isClust:
                if tup2[0][ixPrev]-tup1[0][ixNxt]>=cutOff:#to be used in case of getClusters
                    lstGrpBrk.append(ix + 1)
            else:
                if math.floor(tup2[0][ixPrev]-tup1[0][ixNxt]) > cutOff:
                    lstGrpBrk.append(ix + 1)

        extLstGrpBrk = [0] + lstGrpBrk + [len(lst)]

        lstGrpTuples = []
        for st, end in zip(extLstGrpBrk[0:-1], extLstGrpBrk[1:]):
            lstGrpTuples.append(lst[st:end])
        return lstGrpTuples

    def getWords(lstTup):
        tmp=[tup for tup in lstTup if tup[1][3] is not None if tup[1][3].strip()]
        if not tmp:
            return []
        # modeSpace=statistics.mode([tup2[0][0]-tup1[0][2] for tup1,tup2 in zip(tmp[0:-1],tmp[1:])])
        lstSpace=[max(0,tup2[0][0]-tup1[0][2]) for tup1,tup2 in zip(tmp[0:-1],tmp[1:])]
        modeSpace=getModeVal([math.ceil(elm) for elm in lstSpace])
        # modeSpace=getClusters([elm for elm in lstSpace if elm<10],0.5)
        # lstWrdTuples=assignGroup(modeSpace, tmp, 0, 1, 0, 2,True)
        lstWrdTuples=assignGroup(modeSpace, tmp, 0, 1, 0, 2)

        return lstWrdTuples

    def getNewBbx(lstTup):
        minY,maxY=min([tup[0][1] for tup in lstTup]),max([tup[0][3] for tup in lstTup])
        minX,maxX=min([tup[0][0] for tup in lstTup]),max([tup[0][2] for tup in lstTup])
        newBbx=(minX,minY,maxX,maxY)
        return newBbx

    def determineParagraph(lines):
        lstBbox=[bbx for bbx,ln in lines]
        lstSpace = [max(0, tup1[1] - tup2[3]) for tup1, tup2 in zip(lstBbox[0:-1], lstBbox[1:])]
        minCutOff=2.5
        maxCutOff=12
        # lstSpace=[spc for spc in lstSpace if spc < maxCutOff]
        lstLnTuples=[lines]
        if lstSpace:
            # cutOff=getClusters(lstSpace,minCutOff)
            cutOff=getModeVal([math.ceil(elm) for elm in lstSpace])
            lstLnTuples=assignGroup(cutOff, lines,1,0,1,3)

        linesWithParaId=[]
        for ixPara,lines in enumerate(lstLnTuples):
            for ln in lines:
                linesWithParaId.append(ln+(ixPara,))
        return linesWithParaId
    tree=lxml.html.fromstring(xml)
    diTags=pdfUtil.parseTree(tree, selKey='textPg', tagAttribAndText=True)
    # diTags=parseTree(token,tree=lxml.html.tostring(tree),selKey='textPg',tagAttribAndText=True)
    diTextLine={}
    for bbx,tagTup in diTags:
        tagTup[2]['pg']=pg
        if bbx not in diTextLine:
            brk=False
            for bbx1,lstTags in diTextLine.items():
                if determineOverlap(bbx,bbx1):
                    diTextLine.setdefault(bbx1,[]).append((bbx,tagTup))
                    brk=True
                    break
            if brk:
                continue
            diTextLine.setdefault(bbx,[]).append((bbx,tagTup))


    diTextLineSrt={}
    for bbx,lstTup in diTextLine.items():
        newBbx=getNewBbx(lstTup)
        diTextLineSrt[newBbx]=sorted(lstTup,key=lambda tup:tup[0])
    diWords={}
    textLines=list(diTextLineSrt.items())
    textLines=determineParagraph(textLines)
    for ixLn,lnTup in enumerate(textLines):
        bbx, lstTup,ixPara=lnTup[0],lnTup[1],lnTup[2]
        try:
            wrds=getWords(lstTup)
        except:
            print('')
        lstWrds=[]
        for ixWrd,wrd in enumerate(wrds):
            newBbx = getNewBbx(wrd)
            text=[(tup[1][3],tup[1][2],(ixLn,ixWrd,ixChr,ixCol,ixPara)) for ixChr,tup in enumerate(wrd)]
            if text:

                if lstWrds:
                    xLft=lstWrds[-1][0][2]
                    xRht=newBbx[0]
                    blnkBbx=list(newBbx)
                    blnkBbx[0],blnkBbx[2]=xLft,xRht
                    blnkBbxStr=','.join(map(str,blnkBbx))
                    tmp = copy.deepcopy(list(lstWrds[-1][1][-1]))
                    tmp[0] = ' '
                    tmp[1]['bbox'] = blnkBbxStr
                    lstWrds[-1][1].append(tuple(tmp))

            fontInfo=(wrd[0][1][2]['font'],wrd[0][1][2]['size'])
            lstWrds.append((newBbx,text,fontInfo))
        if lstWrds:
            if lstWrds[-1]:
                lstWrds[-1]=(lstWrds[-1][0],lstWrds[-1][1]+[(' ',lstWrds[-1][1][-1][1],lstWrds[-1][1][-1][2])],lstWrds[-1][2])
        diWords[bbx]=lstWrds
    diSubLines = {}
    for bbx,lstWrds in diWords.items():
        tmpList=[]
        prevWrd = None
        for wrd in lstWrds:
            if not tmpList:
                tmpList.append(wrd)
                prevWrd=wrd
                continue
            if prevWrd[2]==wrd[2]:
                prevWrd = wrd
                tmpList.append(wrd)
            else:
                text=[tup[1] for tup in tmpList]
                fontInfo=prevWrd[2]
                diSubLines.setdefault(bbx,[]).append([text,fontInfo])
                tmpList=[wrd]
                prevWrd=wrd
        if tmpList:
            text = [tup[1] for tup in tmpList]
            fontInfo = prevWrd[2]
            diSubLines.setdefault(bbx, []).append([text, fontInfo])

    textLines=sorted(list(diSubLines.items()),key=lambda tup:tup[0][1],reverse=True)
    textLines=removeUnwantedEOLSpace(textLines)
    return textLines
def removeUnwantedEOLSpace(textLines):
    for ix,ln in enumerate(copy.deepcopy(textLines)):
        if ln and ln[1]:
            if ix==0:
                if ln[1][-1][0][-1][-2][0]=='-':
                    textLines[ix][1][-1][0][-1]=textLines[ix][1][-1][0][-1][:-1]
                continue
            else:
                if ln[1][-1][0][-1][-2][0] == '-':
                    textLines[ix][1][-1][0][-1] = textLines[ix][1][-1][0][-1][:-1]
                if ln[1][0][0][0][0][0] == '-' and textLines[ix-1][1][-1][0][-1][-1][0]==' ':
                    textLines[ix-1][1][-1][0][-1] = textLines[ix-1][1][-1][0][-1][:-1]
    return textLines

def getNonTableRegions(diTbl,numPages,pgNum):
    tmp = {pg: sorted([tbl[3] for tbl in tblTuple],key=lambda tup:tup[1])for pg, tblTuple in diTbl.items()}

    nonTableRegions={}
    for pg,lstTblRgn in tmp.items():
        lstNonTblRgn=[]
        minY=0
        for tblRgn in lstTblRgn:
            if not lstNonTblRgn:
                lstNonTblRgn.append((0,max(0,minY-1),612,min(792,tblRgn[1]+1)))
                minY=tblRgn[3]
                continue
            lstNonTblRgn.append((0, max(0,minY-1), 612, min(792,tblRgn[1]+1)))
            minY = tblRgn[3]
        lstNonTblRgn.append((0, max(0,minY-1), 612, 792))
        nonTableRegions[pg]=lstNonTblRgn
    if pgNum==None:
        nonTableRegions.update({pg:[(0, 0, 612, 792)] for pg in range(1,numPages+1) if pg not in diTbl.keys()})
    else:
        if pgNum not in diTbl.keys():
            nonTableRegions.update({pgNum: [(0, 0, 612, 792)]})
    return nonTableRegions

def parseMultipleApi(token,**kwargs):
    params = {"token": token, "pklDir": constants.pklDir}
    data=pickle.load(open(constants.pklDir + token + '.pkl', 'rb'))
    data['funcInp']=kwargs
    pickle.dump(data,open(constants.pklDir + token + '.pkl', 'wb'))
    # prt = constants.tblExtApiPorts[int(data['pg']) % len(constants.tblExtApiPorts)]
    # res = requests.get(constants.parseXmlMultApi.format(prt), params=params)
    res = requests.get(constants.parseXmlMultApi, params=params)
    data = pickle.load(open(constants.pklDir + token + '.pkl', 'rb'))
    diTags = {}
    for fNm, diPg in data['diTags'].items():
        for pgNm, lstTags in diPg.items():
            for tgTup in lstTags:
                bbx = tgTup[0]
                tgInfo = tgTup[1]
                tgTyp, tgObjStr = tgInfo[0], tgInfo[1]
                tgObj = lxml.html.fromstring(tgObjStr)
                diTags.setdefault(fNm, {}).setdefault(pgNm, []).append((bbx, (tgTyp, tgObj)))
    return diTags

def assingTags(pgTags):
    lstTags=[]
    for tgTup in sorted(pgTags,key=lambda tup:(-tup[0][1],tup[0][0])):
        bbx=tgTup[0]
        tg=tgTup[1]
        lstTags.append(tg[1])
    if const.usePgApi:
        assigned=b''.join([tg for tg in lstTags])
    else:
        assigned=b''.join([lxml.html.tostring(tg) for tg in lstTags])
    return assigned


def determineOverlap(bbx1,bbx2):
    if (bbx1[1] <= bbx2[1] < bbx2[3] <= bbx1[3] or bbx2[1] <= bbx1[1] < bbx1[3] <=bbx2[3]) \
            or (bbx1[1] <= bbx2[3] <= bbx1[3] and not (bbx1[1] <= bbx2[1] <= bbx1[3]) and (((bbx2[3] - bbx1[1]) / (bbx1[3] - bbx1[1])) > 0.5 or ((bbx2[3] - bbx1[1]) / (bbx2[3] - bbx2[1])) > 0.5)) \
            or (bbx1[1] <= bbx2[1] <= bbx1[3] and not (bbx1[1] <= bbx2[3] <= bbx1[3]) and (((bbx1[3] - bbx2[1]) / (bbx1[3] - bbx1[1])) > 0.5 or ((bbx1[3] - bbx2[1]) / (bbx2[3] - bbx2[1])) > 0.5)):
        return True
    return False



def getDiTags(pgXml,params):
    fNm = params.get('tkn')
    pg= params.get('pg')
    bounds=params.get('bounds')
    xmlParseInp = params.get('xmlParseInp')
    diOut = pdfUtil.convertMultipleNew([(fNm, pgXml)])
    diTags = parseXmlMultApi(diOut, xmlParseInp)
    return {"data": {"diTags": diTags},"pg":pg,"fNm":fNm,"bounds":bounds}



def parseXmlMultApi(diOut,funcInp):
    diTags = pdfUtil.parseMultiple(diOut, selKey=funcInp['selKey'], text=funcInp['text'])
    diTagsNew = {}
    for fNm, diPg in diTags.items():
        for pgNm, lstTags in diPg.items():
            for tgTup in lstTags:
                bbx = tgTup[0]
                tgInfo = tgTup[1]
                tgTyp, tgObj = tgInfo[0], tgInfo[1]
                tgObjStr = lxml.html.tostring(tgObj)
                diTagsNew.setdefault(fNm, {}).setdefault(pgNm, []).append((bbx, (tgTyp, tgObjStr)))
    return diTagsNew

