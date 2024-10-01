import cv2
import numpy as np
import copy
# from bin import pdfminer_testing as pdfmin
from collections import defaultdict
from collections import OrderedDict
from itertools import groupby
from bin import utils
from bin import constants
from bin import main as mn

def getLSgmt(edges,minLLen,type='H'):
    lstVLines=[]
    for idxLstCell,lstCell in enumerate(edges):
        if not any(lstCell):
            # lstVLines.append([])
            continue
        lstLineSeg=[]
        start=0
        end=0
        for cellIdx,cellVal in enumerate(lstCell):
            if cellVal and not start:
                start=cellIdx
            if cellVal:
                end=cellIdx
            if not cellVal and start:
                if end-start>=minLLen:
                    if type=='H':
                        lstLineSeg.append((start,idxLstCell,end,idxLstCell))
                    elif type=='V':
                        lstLineSeg.append((idxLstCell, start, idxLstCell, end))
                start = 0
                end = 0
        if lstLineSeg:
            lstVLines.append(lstLineSeg)
    return lstVLines

def captureIntersections(lstHLines,lstVLines):
    lstIntersections=[]
    for lstHLine in lstHLines:
        for hLSeg in lstHLine:
            xRange=(hLSeg[0],hLSeg[2])
            yStatic=hLSeg[1]
            for lstVLine in lstVLines:
                for vLSeg in lstVLine:
                    isXInRange,isYInRange=False,False
                    yRange = (vLSeg[1], vLSeg[3])
                    xStatic = vLSeg[0]
                    if xRange[0]<=xStatic<=xRange[1]:
                        isXInRange=True
                    if yRange[0]<=yStatic<=yRange[1]:
                        isYInRange=True
                    if isXInRange and isYInRange:
                        lstIntersections.append((xStatic,yStatic))
    return list(set(lstIntersections))

def getBBox(lstIntersections,lstHLines,lstVLines):
    diHLines={lst[0][1]:lst for lst in lstHLines}
    diVLines={lst[0][0]:lst for lst in lstVLines}
    lstIntersections=sorted(lstIntersections,key=lambda tup:(tup[1],tup[0]))
    diBbox={}
    for idx,pt in enumerate(lstIntersections[0:-1]):
        pt_right=sorted([p for p in lstIntersections if p[1]==pt[1] and p[0]>pt[0]],key=lambda tup:tup[0])
        pt_btm=sorted([p for p in lstIntersections if p[0]==pt[0] and p[1]>pt[1]],key=lambda tup:tup[0])
        if not pt_right or not pt_btm:
            continue
        for idx1,pt1 in enumerate(lstIntersections[idx+1:]):
            if pt1[0]==pt[0] or pt1[1]==pt[1]:
                continue
            if (pt1[0],pt[1])in pt_right and (pt[0],pt1[1]) in pt_btm:
                pt1ToPtLsUp=(pt1[0],pt[1],pt1[0],pt1[1])
                pt1ToPtLsleft=(pt[0],pt1[1],pt1[0],pt1[1])

                ptToPt1LsBtm = (pt[0], pt[1], pt[0], pt1[1])
                ptToPt1LsRight = (pt[0], pt[1], pt1[0], pt[1])
                if pt not in diBbox:
                    if not (any([ vLs for vLs in diVLines[pt1[0]] if vLs[1]<=pt1ToPtLsUp[1]<pt1ToPtLsUp[3]<=vLs[3]]) and any([ hLs for hLs in diHLines[pt1[1]] if hLs[0]<=pt1ToPtLsleft[0]<pt1ToPtLsleft[2]<=hLs[2]])):
                        continue
                    if not (any([ vLs for vLs in diVLines[pt[0]] if vLs[1]<=ptToPt1LsBtm[1]<ptToPt1LsBtm[3]<=vLs[3]]) and any([ hLs for hLs in diHLines[pt[1]] if hLs[0]<=ptToPt1LsRight[0]<ptToPt1LsRight[2]<=hLs[2]])):
                        continue
                    diBbox[pt] = pt1

    return diBbox

def debugLS(img,lstHLines,lstVLines):
    for lstHLine in lstHLines:
        for lSeg in lstHLine:
            cv2.line(img, (lSeg[0], lSeg[1]), (lSeg[2], lSeg[3]), (0, 255, 0), 1)
    for lstVLine in lstVLines:
        for lSeg in lstVLine:
            cv2.line(img, (lSeg[0], lSeg[1]), (lSeg[2], lSeg[3]), (0, 255, 0), 1)

    cv2.imwrite(constants.debugLsPath,img)

