import subprocess
from PIL import Image
import math
import lxml.html
import re
import cv2
import numpy as np
import copy
from bin import constants
from os.path import abspath, dirname, join
from bin import convertPdf
from bin import utils
from bin import extractTable as tblExt
import pandas as pd
import os
from datetime import datetime
from lxml import etree
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



def pdfToXml(inpPdfPath,xmlPath):
    output=subprocess.check_output("{0} {1} {2} -o {3} -txml".format(pythonPath,pdfToXmlToolPath,inpPdfPath,xmlPath))
    return output


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

def cropMultiBoxes(inpFileNm,lstBbox,inpDir=constants.imageDir,outDir=constants.imageDir):
    inpfileNmNoExt=inpFileNm.split('.png')[0]
    inpFilePath=inpDir+inpFileNm
    outExt='.png'
    im=Image.open(inpFilePath)
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    for bBox,tagTyp in lstBbox:
        bBox=list(bBox)
        xMax = im.size[0]
        yMax = im.size[1]
        newBbox=translateBbox(bBox,yMax)
        outImg=im.crop(newBbox)
        outFilePath=outDir+tagTyp+'_'+str(newBbox)+'_'+str(bBox)+outExt
        try:
            if constants.debugCropLog:
                print('outfilePath==> {0}'.format(outFilePath))

            outImg.save(outFilePath,"PNG")
        except Exception as e:
            print(e.__str__())
            pass
    im.close()

def cropMultiFiles(diBbox):
    for inpFileNm,lstBbox in diBbox.items():
        cropMultiBoxes(inpFileNm, lstBbox)


def imgPxlToPdfPxl(imgPxl):
    return math.floor((imgPxl/150)*72)

def imgYtoPdfY(pdfPxl,pdfMaxY):
    pdfPxl=pdfMaxY-pdfPxl
    return pdfPxl


def imgBboxToPdfBbox(ul,lr,imgMaxY):
    pdfMaxY=imgPxlToPdfPxl(imgMaxY)
    ul0,ul1=imgPxlToPdfPxl(ul[0]),imgPxlToPdfPxl(ul[1])
    lr0,lr1=imgPxlToPdfPxl(lr[0]),imgPxlToPdfPxl(lr[1])
    pdfUl1=imgYtoPdfY(ul1, pdfMaxY)
    pdflr1=imgYtoPdfY(lr1, pdfMaxY)
    return (ul0,pdflr1,lr0,pdfUl1)

def getTagText(elmStr):
    if not elmStr:
        return ""
    elm=lxml.html.fromstring(elmStr)
    txt = "".join(elm.xpath('.//text()'))
    txt = re.sub('\n+', '', txt)
    return txt
def getXmlInsideBbox(diTags,bBox,isLastRow,text=False):
    def isTagBboxInside(tagBbox,bBox,isLastRow):
        isInside=False
        if isLastRow:
            if (math.ceil(tagBbox[0])>=bBox[0] or math.ceil(tagBbox[0])+1>=bBox[0]) and (math.ceil(tagBbox[1])>=bBox[1] or math.ceil(tagBbox[1])+5>=bBox[1]) and (math.floor(tagBbox[2])<=bBox[2] or math.floor(tagBbox[2])-3<=bBox[2]) and (math.floor(tagBbox[3])<=bBox[3] or math.floor(tagBbox[3])-3<=bBox[3]):
                isInside = True
        else:
            if (math.ceil(tagBbox[0])>=bBox[0] or math.ceil(tagBbox[0])+1>=bBox[0]) and (math.ceil(tagBbox[1])>=bBox[1] or math.ceil(tagBbox[1])+1>=bBox[1]) and (math.floor(tagBbox[2])<=bBox[2] or math.floor(tagBbox[2])-3<=bBox[2]) and (math.floor(tagBbox[3])<=bBox[3] or math.floor(tagBbox[3])-3<=bBox[3]):
                isInside = True
        return isInside
    tagsInsideBBox=[]
    for tagBbox,tagTup in diTags.items():
        isInside=isTagBboxInside(tagBbox, bBox, isLastRow)
        if isInside:
            if text:
                txt = "".join(tagTup[1].xpath('.//text()'))
                txt = re.sub('\n+', '', txt)
                tagsInsideBBox.append((tagBbox,txt))
            else:
                tagsInsideBBox.append((tagBbox,tagTup[1]))

    tagsInsideBBoxSrt=[tg[1] for tg in sorted(tagsInsideBBox, key=lambda tup: (-tup[0][3],tup[0][0]))]
    return tagsInsideBBoxSrt

def imgBboxToPdfBboxMult(diBBox,maxY):
    diPdfBbox={}
    for ul,lr in diBBox.items():
        k=ul+lr
        diPdfBbox[k]=imgBboxToPdfBbox(ul,lr,maxY)
    return diPdfBbox

def getXmlInsideBboxMult(diPdfBbox,diTags,text=False):
    def lastRowY0(diPdfBbox):
        srt=sorted(list(diPdfBbox.keys()), key=lambda tup: tup[1])
        if srt:
            return srt[-1][1]
    lastRowYLow=lastRowY0(diPdfBbox)
    diBboxText={}
    isLastRow=False
    for imbBbox,pdfBbox in diPdfBbox.items():
        if imbBbox[1]==lastRowYLow:
            isLastRow=True
        diBboxText[imbBbox]=getXmlInsideBbox(diTags,pdfBbox,isLastRow,text=text)
    return diBboxText

