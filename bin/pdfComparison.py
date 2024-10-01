import lxml.html
import math
import re
import copy
import pickle
import traceback
from bin import extractTableWrapper as tblWrap
from bin import pdfComparisonRuleFuncs as funcs
from bin import pdfExtractionUtils as pdfutil
from bin import utils

def determineOverlap(bbx1,bbx2):
    if (bbx1[1] <= bbx2[1] < bbx2[3] <= bbx1[3] or bbx2[1] <= bbx1[1] < bbx1[3] <=bbx2[3]) \
            or (bbx1[1] <= bbx2[3] <= bbx1[3] and not (bbx1[1] <= bbx2[1] <= bbx1[3]) and (((bbx2[3] - bbx1[1]) / (bbx1[3] - bbx1[1])) > 0.5 or ((bbx2[3] - bbx1[1]) / (bbx2[3] - bbx2[1])) > 0.5)) \
            or (bbx1[1] <= bbx2[1] <= bbx1[3] and not (bbx1[1] <= bbx2[3] <= bbx1[3]) and (((bbx1[3] - bbx2[1]) / (bbx1[3] - bbx1[1])) > 0.5 or ((bbx1[3] - bbx2[1]) / (bbx2[3] - bbx2[1])) > 0.5)):
        return True
    return False
def wordAndTextline(xml):

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


    def getWords(lstTup):
        tmp=[tup for tup in lstTup if tup[1][3].strip()]
        if not tmp:
            return []
        # modeSpace=statistics.mode([tup2[0][0]-tup1[0][2] for tup1,tup2 in zip(tmp[0:-1],tmp[1:])])
        modeSpace=getModeVal([max(0,tup2[0][0]-tup1[0][2]) for tup1,tup2 in zip(tmp[0:-1],tmp[1:])])
        lstWrdBrk=[]
        for ix,tups in enumerate(zip(tmp[0:-1],tmp[1:])):
            tup1,tup2=tups[0],tups[1]
            tup1FontInfo=(tup1[1][2]['font'],tup1[1][2]['size'])
            tup2FontInfo=(tup2[1][2]['font'],tup2[1][2]['size'])
            if math.floor(tup2[0][0]-tup1[0][2])>modeSpace or tup1FontInfo!=tup2FontInfo:
                lstWrdBrk.append(ix+1)
        extLstWrdBrk=[0]+lstWrdBrk+[len(tmp)]

        lstWrdTuples=[]
        for st,end in zip(extLstWrdBrk[0:-1],extLstWrdBrk[1:]):
            lstWrdTuples.append(tmp[st:end])

        return lstWrdTuples

    def getNewBbx(lstTup):
        minY,maxY=min([tup[0][1] for tup in lstTup]),max([tup[0][3] for tup in lstTup])
        minX,maxX=min([tup[0][0] for tup in lstTup]),max([tup[0][2] for tup in lstTup])
        newBbx=(minX,minY,maxX,maxY)
        return newBbx

    tree=lxml.html.fromstring(xml)

    diTags=pdfutil.parseTree(tree, selKey='textPg',tagAttribAndText=True)
    diTextLine={}
    for bbx,tagTup in diTags:
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
    for bbx,lstTup in diTextLineSrt.items():
        wrds=getWords(lstTup)
        lstWrds=[]
        for wrd in wrds:
            newBbx = getNewBbx(wrd)
            text=''.join([tup[1][3] for tup in wrd])
            fontInfo=(wrd[0][1][2]['font'],wrd[0][1][2]['size'])
            lstWrds.append((newBbx,text,fontInfo))
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
                text=' '.join([tup[1] for tup in tmpList])
                fontInfo=prevWrd[2]
                diSubLines.setdefault(bbx,[]).append([text,fontInfo])
                tmpList=[wrd]
                prevWrd=wrd
        if tmpList:
            text = ' '.join([tup[1] for tup in tmpList])
            fontInfo = prevWrd[2]
            diSubLines.setdefault(bbx, []).append([text, fontInfo])

    return sorted(list(diSubLines.items()),key=lambda tup:tup[0][1],reverse=True)