def debugPoints(img,lstPts):
    for pt in lstPts:
        cv2.putText(img, "Pt{}".format(pt), pt, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
    cv2.imwrite(constants.debugPtsPath, img)

def debugBbox(img,diBBox):
    for ul, lr in diBBox.items():
        cv2.putText(img, "UL{}".format(str(ul)), ul, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        cv2.putText(img, "LR{}".format(str(lr)), lr, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
    cv2.imwrite(constants.debugPtsPath, img)

def imgBboxToPdfBboxMult(diBBox,maxY):
    diPdfBbox={}
    for ul,lr in diBBox.items():
        k=ul+lr
        diPdfBbox[k]=pdfmin.imgBboxToPdfBbox(ul,lr,maxY)
    return diPdfBbox

def getTextInsideBboxMult(lstPdfBbox,diTags):
    diBboxText={}
    for pdfBbox in lstPdfBbox:
        diBboxText[pdfBbox]=pdfmin.getTextInsideBbox(diTags,pdfBbox)
    return diBboxText



def bboxesToTable(di):
    def desolveOvrlapCk(ck, ck1,ixLow,ixUp,ixCmnLow,ixCmnUp,dslTyp):
        cmnLow, cmnUp = ck[ixCmnLow], ck[ixCmnUp]
        ckLow,ckUp,ck1Low,ck1Up = ck[ixLow],ck[ixUp],ck1[ixLow],ck1[ixUp]

        if ckLow == ck1Low:
            if dslTyp=='hr':
                return [(cmnLow, ckLow, cmnUp, ckUp), (cmnLow, ckUp, cmnUp, ck1Up)]
            elif dslTyp == 'vr':
                return [(ckLow,cmnLow, ckUp,cmnUp), (ckUp,cmnLow,ck1Up,cmnUp)]
        elif ckLow < ck1Low:
            if dslTyp == 'hr':
                return [(cmnLow, ckLow, cmnUp, ck1Low), (cmnLow, ck1Low, cmnUp, ckUp), (cmnLow, ckUp, cmnUp, ck1Up)]
            elif dslTyp == 'vr':
                return [(ckLow,cmnLow,ck1Low, cmnUp), (ck1Low,cmnLow,ckUp,cmnUp), (ckUp,cmnLow,ck1Up,cmnUp)]

    def getNonOvrLapCk(chunk,lstDslvd,dslType):
        if dslType=='hr':
            ixLow,ixUp=1,3
            ixCmnLow,ixCmnUp=0,2
        elif dslType=='vr':
            ixLow,ixUp=0,2
            ixCmnLow,ixCmnUp=1,3
        lstFlat=[ck for sbLst in [di.keys() for di in lstDslvd] for ck in sbLst]
        flag=True
        while(flag):
            lstSrt=sorted(list(set(lstFlat)),key=lambda tup:(tup[ixLow],tup[ixUp]-tup[ixLow]))
            for ix in range(len(lstSrt)-1):
                ck,ck1=lstSrt[ix],lstSrt[ix+1]
                if not(ck[ixLow]<=ck1[ixLow]<ck[ixUp]):
                    continue
                lstDsl=desolveOvrlapCk(ck,ck1,ixLow,ixUp,ixCmnLow,ixCmnUp,dslType)
                if lstDsl:
                    lstFlat.remove(ck)
                    lstFlat.remove(ck1)
                    lstFlat.extend(lstDsl)
                    break

            else:
                flag=False
                diNonOLCk ={ck:chunk for ck in set(lstSrt)}
        return diNonOLCk

    def desolveVr(ck,ck1,bbox,bbox1):
        tDi,tDi1= {},{}
        ck_p1_x,ck_p1_y,ck_p2_x,ck_p2_y= ck[0],ck[1],ck[2],ck[3]
        ck1_p1_x, ck1_p1_y, ck1_p2_x, ck1_p2_y = ck1[0], ck1[1], ck1[2], ck1[3]
        ckLow,ckUp=ck_p1_x,ck_p2_x
        ck1Low,ck1Up=ck1_p1_x,ck1_p2_x

        if ckLow < ck1Low < ckUp and ckLow < ck1Up < ckUp:
            tDi = {(ck_p1_x, ck_p1_y, ck1_p1_x, ck_p2_y): bbox,
                   (ck1_p1_x, ck_p1_y, ck1_p2_x, ck_p2_y): bbox,
                   (ck1_p2_x, ck_p1_y, ck_p2_x, ck_p2_y): bbox}
        elif ck1Low < ckLow < ck1Up and ck1Low < ckUp < ck1Up:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck_p1_x, ck1_p2_y): bbox1,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck1_p2_y): bbox1,
                   (ck_p2_x, ck1_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Low < ckUp and ckUp < ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck1_p1_x, ck_p2_y): bbox,
                   (ck1_p1_x, ck_p1_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck_p2_x, ck1_p2_y): bbox1,
                    (ck_p2_x, ck1_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Low < ckUp and ckUp == ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck1_p1_x, ck_p2_y): bbox,
                   (ck1_p1_x, ck_p1_y, ck_p2_x, ck_p2_y): bbox}


        elif ckLow < ck1Up < ckUp and ckLow>ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck1_p2_x, ck_p2_y): bbox,
                   (ck1_p2_x, ck_p1_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck_p1_x, ck1_p2_y): bbox1,
                    (ck_p1_x, ck1_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Up < ckUp and ckLow == ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck1_p2_x, ck_p2_y): bbox,
                   (ck1_p2_x, ck_p1_y, ck_p2_x, ck_p2_y): bbox}

        elif ck1Low < ckUp < ck1Up and ck1Low == ckLow:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck_p2_x, ck1_p2_y): bbox1,
                   (ck_p2_x, ck1_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ck1Low < ckLow < ck1Up and ck1Up == ckUp:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck_p1_x, ck1_p2_y): bbox1,
                   (ck_p1_x, ck1_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        return tDi, tDi1

    def desolveHr(ck, ck1, bbox, bbox1):
        tDi, tDi1 = {}, {}
        ck_p1_x, ck_p1_y, ck_p2_x, ck_p2_y = ck[0], ck[1], ck[2], ck[3]
        ck1_p1_x, ck1_p1_y, ck1_p2_x, ck1_p2_y = ck1[0], ck1[1], ck1[2], ck1[3]
        ckLow, ckUp = ck_p1_y, ck_p2_y
        ck1Low, ck1Up = ck1_p1_y, ck1_p2_y

        if ckLow < ck1Low < ckUp and ckLow < ck1Up < ckUp:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p1_y): bbox,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck1_p2_y): bbox,
                   (ck_p1_x, ck1_p2_y, ck_p2_x, ck_p2_y): bbox}
        elif ck1Low < ckLow < ck1Up and ck1Low < ckUp < ck1Up:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p1_y): bbox1,
                    (ck1_p1_x, ck_p1_y, ck1_p2_x, ck_p2_y): bbox1,
                    (ck1_p1_x, ck_p2_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Low < ckUp and ckUp<ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p1_y): bbox,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p2_y): bbox1,
                    (ck1_p1_x, ck_p2_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Low < ckUp and ckUp==ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p1_y): bbox,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck_p2_y): bbox}


        elif ckLow < ck1Up < ckUp and ckLow>ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p2_y): bbox,
                   (ck_p1_x, ck1_p2_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p1_y): bbox1,
                    (ck1_p1_x, ck_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Up < ckUp and ckLow==ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p2_y): bbox,
                   (ck_p1_x, ck1_p2_y, ck_p2_x, ck_p2_y): bbox}

        elif ck1Low < ckUp < ck1Up and ck1Low == ckLow:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p2_y): bbox1,
                    (ck1_p1_x, ck_p2_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ck1Low < ckLow < ck1Up and ck1Up == ckUp:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p1_y): bbox1,
                    (ck1_p1_x, ck_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        return tDi, tDi1

    def desolveChunks(chunks,bbox,chunks1,bbox1,desolveType):
        chunksCp=copy.deepcopy(chunks)
        diP,di1P,delCk,delCk1={},{},[],[]

        for ck1 in sortLstBtmRight(chunks1):
            di,tDelCk,lstTdi1={},[],[]
            for ck in sortLstBtmRight(chunks):
                if desolveType=="hr":
                    if not getDiLeftToRight(ck,{ck1:ck1}):
                        continue
                    tDi,tDi1=desolveHr(ck, ck1, bbox, bbox1)

                elif desolveType == "vr":
                    if not getDiTopToBtm(ck,{ck1:ck1}):
                        continue
                    tDi, tDi1 = desolveVr(ck, ck1, bbox, bbox1)

                di.update(tDi)
                if tDi:
                    tDelCk.append(ck)

                if tDi1 and tDi1 not in lstTdi1:
                    lstTdi1.append(tDi1)

            if di:
                oldChunks={c:bbox for c in chunks}
                for c in tDelCk:
                    oldChunks.pop(c)
                    if c in chunksCp:
                        delCk.append(c)
                oldChunks.update(di)
                chunks=oldChunks.keys()
            if lstTdi1:
                di1P.update(getNonOvrLapCk(bbox1,lstTdi1,desolveType))
                delCk1.append(ck1)
        if set(chunks)!=set(chunksCp):
            diP={c:bbox for c in chunks}
        return diP,di1P,delCk+delCk1

    def reverseDi(di):
        diReverse = {}
        for k, v in di.items():
            diReverse.setdefault(v, []).append(k)
        return diReverse
    def getDiTopToBtm(bbox,di):
        diReverse=reverseDi(di)

        bboxLow, bboxUp = bbox[0], bbox[2]
        bboxOthUp =bbox[3]
        diTopToBtm={}
        for k, v in diReverse.items():
            kLow, kUp = k[0], k[2]
            kOthLow=k[1]
            if ((kLow <= bboxLow <= kUp) or (kLow <= bboxUp <= kUp) or ((bboxLow <= kLow <= bboxUp) and (bboxLow <= kUp <= bboxUp))) and ((bboxLow != kUp) and (bboxUp != kLow)) and not ((bboxLow, bboxUp) == (kLow, kUp)) and bboxOthUp <= kOthLow:
                diTopToBtm[k]=v

        return diTopToBtm

    def getDiLeftToRight(bbox,di):
        diReverse = reverseDi(di)

        bboxLow, bboxUp = bbox[1], bbox[3]
        bboxOthUp=bbox[2]
        diLeftToRight = {}
        for k, v in diReverse.items():
            kLow, kUp = k[1], k[3]
            kOthLow = k[0]
            if ((kLow <= bboxLow <= kUp) or (kLow <= bboxUp <= kUp) or ((bboxLow <= kLow <= bboxUp) and (bboxLow <= kUp <= bboxUp))) and ((bboxLow != kUp) and (bboxUp != kLow)) and not ((bboxLow, bboxUp) == (kLow, kUp)) and bboxOthUp <= kOthLow:
                diLeftToRight[k] = v

        return diLeftToRight

    def sortLstBtmRight(lst):
        return sorted(lst, key=lambda tup: (tup[1], tup[0]))

    def sortDiBtmRight(di):
        return OrderedDict(sorted(di.items(), key=lambda tup: (tup[0][1], tup[0][0])))

    def finalShape(diNew):
        rows = []
        for y in sorted(list(set([k[1] for k in diNew.keys()]))):
            row = []
            for c, p in sorted(diNew.items(), key=lambda tup: (tup[0][1], tup[0][0])):
                if c[1] == y:
                    row.append(p)
            rows.append(row)
        return rows

    diNew={ul + lr:ul + lr for ul,lr in di.items()}

    lstBboxSrt=sortLstBtmRight(diNew.keys())
    for bbox in list(lstBboxSrt):
        diTopToBtm=sortDiBtmRight(getDiTopToBtm(bbox,diNew))
        for bbx,lstChunks in diTopToBtm.items():
            di1,di2,delK=desolveChunks(reverseDi(diNew)[bbox],bbox,lstChunks,bbx,"vr")
            for elm in set(delK):
                diNew.pop(elm)
            diNew.update(di1)
            diNew.update(di2)

        diLeftToRight = sortDiBtmRight(getDiLeftToRight(bbox,diNew))
        for bbx, lstChunks in diLeftToRight.items():
            di1,di2,delK=desolveChunks(reverseDi(diNew)[bbox],bbox,lstChunks,bbx,"hr")
            for elm in set(delK):
                diNew.pop(elm)
            diNew.update(di1)
            diNew.update(di2)
    print(diNew)
    return finalShape(diNew)

def htmlTable(lol):
    diBboxGrp = {}
    for row in lol:
        tDi = {}
        for bbox in row:
            tDi.setdefault(bbox, []).append(bbox)
        for k, v in tDi.items():
            diBboxGrp.setdefault(k, []).append(v)
    diSpanInfo={}
    for k,v in diBboxGrp.items():
        colSpan=len(v[0])
        rowSpan=len(v)
        diSpanInfo.setdefault(k,{})['cSpan']=colSpan
        diSpanInfo.setdefault(k,{})['rSpan']=rowSpan

    srtLstBbx=sorted(diBboxGrp.keys(),key=lambda tup:(tup[1],tup[0]))
    grpd=groupby(srtLstBbx, lambda tup: tup[1])
    tblString='''<table border="1"><tbody>'''
    for _, g in grpd:
        trString='''<tr style="height: 15.0pt;">'''
        for elm in g:
            tdString=r'''<td rowspan="{0}" colspan="{1}">{{{2}}}</td>'''
            rSpan=diSpanInfo[elm]['rSpan']
            cSpan=diSpanInfo[elm]['cSpan']
            tdString=tdString.format(rSpan,cSpan,elm)
            trString+=tdString
        trString+='''</tr>'''
        tblString+=trString
    tblString+='''</tbody></table>'''
    return tblString,diSpanInfo


def temp():


    lstDi=[{(0, 0): (5, 3), (5, 0): (10, 5), (10, 0): (15, 3), (0, 3): (3, 5), (3, 3): (5, 5), (10, 3): (15, 5)},
    {(0,0):(4,2),(0,2):(2,4),(2,2):(4,4),(0,4):(4,8),(4,0):(8,4),(4,4):(6,5),(6,4):(8,5),(4,5):(8,7),(4,7):(8,8),(8,0):(12,2),(8,2):(12,4),
    (8,4):(10,5),(10,4):(12,5),(8,5):(10,6),(10,5):(12,6),(8,6):(10,7),(10,6):(12,7),(8,7):(10,8),(10,7):(12,8)
    },
       {(0, 0): (4, 2), (0, 2): (2, 4), (2, 2): (4, 4), (0, 4): (4, 8), (4, 0): (8, 4), (4, 4): (6, 5),
      (6, 4): (8, 5), (4, 5): (8, 7), (4, 7): (8, 8), (8, 0): (12, 2), (8, 2): (12, 4),
      (8, 4): (10, 6), (10, 4): (12, 5), (10, 5): (12, 6), (8, 6): (10, 7), (10, 6): (12, 8),
      (8, 7): (10, 8)
      },
    {(0, 0): (4, 2), (0, 2): (2, 4), (2, 2): (4, 4), (0, 4): (4, 8), (4, 0): (8, 4), (4, 4): (6, 5),
        (6, 4): (8, 5), (4, 5): (8, 7), (4, 7): (8, 8), (8, 0): (12, 2), (8, 2): (12, 4),
        (8, 4): (10, 6), (10, 4): (12, 5), (10, 5): (12, 6), (8, 6): (10, 7), (10, 6):(11,8),(11, 6):(12, 8),
        (8, 7): (10, 8)
        },
           {(0,4):(4,8),(4,4):(6,5),(6,4):(8,6),(8,4):(10,7),(4,5):(6,7),(6,6):(8,7),(4,7):(8,8),(8,7):(10,8)},
           {(10, 4): (18, 8), (10, 8): (12, 9), (12, 8): (18, 9), (10, 9): (14, 10), (14, 9): (18, 10),
            (10, 10): (16, 11), (16, 10): (18, 11), (10, 11): (12, 12), (12, 11): (14, 12), (14, 11): (18, 12)}]
    for di in lstDi[-1:]:
        lol=bboxesToTable(di)
        htm,diSpanInfo=htmlTable(lol)
        print(htm)


def readContours(img):

    blue, green, red = cv2.split(img)


    def medianCanny(img, thresh1, thresh2):
        median = np.median(img)
        img = cv2.Canny(img, int(thresh1 * median), int(thresh2 * median))
        return img


    blue_edges = medianCanny(blue, 0.2, 0.3)
    green_edges = medianCanny(green, 0.2, 0.3)
    red_edges = medianCanny(red, 0.2, 0.3)

    edges = blue_edges | green_edges | red_edges

    newEdges=None
    _,cnts,hrchy=cv2.findContours(edges,cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    hrchy=hrchy[0]
    for component in zip(cnts, hrchy):
        currentContour = component[0]
        currentHierarchy = component[1]
        x, y, w, h = cv2.boundingRect(currentContour)
        if currentHierarchy[2] < 0:
            # these are the innermost child components
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 1)
            pass
        elif currentHierarchy[3] < 0:
            # these are the outermost parent components
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 1)
    cv2.imwrite('cntImg.jpg', img)

