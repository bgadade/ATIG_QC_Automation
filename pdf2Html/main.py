from bin import constants
from bin import convertPdf
from pdf2Html import pgApiFunctions
import os
import requests
import json
import hashlib
import concurrent
import concurrent.futures
import lxml.html
import re
import datetime
import html
from statistics import mean
from pdf2Html import constants as const
def fetchUrl(job):
    res = requests.post(**job)
    return res
def fetchAsync(lstJobs):
    lstRes=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=const.pgApiMaxWorkers) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(fetchUrl, job): job for job in lstJobs}
        for future in concurrent.futures.as_completed(future_to_url):
            lstRes.append(future.result())
    return lstRes

def collectRes(lstRes):
    lstResSrt=sorted([(int(res['pg']), res) for res in lstRes], key=lambda tup: tup[0])
    for pg,res in lstResSrt:
        data = res["data"]
        fNm = res["fNm"]
        bounds=res["bounds"]
        if data['diTags']:
            diTags=data['diTags'][fNm][1]
        else:
            bbx = (0, 0) + bounds
            tgTyp = 'text'
            tgTxt=' '
            tg = '<text font="Calibri" bbox="{}" size="9.960">{}</text>'.format(','.join(map(str, bbx)),tgTxt)
            tgTup = (tgTyp, tg.encode('utf-8'))
            diTags=[(bbx,tgTup)]
        yield (pg,bounds,diTags)

def collectResAsync(lstRes):
    lstResSrt=sorted([(int(res.json()['pg']), res.json()) for res in lstRes], key=lambda tup: tup[0])
    for pg,resJsn in lstResSrt:
        data = resJsn["data"]
        dataLen = resJsn["len"]
        fNm = resJsn["fNm"]
        bounds=eval(resJsn["bounds"])
        if len(data) != dataLen:
            print("*********send and receive bytelen not equal*****")
        evalData=eval(data)
        diTags=evalData['diTags'][fNm][1]
        yield (pg,bounds,diTags)


def splitPdfXmlConv(fNm):
    infilePath = constants.pdfDir + '{}.pdf'.format(fNm)
    gen=convertPdf.convert_pdf_by_page(infilePath)
    return gen

def getPgBound(diOut):
    tree=lxml.html.fromstring(diOut)
    tupBound=tuple(map(float, tree.xpath('string(//page/@bbox)').split(',')))
    return tupBound[2:]

def pageApiWrapper(fNm,token,xmlGen):
    lstJobs = []
    for pg, pgXml in enumerate(xmlGen):
        pg += 1
        tkn = token + '_{}_{}'.format(fNm, pg)
        tupBound = getPgBound(pgXml)
        xmlParseInp = {'selKey': 'tagsWithNoChildren', 'text': False}
        hashVal = hashlib.sha256(tkn.encode('utf-8')).hexdigest()
        print(tkn, '\t', tkn.encode('utf-8'), '\t', hash(tkn), '\t', hashVal)
        params = {'tkn': hashVal, 'fNm': fNm, 'xmlParseInp': xmlParseInp, "pg": pg, "bounds": tupBound}
        lstJobs.append(pgApiFunctions.getDiTags(pgXml,params))
    lstData = collectRes(lstJobs)
    return lstData

def pageApiWrapperAsync(fNm,token,xmlGen):
    lstJobs = []
    for pg,pgXml in enumerate(xmlGen):
        pg+=1
        tkn = token + '_{}_{}'.format(fNm, pg)
        files = {'xmlFile': pgXml}
        tupBound = getPgBound(pgXml)
        xmlParseInp = json.dumps({'selKey': 'tagsWithNoChildren', 'text': False})
        hashVal = hashlib.sha256(tkn.encode('utf-8')).hexdigest()
        print(tkn, '\t', tkn.encode('utf-8'), '\t', hash(tkn), '\t', hashVal)
        params = {'tkn': hashVal, 'fNm': fNm, 'xmlParseInp': xmlParseInp, "pg": pg,"bounds":str(tupBound)}
        lstJobs.append({"url": constants.getDiTagsApi, "files": files, "data": params})
    lstRes = fetchAsync(lstJobs)
    lstData = collectResAsync(lstRes)
    return lstData