def assignTextlinesTable(diTbl,numPages):
    lstPgs=[]
    placeHolder=[(k,[]) for k in range(1,numPages+1) if k not in diTbl.keys()]
    for pg,tupTbl in sorted(diTbl.items(),key=lambda tup:tup[0]):
        lstTbls=[]
        for tbl in tupTbl:
            htmlString=tbl[0]
            tblBbx=tbl[3]
            tree=lxml.html.fromstring(htmlString)
            rows=tree.xpath('.//tr')
            lstRows=[]
            for row in rows[1:]:
                cols=row.xpath('.//td')
                lstCols=[]
                for col in cols:
                    textTagStr=[lxml.html.tostring(tmp) for tmp in col.xpath('.//text')]
                    if not textTagStr:
                        lstCols.append([])
                        continue
                    xml=(b'<pages><page id="1" bbox="0,0,0,0"><textline>'+b''.join(textTagStr)+b'</textline></page></pages>').decode('utf-8')
                    textLines=wordAndTextline(xml)
                    lstCols.append(textLines)
                lstRows.append(lstCols)
            lstTbls.append((tblBbx,lstRows,'tbl'))
        lstPgs.append((pg,lstTbls))
    lstPgs=sorted(lstPgs+placeHolder,key=lambda tup:tup[0])
    return lstPgs


def getNonTableRegions(diTbl,numPages):
    tmp = {pg: [tbl[3] for tbl in tblTuple] for pg, tblTuple in diTbl.items()}

    nonTableRegions={}
    for pg,lstTblRgn in tmp.items():
        lstNonTblRgn=[]
        minY=0
        for tblRgn in lstTblRgn:
            if not lstNonTblRgn:
                lstNonTblRgn.append((0,minY,612,tblRgn[1]))
                minY=tblRgn[3]
                continue
            lstNonTblRgn.append((0, minY, 612, tblRgn[1]))
        lstNonTblRgn.append((0, minY, 612, 792))
        nonTableRegions[pg]=lstNonTblRgn
    nonTableRegions.update({pg:[(0, 0, 612, 792)] for pg in range(1,numPages+1) if pg not in diTbl.keys()})
    return nonTableRegions


def assingTags(region,pgTags):
    lstTags=[]
    for tgTup in sorted(pgTags,key=lambda tup:(-tup[0][1],tup[0][0])):
        bbx=tgTup[0]
        tg=tgTup[1]
        if region[0]<=bbx[0]<bbx[2]<=region[2] and region[1]<=bbx[1]<bbx[3]<=region[3]:
            lstTags.append(tg[1])
    return b''.join([lxml.html.tostring(tg) for tg in lstTags])
def assignTextlinesNonTable(diTbl,diOut,fNm,numPages):
    nonTblRegions = getNonTableRegions(diTbl,numPages)
    diTags = pdfutil.parseMultiple(diOut, selKey='tagsWithNoChildren', text=False)

    textLinesNonTbl=[]
    for pg,lstRegions in sorted(nonTblRegions.items(),key=lambda tup:tup[0]):
        pgTags=diTags[fNm][pg]
        wordAndTextlinePerRgn=[]
        for region in lstRegions:
            textLines=[]
            xml=assingTags(region, pgTags)
            xml1 = (b'<pages><page id="1" bbox="0,0,0,0"><textline>' +xml+ b'</textline></page></pages>').decode('utf-8')
            if xml:
                textLines=wordAndTextline(xml1)
            wordAndTextlinePerRgn.append((region,textLines,'nontbl'))
        textLinesNonTbl.append((pg,sorted(wordAndTextlinePerRgn,key=lambda tup:tup[0][3],reverse=True)))
    return textLinesNonTbl

def mergeTblAndNonTblTxtLn(lstTblTxtLn, lstNonTblTxtLn):
    txtLn=[(pg+1,sorted(pgTxtLnTup[0][1]+pgTxtLnTup[1][1],key=lambda tup:tup[0][3],reverse=True) ) for pg,pgTxtLnTup in enumerate(list(zip(lstTblTxtLn, lstNonTblTxtLn)))]
    return txtLn

def removeHeadAndFoot(diNonTblTxtLn,header=None,footer=None):
    diNonTblTxtLnCopy=copy.deepcopy(diNonTblTxtLn)
    for pgIx,pg in enumerate(diNonTblTxtLn):

        if header:
            lst=list(diNonTblTxtLnCopy[pgIx][1][0])
            lst[1]=diNonTblTxtLnCopy[pgIx][1][0][1][header:]
            diNonTblTxtLnCopy[pgIx][1][0]=tuple(lst)

        if footer:
            lst=list(diNonTblTxtLnCopy[pgIx][1][-1])
            lst[1]=diNonTblTxtLnCopy[pgIx][1][-1][1][0:-footer]
            diNonTblTxtLnCopy[pgIx][1][-1]=tuple(lst)
    return diNonTblTxtLnCopy