def clnLS(lstHLines,lstVLines):
    def intraConnectLines(lstLines,ixLow,ixUp,tol=5):
        newlstLines=[]

        for lnIx,vLn in enumerate(lstLines):
            flag=True
            while (flag):
                vLnSrt = sorted((vLn), key=lambda tup: tup[ixLow])
                for ix in range(len(vLnSrt) - 1):
                    ls, ls1 = vLnSrt[ix], vLnSrt[ix + 1]
                    if 0<ls1[ixLow]-ls[ixUp]<tol:
                        t,t1=list(ls),list(ls1)
                        t[ixUp],t1[ixLow]=ls[ixUp]+1,ls[ixUp]+1
                        vLn.remove(ls)
                        vLn.remove(ls1)
                        vLn.extend([tuple(t),tuple(t1)])
                        break
                else:
                    flag = False
            newlstLines.append(vLnSrt)

        return newlstLines
    def interConnectLines(lstVLines,lstHLines,tol=5):
        lstVLinesCp=[[list(ls) for ls in ln] for ln in copy.deepcopy(lstVLines) ]
        lstHLinesCp=[[list(ls) for ls in ln] for ln in copy.deepcopy(lstHLines) ]
        flag = True
        while (flag):
            brk=False
            for hLnIx, hLn in enumerate(copy.deepcopy(lstHLinesCp)):
                for hLsIx, hLs in enumerate(hLn):
                    for vLnIx, vLn in enumerate(copy.deepcopy(lstVLinesCp)):
                        for vLsIx, vLs in enumerate(vLn):
                            xStatic=vLs[0]
                            yStatic=hLs[1]
                            if vLs[3]<yStatic:
                                dif=yStatic-vLs[3]
                                if dif<=tol:
                                    lstVLinesCp[vLnIx][vLsIx][3]+=dif

                            elif yStatic<vLs[1]:
                                dif=vLs[1]-yStatic
                                if dif<=tol:
                                    lstVLinesCp[vLnIx][vLsIx][1] -= dif

                            if hLs[2]<xStatic:
                                dif=xStatic-hLs[2]
                                if dif<=tol:
                                    lstHLinesCp[hLnIx][hLsIx][2]+=dif
                                    brk = True
                                    break

                            elif xStatic<hLs[0]:
                                dif=hLs[0]-xStatic
                                if dif<=tol:
                                    lstHLinesCp[hLnIx][hLsIx][0] -= dif
                                    brk = True
                                    break

                        if brk:
                            break
                    if brk:
                        break
                if brk:
                    break
            if not brk:
                flag=False
        lstVLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstVLinesCp)]
        lstHLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstHLinesCp)]
        return lstVLines,lstHLines

    lstVLines=lstVLines
    lstHLines=lstHLines
    newLstVLines=intraConnectLines(lstVLines,1,3)
    newLstHLines=intraConnectLines(lstHLines,0,2)
    newLstVLines,newLstHLines=interConnectLines(newLstVLines, newLstHLines)

    return newLstHLines,newLstVLines