def getGraphics(lstTags):
    diGraphics={}
    for elmTup in lstTags:
        tgTup=elmTup[1]
        tgTyp=tgTup[0]
        if tgTyp not in ['rect','line','curve']:
            continue
        diGraphics.setdefault(tgTyp,[]).append(tgTup[1])
    return diGraphics

def getLines(lstData):
    for ix,tupData in enumerate(lstData):
        pg, bounds, lstTags=tupData[0],tupData[1],tupData[2]
        lines=pgApiFunctions.assignTextlinesNonTable(lstTags,pg)
        diGraphics=getGraphics(lstTags)
        yield (bounds,lines,diGraphics)

def getFontProp(fontString):
    # print('****',fontString)
    wht='400'
    style='normal'
    fmly='calibri'
    lst=fontString.split('+')
    if len(lst)>1:
        if len(lst[1].split(','))>1:
            lst1=lst[1].split(',')
            fmly=lst1[0]
        elif len(lst[1].split('-')) > 1:
            lst1 = lst[1].split('-')
            fmly = lst1[0]
        else:
            fmly=lst[1]

    else:
        if len(lst[0].split(',')) > 1:
            lst1 = lst[0].split(',')
            fmly = lst1[0]
        elif len(lst[0].split('-')) > 1:
            lst1 = lst[0].split('-')
            fmly = lst1[0]
        else:
            fmly = lst[0]
    if 'bold' in fontString.lower():
        wht='700'
    elif 'demi' in fontString.lower():
        wht = '600'
    elif 'medium' in fontString.lower():
        wht = '500'
    if 'italic' in fontString.lower():
        style='italic'
    # print('****{}**{}**{}'.format(fmly,wht,style))
    return fmly,wht,style

def addGlobalStyle(htm):
    htm += '''<style class="shared-css" type="text/css" >
        .t {
        	position: absolute;
        	white-space: pre;
        	overflow: visible;
        	text-align-last:justify;
        }
        .g{
            fill:none; 
            stroke:black; 
        }
        .g1{
            shape-rendering:crispEdges;
        }
        </style>
        '''
    return htm
def addIdInfo(htm,idCss):
    htm+='<style type="text/css" >{}</style>\n'.format(idCss)
    return htm

def createTextDiv(tup,txt,htm,scale,ixDiv,width,tupId,spcLen=0,nonSpcLen=None):
    bbx = getBbxTup(tup)
    sizeOrig = float(tup[1]['size'])
    font = tup[1]['font']
    fmly,wht, style = getFontProp(font)
    sizeNew = round((sizeOrig*scale)*const.fontScaler)
    ##print(sizeOrig,',',sizeNew)
    ##print(fmly,',', wht,',', style)
    lft = round(bbx[0] * scale)
    btm = round(bbx[1] * scale)
    width=round(width*scale)
    fmly=const.fixedFontFamily if const.fixedFont else fmly

    divIdVal='font-family:{};font-size: {}pt;font-weight:{};font-style:{};'.format(fmly,sizeNew, wht, style)
    idStr='|'.join(map(str,tupId))
    htm += '<div id="{}" class="{{{}}} t" style="left:{}pt;bottom:{}pt;width:{}pt;">{}</div>\n'.format(idStr,'i{}'.format(ixDiv), lft, btm,width,txt)
    return htm,divIdVal

def assignDivId(diDivId):
    css='\n'
    diId={}
    for ix,divIdTup in enumerate(diDivId.items()):
        for ixDiv in divIdTup[1]:
            diId['i{}'.format(ixDiv)]='i{}'.format(ix)
        css+='.i{}{{{}}}\n'.format(ix,divIdTup[0])
    return css,diId