def pdfToImg(fNm, stPage, enPage,**kwargs):
    fPath=kwargs.get('pdfDir',constants.pdfDir)+fNm+'.pdf'
    absFPath = abspath(join(dirname(__file__), fPath))
    outPath=constants.imageDir+fNm
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    absOutPath=abspath(join(dirname(__file__), outPath, fNm))
    pdfToImgToolPath=abspath(join(dirname(__file__),constants.pdfToImgToolPath))
    subprocess.check_call('"%s" -png -f %s -l %s %s %s ' % (pdfToImgToolPath, stPage, enPage, absFPath,absOutPath))

def pdfToImgPDFBox(fNm, stPage, enPage,**kwargs):
    pdfDir=kwargs.get('pdfDir',constants.pdfDir)
    pdfDir=pdfDir if pdfDir else constants.pdfDir
    fPath=pdfDir+fNm+'.pdf'
    absFPath = abspath(join(dirname(__file__), fPath))
    outPath=constants.imageDir+fNm
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    absOutPath=abspath(join(dirname(__file__), outPath, 'p'+'-'))
    pdfToImgToolPath=abspath(join(dirname(__file__),constants.pdfToImgToolPath))
    subprocess.check_call('java -jar %s PDFToImage %s -imageType png -dpi 150 -startPage %s -endPage %s -outputPrefix %s ' % (pdfToImgToolPath, absFPath, stPage, enPage, absOutPath),shell=True)

def treatBlankPg(tree):
    for pg in tree.xpath('//pages//page'):
        if len(pg.getchildren()) == 0:
            txtTag = etree.Element("text")
            txtTag.text = ""
            txtTag.attrib['bbox'] = "0,0,0,0"
            # txtTag.text = "."
            # txtTag.attrib['bbox'] = "0,0,1,1"
            # txtTag.attrib['font'] = "Arial,Bold"
            # txtTag.attrib['size'] = "1"
            pg.append(txtTag)
    return tree

def convertMultiple(lstFiles,**kwargs):
    diOut={}
    for f in lstFiles:
        inpFile=kwargs.get('pdfDir',constants.pdfDir)+f+'.pdf'
        output=convertPdf.convert_pdf_doc(inpFile)
        tree = lxml.html.fromstring(output)
        tree=treatBlankPg(tree)
        diOut[f]=lxml.html.tostring(tree)
    return diOut

def convertMultipleNew(lstFiles,**kwargs):
    diOut={}
    for fNm,xml in lstFiles:
        tree = lxml.html.fromstring(xml)
        tree = treatBlankPg(tree)
        diOut[fNm]=lxml.html.tostring(tree)
    return diOut

def queryXml(tree,sel,text=False,tagAttrib=False,tagAttribAndText=False):
    lstElm=tree.xpath(sel)
    diElm={}
    for elm in lstElm:
        bboxStr=elm.xpath("normalize-space(.//@bbox)")#"69.000,708.401,562.163,723.401"
        bbox=tuple([float(elm) for elm in bboxStr.split(',')])
        if text:
            text = "".join(elm.xpath('.//text()'))
            text = re.sub('\n+', '', text)
            diElm[bbox]=text.strip()
        else:
            if tagAttrib:
                diElm[bbox] = (elm.tag,elm,dict(elm.attrib))
            elif tagAttribAndText:
                diElm[bbox] = (elm.tag, elm, dict(elm.attrib),elm.text)
            else:
                diElm[bbox] = (elm.tag,elm)
    return diElm

def parseTree(tree,selKey='textline',pageNo=1,sort=True,text=False,qry=None,tagAttribAndText=False):
    if not qry:
        qry=constants.diSel[selKey].format(int(pageNo))
    diTags = queryXml(tree, qry,text=text,tagAttribAndText=tagAttribAndText)
    if sort:
        srt = sorted(zip(diTags.keys(), diTags.values()), key=lambda tup: (-tup[0][1],tup[0][0]))
        return srt

    return diTags

def findPgTag(tree):
    return len(tree.xpath("//page"))

def addBboxToBlankTextTag(tree):
    t = list(zip(tree.xpath('//text[text()=" " and not(@bbox)]/preceding-sibling::text[1]'),
                 tree.xpath('//text[text()=" " and not(@bbox)]/following-sibling::text[1]')))
    t1 = [(tuple(map(float, tup[0].xpath('.//@bbox')[0].split(','))),
           tuple(map(float, tup[1].xpath('.//@bbox')[0].split(',')))) for tup in t]
    t2 = [(round(tup[0][2] + 0.1, 2), tup[0][1], round(tup[1][0] - 0.1, 2), tup[0][3]) for tup in t1]
    for blankTextTag,newBbox in zip(tree.xpath('//text[text()=" " and not(@bbox)]'),t2):
        blankTextTag.attrib['bbox']=','.join([str(elm) for elm in newBbox])
    return tree
def parseMultiple(diXml,pages=None,selKey='textline',text=True):
    diParsed = {}
    for f,xml in diXml.items():
        tree = lxml.html.fromstring(xml)
        tree=addBboxToBlankTextTag(tree)
        numOfPages=findPgTag(tree)
        pageDi={}
        if pages:
            for pgNo in pages:
                parsed = parseTree(tree,selKey=selKey,pageNo=pgNo,text=text)
                pageDi.update({pgNo:parsed})
        else:
            for pgNo in range(1,numOfPages+1):
                parsed = parseTree(tree,selKey=selKey,pageNo=pgNo,text=text)
                pageDi.update({pgNo:parsed})
        diParsed.update({f:pageDi})
    return diParsed

def debugTimeTaken(st,end,stage,debug=constants.debugTime):
    if debug:
        print('Time Taken in {}: '.format(stage), end - st)