def findAllTbls(img,lstHLines, lstVLines):

    def intraConnectLines(lstLines,ixLow,ixUp,tol=5):
        newlstLines=[]

        for lnIx,vLn in enumerate(lstLines):
            flag=True
            while (flag):
                vLnSrt = sorted((vLn), key=lambda tup: tup[ixLow])
                for ix in range(len(vLnSrt) - 1):
                    ls, ls1 = vLnSrt[ix], vLnSrt[ix + 1]
                    if 0<ls1[ixLow]-ls[ixUp]<tol:
                        t,t1=list(ls),list(ls1)
                        t[ixUp],t1[ixLow]=ls[ixUp]+1,ls[ixUp]+1
                        vLn.remove(ls)
                        vLn.remove(ls1)
                        vLn.extend([tuple(t),tuple(t1)])
                        break
                else:
                    flag = False
            newlstLines.append(vLnSrt)

        return newlstLines

    def mergeLs(lstLines,ixUp,ixLow):
        newLstLines=[]
        for ln in lstLines:
            prevUp = None
            sliceLow=0
            flag=True
            while(flag):
                for ix,ls in enumerate(ln[sliceLow:]):
                    if ix==0:
                        newBbox=ls
                    crntLow=ls[ixLow]
                    crntUp=ls[ixUp]
                    if prevUp:
                        if prevUp==crntLow:
                            tmp=list(newBbox)
                            tmp[ixUp]=crntUp
                            newBbox=tuple(tmp)
                            prevUp=crntUp
                            continue
                        prevUp = crntLow
                        sliceLow+=ix
                        newLstLines.append(newBbox)
                        break
                    else:
                        prevUp=crntUp
                else:
                    flag=False
                    newLstLines.append(newBbox)
        return newLstLines

    def reshpDiLines(diLines,ixLow,ixSrt):
        diLinesNew = {}
        for bbx, lst in list(diLines.items()):
            diLinesNew[bbx] = []
            vSteps = sorted(list(set([ls[ixLow] for ls in lst])))
            for ix, step in enumerate(vSteps):
                lstStep = []
                for hLs in lst:
                    if hLs[ixLow] == step:
                        lstStep.append(hLs)
                diLinesNew[bbx].append(sorted(lstStep, key=lambda tup: tup[ixSrt]))
        return diLinesNew

    def findTblMainBbox(lstHLines,lstVLines,tol=5):
        lstMainBbox=[]
        flag=True
        while(flag):
            brk=False
            for hLs in lstHLines:
                if any([bbx[0]<=hLs[0]<=bbx[2] and bbx[1]<=hLs[1]<=bbx[3] for bbx in lstMainBbox]):
                    continue
                for vLs in lstVLines:
                    if not (vLs[0]+tol>=hLs[0] and vLs[1]>=hLs[1]):
                        continue
                    xStatic=vLs[0]
                    yStatic=hLs[1]
                    xDif=hLs[0]-xStatic
                    yDif=vLs[1]-yStatic
                    if xDif<=5 and yDif<=5:
                        try:
                            pt1_x,pt1_y=xStatic,yStatic
                            tmpX1=[ls for ls in sorted(lstVLines,key=lambda tup:(-tup[0],tup[1])) if 0<=ls[0]-hLs[2]<=tol and 0<=ls[1]-hLs[1]<=tol]
                            tmpX2=[ls for ls in sorted(lstVLines,key=lambda tup:(-tup[0],tup[1])) if 0<=abs(ls[0]-hLs[2])<=tol and 0<=ls[1]-hLs[1]<=tol]
                            tmpY1=[ls for ls in sorted(lstHLines,key=lambda tup:(-tup[1],tup[0])) if 0<=ls[0]-vLs[0]<=tol and 0<=ls[1]-vLs[3]<=tol]
                            tmpY2=[ls for ls in sorted(lstHLines,key=lambda tup:(-tup[1],tup[0])) if 0<=ls[0]-vLs[0]<=tol and 0<=abs(ls[1]-vLs[3])<=tol]
                            if tmpX1:
                                pt2_x = tmpX1[0][0]
                            elif tmpX2:
                                pt2_x = hLs[2]
                            if tmpY1:
                                pt2_y = tmpY1[0][1]
                            elif tmpY2:
                                pt2_y=vLs[3]


                            lstMainBbox.append((pt1_x,pt1_y,pt2_x,pt2_y))
                            brk=True
                            break
                        except:
                            print('')
                if brk:
                    break
            if not brk:
                flag=False
        diHLines={}
        diVLines={}
        for bbx in lstMainBbox:
            for hLs in lstHLines:
                if bbx[0] <= hLs[0]<hLs[2]<= bbx[2] and bbx[1] <= hLs[1]<= bbx[3]:
                    diHLines.setdefault(bbx,[]).append(hLs)

            for vLs in lstVLines:
                if bbx[0] <= vLs[0] <= bbx[2] and bbx[1] <= vLs[1] < vLs[3] <= bbx[3]:
                    diVLines.setdefault(bbx, []).append(vLs)

        diHLinesNew=reshpDiLines(diHLines, 1, 0)
        diVLinesNew=reshpDiLines(diVLines, 0, 1)
        diLines={}
        for bbx in lstMainBbox:
            diLines[bbx]=(diHLinesNew[bbx],diVLinesNew[bbx])
        return diLines

    def interConnectLines(lstVLines,lstHLines,tol=5):
        lstVLinesCp=[[list(ls) for ls in ln] for ln in copy.deepcopy(lstVLines) ]
        lstHLinesCp=[[list(ls) for ls in ln] for ln in copy.deepcopy(lstHLines) ]
        flag = True
        while (flag):
            brk=False
            for hLnIx, hLn in enumerate(copy.deepcopy(lstHLinesCp)):
                for hLsIx, hLs in enumerate(hLn):
                    for vLnIx, vLn in enumerate(copy.deepcopy(lstVLinesCp)):
                        for vLsIx, vLs in enumerate(vLn):
                            xStatic=vLs[0]
                            yStatic=hLs[1]
                            if vLs[3]<yStatic:
                                dif=yStatic-vLs[3]
                                if dif<=tol:
                                    lstVLinesCp[vLnIx][vLsIx][3]+=dif

                            elif yStatic<vLs[1]:
                                dif=vLs[1]-yStatic
                                if dif<=tol:
                                    lstVLinesCp[vLnIx][vLsIx][1] -= dif

                            if hLs[2]<xStatic:
                                dif=xStatic-hLs[2]
                                if dif<=tol:
                                    lstHLinesCp[hLnIx][hLsIx][2]+=dif
                                    brk = True
                                    break

                            elif xStatic<hLs[0]:
                                dif=hLs[0]-xStatic
                                if dif<=tol:
                                    lstHLinesCp[hLnIx][hLsIx][0] -= dif
                                    brk = True
                                    break

                        if brk:
                            break
                    if brk:
                        break
                if brk:
                    break
            if not brk:
                flag=False
        lstVLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstVLinesCp)]
        lstHLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstHLinesCp)]
        return lstVLines,lstHLines

    lstVLines = lstVLines  # [0::2]
    lstHLines = lstHLines  # [0::2]
    newLstVLines = intraConnectLines(lstVLines, 1, 3)
    newLstHLines = intraConnectLines(lstHLines, 0, 2)

    # debugLS(img, lstHLines, lstVLines)
    lstHLinesMrgd=mergeLs(newLstHLines, 2, 0)
    lstVLinesMrgd=mergeLs(newLstVLines, 3, 1)
    diLines=findTblMainBbox(lstHLinesMrgd,lstVLinesMrgd)
    for bbx,tupLines in list(diLines.items()):
        newLstVLines,newLstHLines=interConnectLines(tupLines[1][0::2], tupLines[0][0::2])
        diLines[bbx]=(newLstHLines,newLstVLines)
    return diLines