def breakMixedFontWrd(subLn):
    wrd=subLn[0]
    first = True
    lstBreak = []
    for ix,chrTup in enumerate(wrd):
        fontInfo = (chrTup[1]['font'], chrTup[1]['size'])
        if first:
            prevFontInfo = fontInfo
            first = False
            continue
        if fontInfo == prevFontInfo:
            continue
        prevFontInfo = fontInfo
        lstBreak.append(ix)
    lstBreak.append(ix)
    if ix==0:   # handling subLn having only one character
        lstBreak=[1]
    lstBreak=[0]+lstBreak
    lstClust=[]
    for st,end in zip(lstBreak[0:-1],lstBreak[1:]):
        lstClust.append([wrd[st:end]])
    return lstClust
def getCluster(subLn):
    if len(subLn)==1:
        newSubLn=breakMixedFontWrd(subLn)
        return newSubLn

    lstSpace = []
    for ix, wrd in enumerate(subLn[0:-1]):
        lstBbx=[tuple(map(float, chrTup[1]['bbox'].split(','))) for chrTup in wrd]
        avgChrLen =mean([bbx[2]-bbx[0] for bbx in lstBbx[:-1]])
        avgWrdSpc = lstBbx[-1][2]-lstBbx[-1][0]
        lstSpace.append((round(avgChrLen,2), round(avgWrdSpc,2)))
    # print(lstSpace)
    lstBreak = []
    ixStart = 0
    for ix, spcTup in enumerate(lstSpace):
        if (spcTup[1] / max(0.1, spcTup[0])) < 2: # max added to avoid ZeroDivisionError
            continue
        lstBreak.append((ixStart, ix + 1))
        ixStart = ix + 1
    lstBreak.append((ixStart, ix + 2))
    # print(lstBreak)
    lstCluster=[]
    for tupBrk in lstBreak:
        lstCluster.append(subLn[tupBrk[0]:tupBrk[1]])
    return lstCluster

def escapeText(text):
    text = re.sub(r'\{', '{{', text)
    text = re.sub(r'\}', '}}', text)
    text = html.escape(text)
    return text

def getBbxLen(bbx):
    return bbx[2]-bbx[0]

def getWidth(lstChr):
    if len(lstChr)>1:
        return getBbxTup(lstChr[-2])[2]-getBbxTup(lstChr[0])[0]
    elif len(lstChr)==1:
        return getBbxTup(lstChr[-1])[2] - getBbxTup(lstChr[0])[0]
    else:
        return 0
def mapBbx(bbxStr):
    return tuple(map(float, bbxStr.split(',')))

def getBbxTup(chrTup):
    return mapBbx(chrTup[1]['bbox'])


def getText(lstChr):
    return ''.join([chrTup[0] for chrTup in lstChr])

def getMean(lst):
    if lst:
        round(mean(lst))
    return 0
def scaleBbx(bbx):
    return tuple([elm*const.dimScaler for elm in bbx])

def computeRect(pgBound,tg):
    et=lxml.html.fromstring(tg)
    bbxStr=et.xpath("string(//rect/@bbox)")
    bbx=mapBbx(bbxStr)
    bbx1=scaleBbx(bbx)
    x=bbx1[0]
    x1=bbx1[2]
    y=(pgBound[1]-bbx1[3])
    y1=(pgBound[1]-bbx1[1])
    width=x1-x
    height=y1-y

    return (round(x,2),round(y,2),round(width,2),round(height,2))

def computePolyline(pgBound,tg):
    et=lxml.html.fromstring(tg)
    ptsStr=et.xpath("string(//curve/@pts)")
    ptsTup=mapBbx(ptsStr)
    ptsTup1=scaleBbx(ptsTup)
    return zip(ptsTup1[0::2],[pgBound[1]-elm for elm in ptsTup1[1::2]])