def getTblHeaderLen(txtLnNew,rgnData):
    prev = [' '.join([rowSgmt[0] for col in row if col for row1 in col for rowSgmt in row1[1]]) for row in txtLnNew[-1][0]]
    now = [' '.join([rowSgmt[0] for col in row if col for row1 in col for rowSgmt in row1[1]]) for row in rgnData]
    for ix, bool in enumerate([lnPrev == lnNow for lnPrev, lnNow in list(zip(prev, now))]):
        if bool == False:
            return ix

def isSameLine(prevTbl,currentTbl):
    prevTblLstLn=prevTbl[-1]
    currentTblFrstLn=currentTbl[0]
    if not (isHeadingTbl(currentTblFrstLn,1) or isHeadingTbl(currentTblFrstLn,2)):
        if len(prevTblLstLn)==len(currentTblFrstLn):
            joinedLine=[tup[0]+tup[1] for tup in zip(prevTblLstLn,currentTblFrstLn)]
            newTbl=prevTbl[0:-1]+[joinedLine]+currentTbl[1:]
            return newTbl
    return prevTbl+currentTbl



def combinePages(txtLn):
    txtLnNew=[]
    prevRgnTyp=None
    for pg,pgData in txtLn:
        for rgn in pgData:
            rgnBbx, rgnData, rgnTyp=rgn
            if rgnTyp==prevRgnTyp:
                if rgnData:
                    if rgnTyp=='nontbl':
                        txtLnNew[-1][0]=txtLnNew[-1][0]+rgnData

                    elif rgnTyp=='tbl':
                        tblHeaderLen=getTblHeaderLen(txtLnNew,rgnData)
                        if tblHeaderLen==0:
                            txtLnNew.append([rgnData, rgnTyp])
                        else:
                            txtLnNew[-1][0] = isSameLine(txtLnNew[-1][0],rgnData[tblHeaderLen:])
                    prevRgnTyp = rgnTyp
            else:
                if rgnData:
                    prevRgnTyp = rgnTyp
                    txtLnNew.append([rgnData,rgnTyp])
    return txtLnNew



def isHeadingTbl(row,typ):
    tmp=[all([re.search(r'\-bold',lnSgmt[1][0],re.I) and float(lnSgmt[1][1])>11 for lnSgmt in line[1]]) for col in row for line in col]
    if typ==1:
        if tmp:
            return all(tmp)
    elif typ==2:
        if tmp:
            return tmp[0]
    return False



def associateHeader(newTxtLn):
    headingsData=[]
    for rgn,rgnTyp in newTxtLn:
        if rgnTyp=='nontbl':
            heading='None'
            txt=False
            lstTxtLn=[]
            for txtLn in rgn:
                lnText=' '.join([lnSgmt[0] for lnSgmt in txtLn[1]])
                isHeading=len(txtLn[1])==1 and re.search(r'\-bold',txtLn[1][0][1][0],re.I) and float(txtLn[1][0][1][1])>14
                if isHeading:
                    if txt:
                        headingsData.append((heading,' '.join(lstTxtLn)))
                        lstTxtLn= []
                        txt=False
                    heading=lnText
                else:
                    txt=True
                    lstTxtLn.append(lnText)
            headingsData.append((heading, ' '.join(lstTxtLn)))
        elif rgnTyp == 'tbl':
            lstTxtLn = []
            heading = 'None'
            txt = False
            for row in rgn:
                rowText = [[lnSgmt[0] for row1 in col for lnSgmt in row1[1]] for col in row ]
                # isHeading1=all([len(row1[1]) == 1 and re.search(r'bold$|boldoblique$', row1[1][0][1][0], re.I) and float(row1[1][0][1][1]) > 11  for col in row for row1 in col])
                # isHeading2=[len(row1[1]) == 1 and re.search(r'bold$|boldoblique$', row1[1][0][1][0], re.I) and float(row1[1][0][1][1]) > 11  for col in row for row1 in col][0]
                isHeading1=isHeadingTbl(row,1)
                isHeading2=isHeadingTbl(row,2)
                if isHeading1:
                    if txt or lstTxtLn:
                        headingsData.append((heading,lstTxtLn))
                        txt=False
                        lstTxtLn= []
                    heading=' '.join([row1 for col in rowText for row1 in col])
                    # print(heading)
                # elif isHeading2:
                #     if txt or lstTxtLn:
                #         headingsData.append((heading, lstTxtLn))
                #         txt=False
                #         lstTxtLn = []
                #     heading = rowText[0][0]
                #     lstTxtLn.append([' '.join(rowText[0][1:])]+[' '.join([lnSgmt[0] for row1 in col for lnSgmt in row1[1]]) for col in row[1:] ])
                else:
                    txt=True
                    lstTxtLn.append([' '.join(col) for col in rowText])
            headingsData.append((heading,lstTxtLn))
    return headingsData