def extractTable(fNm,pgNo,pagesInFile):
    tmpDir=constants.tmpDir
    minLsLen=constants.tblMinLsLen
    justPgNo = utils.lJustPgNo(pgNo,pagesInFile)
    imgFNm = '{0}-{1}.png'.format(fNm, justPgNo)
    imgPath = constants.imageDir+fNm+'/'+imgFNm
    img = cv2.imread(imgPath)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    cv2.imwrite(tmpDir+'edges.jpg', edges)
    cv2.imwrite(tmpDir+'gray.jpg', gray)
    lstHLines = getLSgmt(edges, minLsLen, 'H')
    lstVLines = getLSgmt(edges.transpose(), minLsLen, 'V')
    diTbls=findAllTbls(img,lstHLines, lstVLines)
    diTblsNew={}
    for tbl,tupLines in diTbls.items():
        lstHLines,lstVLines=tupLines[0],tupLines[1]
        debugLS(img, lstHLines, lstVLines)
        imgShp = edges.shape
        lstIntersections = captureIntersections(lstHLines, lstVLines)
        imgPts = copy.deepcopy(img)
        debugPoints(imgPts, lstIntersections)
        diBbox = getBBox(lstIntersections, lstHLines, lstVLines)
        debugBbox(img, diBbox)
        lol = bboxesToTable(diBbox)
        htmTbl,diSpanInfo = htmlTable(lol)
        diTblsNew[tbl]={'diBbox':diBbox,'lol':lol,'htmTbl':htmTbl,'diSpanInfo':diSpanInfo,'imgShp':imgShp}
    return diTblsNew