def computeLine(pgBound,tg):
    et=lxml.html.fromstring(tg)
    bbxStr=et.xpath("string(//line/@bbox)")
    bbx=mapBbx(bbxStr)
    bbx1=scaleBbx(bbx)
    x=bbx1[0]
    x1=bbx1[2]
    y=(pgBound[1]-bbx1[3])
    y1=(pgBound[1]-bbx1[1])
    return (round(x,2),round(y,2),round(x1,2),round(y1,2))

def displayRect(lst,pgBound,html):
    for tg in lst:
        x,y,width,height=computeRect(pgBound, tg)
        html+='<rect x="{}pt" y="{}pt" width="{}pt" height="{}pt" class="g g1"  />\n'.format(x,y,width,height)
    return html

def displayLine(lst,pgBound,html):
    for tg in lst:
        x1,y1,x2,y2=computeLine(pgBound, tg)
        html+='<line x1="{}pt" y1="{}pt" x2="{}pt" y2="{}pt"  class="g g1"  />\n'.format(x1,y1,x2,y2)
    return html

def displayPolyline(lst,pgBound,html):
    isCurve = False
    for tg in lst:
        if not isCurve:
            html += '<svg  viewbox="0 0 {} {}" width="{}pt" height="{}pt">\n'.format(pgBound[0], pgBound[1],
                                                                                         pgBound[0], pgBound[1])
        isCurve = True
        lstTup = computePolyline(pgBound, tg)
        ptsStr = ' '.join([','.join([str(round(elm, 2)) for elm in tup]) for tup in lstTup])
        html += '<polyline points="{}" class="g" />\n'.format(ptsStr)
    if isCurve:
        html += "</svg>\n"
    return html
def displayGraphics(htmLocal,pgBound,pgGraphics):
    pgBound1=scaleBbx(pgBound)
    htmLocal+='<svg  width="{}pt" height="{}pt">\n'.format(pgBound1[0],pgBound1[1])
    if const.renderLines:
        htmLocal=displayRect(pgGraphics.get('rect',[]), pgBound1,htmLocal)
        htmLocal=displayLine(pgGraphics.get('line', []), pgBound1, htmLocal)
    if const.renderShapes:
        htmLocal=displayPolyline(pgGraphics.get('curve', []), pgBound1, htmLocal)
    htmLocal += "</svg>\n"
    return htmLocal
def getHtml(newData,scale):
    htm='<html>\n<body>\n'
    htmGlobal=addGlobalStyle(htm)
    ixDiv=0
    diDivId={}
    htmLocal=''
    for ixPg,tupPg in enumerate(newData):
        ##print('************page:{}****************'.format(ixPg))
        pgBound, pgLines,pgGraphics=tupPg[0],tupPg[1],tupPg[2]
        htmLocal += '<div style="border-style: ridge;overflow: hidden; position: relative; background-color: white; width: {}pt; height: {}pt;">\n'.format(round(pgBound[0]*scale),round(pgBound[1]*scale))
        pg=pgLines[0]
        lines=pgLines[1]
        htmLocal=displayGraphics(htmLocal,pgBound,pgGraphics)
        for ixLn,ln in enumerate(lines):
            newTxtLn=[subLn[0] for subLn in ln[1]]
            for ixSubLn,subLn in enumerate(newTxtLn):
                lstCluster=getCluster(subLn)
                for ixClust,clust in enumerate(lstCluster):
                    if const.clustLevel:
                        ixDiv += 1
                        lstChr = [chrTup for wrd in clust for chrTup in wrd]
                        lstSpaceLen = [getBbxLen(getBbxTup(chrTup)) for chrTup in lstChr if chrTup[0]==" "]
                        lstNonSpacLen = [getBbxLen(getBbxTup(chrTup)) for chrTup in lstChr if chrTup[0]!=" "]
                        avgSpcLen=getMean(lstSpaceLen)
                        avgNonSpcLen=getMean(lstNonSpacLen)
                        clustTxt = getText(lstChr)
                        clustTxt=escapeText(clustTxt)
                        print('***text:{}****'.format(clustTxt))
                        width=getWidth(lstChr)
                        tupId=(ixPg,ixLn,ixSubLn,ixClust)
                        if width>0:
                            htmLocal, divIdVal = createTextDiv(clust[0][0], clustTxt, htmLocal, scale, ixDiv,width,tupId,spcLen=avgSpcLen,nonSpcLen=avgNonSpcLen)
                            diDivId.setdefault(divIdVal, []).append(ixDiv)
                    else:
                        for ixWrd,wrd in enumerate(clust):
                            if const.wrdLevel:
                                ixDiv+=1
                                wrdTxt=getText(wrd)
                                width=getWidth(wrd)
                                wrdTxt = escapeText(wrdTxt)
                                print(wrdTxt)
                                tupId = (ixPg, ixLn, ixSubLn,ixClust,ixWrd)
                                htmLocal,divIdVal = createTextDiv(wrd[0],wrdTxt,htmLocal,scale,ixDiv,width,tupId)
                                diDivId.setdefault(divIdVal,[]).append(ixDiv)
                            else:
                                for ixChr,chrTup in enumerate(wrd):
                                    ixDiv += 1
                                    width = getWidth([chrTup])
                                    chrTxt = getText([chrTup])
                                    tupId = (ixPg, ixLn, ixSubLn,ixClust, ixWrd,ixChr)
                                    htmLocal, divIdVal = createTextDiv(chrTup, chrTxt, htmLocal, scale, ixDiv,width,tupId)
                                    diDivId.setdefault(divIdVal, []).append(ixDiv)
        htmLocal+="</div>\n"
    idCss,diId=assignDivId(diDivId)
    htmGlobal=addIdInfo(htmGlobal,idCss)
    htmLocal=htmLocal.format(**diId)
    htmGlobal+=htmLocal
    htmGlobal += "</body>\n</html>\n"
    return htmGlobal