def main(fNm):

    # diOut = pdfutil.convertMultiple([fNm])
    # pickle.dump(diOut,open('../tmp/diOut_{}.pkl'.format(fNm),'wb'))
    diOut=pickle.load(open('../tmp/diOut_{}.pkl'.format(fNm), 'rb'))
    numPages = len(lxml.html.fromstring(diOut[fNm]).xpath('//page'))
    # diTbl=tblWrap.findAllTables(fNm, diOut=diOut)
    # pickle.dump(diTbl,open('../tmp/diTbl_{}.pkl'.format(fNm),'wb'))
    diTbl=pickle.load(open('../tmp/diTbl_{}.pkl'.format(fNm), 'rb'))
    # exit(0)
    diTblTxtLn = assignTextlinesTable(diTbl, numPages)
    diNonTblTxtLn = assignTextlinesNonTable(diTbl,diOut, fNm, numPages)
    diNonTblTxtLn = removeHeadAndFoot(diNonTblTxtLn, footer=1)
    txtLn = mergeTblAndNonTblTxtLn(diTblTxtLn, diNonTblTxtLn)

    newTxtLn = combinePages(copy.deepcopy(txtLn))
    headingsData = associateHeader(newTxtLn)
    return headingsData

def applyRules(headingsData):
    dataDiNew={}
    ruleLayrPath='../config/variables_pdfComparison.json'
    ruleLayr=utils.readFile(ruleLayrPath,'json')
    for k,v in headingsData:
        if isinstance(v,list):
            vTextBlob=(' '.join([' '.join(elm) if isinstance(elm, list) else elm for elm in v]))
        else:
            vTextBlob=v

        for layr in ruleLayr:
            for tr in layr['Transformation']:
                funcTyp=tr['type']
                funcNm=tr['name']
                funcInp=tr['input']
                if funcTyp=='both' or funcTyp=='key':
                    k=getattr(funcs,funcNm)(k,funcInp)
        for layr in ruleLayr:
            for tr in layr['Transformation']:
                funcTyp = tr['type']
                funcNm=tr['name']
                funcInp=tr['input']
                if funcTyp=='both' or funcTyp=='value':
                    vTextBlob=getattr(funcs,funcNm)(vTextBlob,funcInp)
        dataDiNew[k]=vTextBlob
    return dataDiNew

def compare(h1Text,h2Text):
    if all([wrd in h2Text.split() for wrd in h1Text.split()]):
        return True
    return False
def comparisonWrapper(fNm1,fNm2):
    # headingsData1=main(fNm1)
    # pickle.dump(headingsData1,open('../tmp/headingsData1.pkl','wb'))
    headingsData1 = pickle.load(open('../tmp/headingsData1.pkl', 'rb'))
    # headingsData2=main(fNm2)
    # pickle.dump(headingsData2, open('../tmp/headingsData2.pkl', 'wb'))
    headingsData2 = pickle.load(open('../tmp/headingsData2.pkl', 'rb'))
    # exit(0)
    dataDi1=applyRules(headingsData1)
    dataDi2=applyRules(headingsData2)
    print(dataDi1)
    print(dataDi2)
    diCompRes={}
    for k,v in dataDi1.items():
        if k not in dataDi2:
            diCompRes[k]='heading not found in ref doc'
        else:
            textBlob1=dataDi1[k]
            textBlob2=dataDi2[k]
            diCompRes[k]=compare(textBlob1,textBlob2)
    return diCompRes

if __name__=='__main__':
    fNm1='DOCUMENT_B_SBN_ISSUANCE'
    # fNm1='DOCUMENT_B_SBN_ISSUANCE'
    fNm2='DOCUMENT_A_FILED_SBN'
    # fNm2='DOCUMENT_B_SBN_ISSUANCE'
    # fNm='DOCUMENT_B_SBN_ISSUANCE-1-7'
        # getTblHeaderLen(tmp1,tmp2)
    diCompRes=comparisonWrapper(fNm1, fNm2)
    print(diCompRes)
    # exit(0)
    # headingsData=main(fNm)
    # for heading,data in headingsData:
    #     print(heading,'-------',data)