if __name__=='__main__':
    # temp()
    # exit(0)
    # fNm = 'UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059_91-95'
    fNm = 'sample'
    pageNo = "1"
    minLLen=14
    img = cv2.imread(r'../output/{0}-{1}.png'.format(fNm,pageNo))

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray,50,150,apertureSize = 3)

    cv2.imwrite('edges-50-150.jpg',edges)
    cv2.imwrite('gray-50.jpg',gray)
    lstHLines=getLSgmt(edges,minLLen,'H')
    lstVLines=getLSgmt(edges.transpose(),minLLen,'V')
    lstHLines, lstVLines=clnLS(lstHLines,lstVLines)
    debugLS(img,lstHLines, lstVLines)
    imgShp=edges.shape

    lstIntersections=captureIntersections(lstHLines,lstVLines)
    imgPts = copy.deepcopy(img)
    debugPoints(imgPts,lstIntersections)

    diBbox=getBBox(lstIntersections,lstHLines,lstVLines)
    debugBbox(img,diBbox)
    diPdfBbox=imgBboxToPdfBboxMult(diBbox, imgShp[0])
    xmlFNm = r'{0}.xml'.format(fNm)
    tree = pdfmin.readXml(xmlFNm)
    diTags = pdfmin.queryXml(tree, pdfmin.diSel['textline'].format(int(pageNo)))
    textInsideBbox=getTextInsideBboxMult(diPdfBbox.values(),diTags)
    lol=bboxesToTable(diBbox)
    htmTbl=htmlTable(lol)
    print(htmTbl)
    print("Done")