def mainFunc(fNm,token='1234'):
    xmlGen = splitPdfXmlConv(fNm)
    # lstData = pageApiWrapperAsync(fNm, token, xmlGen)
    lstData=pageApiWrapper(fNm, token, xmlGen)
    newData = getLines(lstData)
    html = getHtml(newData, const.dimScaler)
    return html
if __name__=='__main__':
    fNm='UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059_91-95'
    fNm='Chintala'
    # fNm='out1'
    # fNm='AnsariSofia'
    # fNm='AAAL18HM4092040_000_E_H0432001_EnrollmentReceipt'
    # fNm='Filed_NY_KA_Choice_Plus_COC-3'
    # fNm='07_12_18_initial_board_profiles_final'
    # fNm='HBS_Ananthapuramu_District_2013-216'
    # fNm='Alexander,_Preston_C_MD_profile-1'
    # fNm='Filed_Form_TX_2018_HMO_SB_Navigate_RX_SBN'
    # fNm='Test_Form_TX_2018_KA_SelectPlus_ChoicePlus_SBN'
    # fNm='Dummit-and-Foote-Abstract-Algebra-30-35'
    # fNm='Dummit-and-Foote-Abstract-Algebra'
    # fNm='PR-4935872'
    # fNm='Request Letter- UHC'
    # fNm='Request_letter'
    # fNm='Request Letter out of network-p'
    # fNm='PR-4935872'
    # fNm='air2010-11complete'
    # fNm='air2010-11complete-176-177'
    # fNm='Demographics (2)'
    # fNm='Doc2'
    # fNm='triangles'
    fNm='CONTRACT LETTTER0'

    token='123456'
    st=datetime.datetime.now()
    xmlGen=splitPdfXmlConv(fNm)
    # lstData=pageApiWrapperAsync(fNm, token, xmlGen)
    lstData=pageApiWrapper(fNm, token, xmlGen)
    newData=getLines(lstData)
    html=getHtml(newData,const.dimScaler)
    with open(r'C:\Users\RA373432\Desktop\tmp2.html','wb') as fp:
        fp.write(html.encode('utf-8'))
    print('total time taken in pdf to html conversion :',(datetime.datetime.now()-st).seconds)
