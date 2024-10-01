import cv2
import numpy as np
import copy
# from bin import pdfminer_testing as pdfmin
from collections import defaultdict
from collections import OrderedDict
from itertools import groupby
from bin import utils
from bin import constants
from bin import pdfExtractionUtils as pdfutil
import lxml.html
import os
import re
from datetime import datetime
import math
import traceback
def getLSgmt(edges, minLsLen, type='H'):
    def iterativeMethod(edges, minLsLen, type):
        lstVLines = []
        for idxListCell, listCell in enumerate(edges):
            if not any(listCell):
                # lstVLines.append([])
                continue
            lstLineSeg = []
            start = 0
            end = 0
            for cellIdx, cellVal in enumerate(listCell):
                if cellVal and not start:
                    start = cellIdx
                if cellVal:
                    end = cellIdx
                if not cellVal and start:
                    if end - start >= minLsLen:
                        if type == 'H':
                            lstLineSeg.append((start, idxListCell, end, idxListCell))
                        elif type == 'V':
                            lstLineSeg.append((idxListCell, start, idxListCell, end))
                    start = 0
                    end = 0
            if lstLineSeg:
                lstVLines.append(lstLineSeg)
        return lstVLines

    def regexMethod(edges, minLsLen, type):
        def func(arr, static,minLsLen,type):
            lstLsStr=re.findall('(?:\d+(?:,|$))+', ','.join([str(ix) if elm else 'False' for ix, elm in enumerate(arr)]))
            lstLs=[]
            for lsStr in lstLsStr:
                lsInt=list(map(int,re.sub(',$', '', lsStr).split(',')))
                lsLow =lsInt[0]
                lsUp=lsInt[-1]
                if lsUp-lsLow<minLsLen:
                    continue
                if type == 'H':
                    lstLs.append((lsLow,static,lsUp,static))
                elif type == 'V':
                    lstLs.append((static,lsLow,static,lsUp))
            if lstLs:
                return lstLs


        # edgesFlt=copy.deepcopy(edges[np.apply_along_axis(any, 1, edges)])

        return list(filter(None,[func(edges[ix], ix,minLsLen,type) for ix in range(edges.shape[0])]))
    res=iterativeMethod(edges, minLsLen, type)

    return res
    # return regexMethod(edges, minLsLen, type)


def captureIntersections(lstHLines, lstVLines):
    lstIntersections = []
    for lstHLine in lstHLines:
        for hLSeg in lstHLine:
            xRange = (hLSeg[0], hLSeg[2])
            yStatic = hLSeg[1]
            for lstVLine in lstVLines:
                for vLSeg in lstVLine:
                    isXInRange, isYInRange = False, False
                    yRange = (vLSeg[1], vLSeg[3])
                    xStatic = vLSeg[0]
                    if xRange[0] <= xStatic <= xRange[1]:
                        isXInRange = True
                    if yRange[0] <= yStatic <= yRange[1]:
                        isYInRange = True
                    if isXInRange and isYInRange:
                        lstIntersections.append((xStatic, yStatic))
    return list(set(lstIntersections))


def getBBox(lstIntersections, lstHLines, lstVLines):
    diHLines = {lst[0][1]: lst for lst in lstHLines}
    diVLines = {lst[0][0]: lst for lst in lstVLines}
    lstIntersections = sorted(lstIntersections, key=lambda tup: (tup[1], tup[0]))
    diBbox = {}
    for idx, pt in enumerate(lstIntersections[0:-1]):
        pt_right = sorted([p for p in lstIntersections if p[1] == pt[1] and p[0] > pt[0]], key=lambda tup: tup[0])
        pt_btm = sorted([p for p in lstIntersections if p[0] == pt[0] and p[1] > pt[1]], key=lambda tup: tup[0])
        if not pt_right or not pt_btm:
            continue
        for idx1, pt1 in enumerate(lstIntersections[idx + 1:]):
            if pt1[0] == pt[0] or pt1[1] == pt[1]:
                continue
            if (pt1[0], pt[1]) in pt_right and (pt[0], pt1[1]) in pt_btm:
                pt1ToPtLsUp = (pt1[0], pt[1], pt1[0], pt1[1])
                pt1ToPtLsleft = (pt[0], pt1[1], pt1[0], pt1[1])

                ptToPt1LsBtm = (pt[0], pt[1], pt[0], pt1[1])
                ptToPt1LsRight = (pt[0], pt[1], pt1[0], pt[1])
                if pt not in diBbox:
                    if not (any([vLs for vLs in diVLines[pt1[0]] if
                                 vLs[1] <= pt1ToPtLsUp[1] < pt1ToPtLsUp[3] <= vLs[3]]) and any(
                        [hLs for hLs in diHLines[pt1[1]] if
                         hLs[0] <= pt1ToPtLsleft[0] < pt1ToPtLsleft[2] <= hLs[2]])):
                        continue
                    if not (any([vLs for vLs in diVLines[pt[0]] if
                                 vLs[1] <= ptToPt1LsBtm[1] < ptToPt1LsBtm[3] <= vLs[3]]) and any(
                        [hLs for hLs in diHLines[pt[1]] if
                         hLs[0] <= ptToPt1LsRight[0] < ptToPt1LsRight[2] <= hLs[2]])):
                        continue
                    diBbox[pt] = pt1

    return diBbox


def debugLS(img, lstHLines, lstVLines, imgFNm, outDir=constants.debugTblPath, outFNm=constants.debugLsFNm,outFExt=constants.tblDebugExt):
    if not constants.debugTblImg:
        return
    img=copy.deepcopy(img)
    outPath = outDir.format(imgFNm)
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    completeOutFPath = outPath + outFNm + outFExt
    try:
        for lstHLine in lstHLines:
            for lSeg in lstHLine:
                cv2.line(img, (lSeg[0], lSeg[1]), (lSeg[2], lSeg[3]), (0, 255, 0), 1)
        for lstVLine in lstVLines:
            for lSeg in lstVLine:
                cv2.line(img, (lSeg[0], lSeg[1]), (lSeg[2], lSeg[3]), (0, 255, 0), 1)
    except:
        print('temp')
    cv2.imwrite(completeOutFPath, img)

def convertBbxtoLn(bbx):
    return ((bbx[0], bbx[1], bbx[2], bbx[1]), (bbx[0], bbx[3], bbx[2], bbx[3]),(bbx[0], bbx[1], bbx[0], bbx[3]), (bbx[2], bbx[1], bbx[2], bbx[3]))

def debugBboxAsRect(bbx,img,imgFNm):
    tupLn=convertBbxtoLn(bbx)
    lstHLines = [[tupLn[0], tupLn[1]]]
    lstVLines=  [[tupLn[2], tupLn[3]]]
    debugLS(img, lstHLines, lstVLines, imgFNm)

def debugPoints(img, lstPts, imgFNm, outDir=constants.debugTblPath, outFNm=constants.debugIsectPtsFNm,
                outFExt=constants.tblDebugExt,text=True):
    img=copy.deepcopy(img)
    if not constants.debugTblImg:
        return
    outPath = outDir.format(imgFNm)
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    completeOutFPath = outPath + outFNm + outFExt
    for pt in lstPts:
        if text:
            cv2.putText(img, "Pt{}".format(pt), pt, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        else:
            cv2.putText(img, ".", pt, cv2.FONT_HERSHEY_SIMPLEX, 0.07, (0, 0, 255), 1)
    cv2.imwrite(completeOutFPath, img)


def debugBbox(img, diBBox, imgFNm, outDir=constants.debugTblPath, outFNm=constants.debugPtsFNm,
              outFExt=constants.tblDebugExt,text=True,iter=False):
    if not constants.debugTblImg:
        return
    img=copy.deepcopy(img)
    outPath = outDir.format(imgFNm)
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    completeOutFPath = outPath + outFNm + outFExt
    for ul, lr in diBBox.items():
        if text:
            cv2.putText(img, "UL{}".format(str(ul)), ul, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
            cv2.putText(img, "LR{}".format(str(lr)), lr, cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
            if iter:
                cv2.imwrite(completeOutFPath, img)
        else:
            cv2.putText(img, ".", ul, cv2.FONT_HERSHEY_SIMPLEX, 0.07, (0, 0, 255), 1)
            cv2.putText(img, ".", lr, cv2.FONT_HERSHEY_SIMPLEX, 0.07, (255, 0, 0), 1)
            if iter:
                cv2.imwrite(completeOutFPath, img)
    if not iter:
        cv2.imwrite(completeOutFPath, img)


def debugImage(img, imgFNm, outDir=constants.debugTblPath, outFNm=constants.debugImgFNm, outFExt=constants.tblDebugExt):
    if not constants.debugTblImg:
        return
    img=copy.deepcopy(img)
    outPath = outDir.format(imgFNm)
    if not os.path.exists(outPath):
        os.makedirs(outPath)
    completeOutFPath = outPath + outFNm + outFExt
    cv2.imwrite(completeOutFPath, img)


def imgBboxToPdfBboxMult(diBBox, maxY):
    diPdfBbox = {}
    for ul, lr in diBBox.items():
        k = ul + lr
        diPdfBbox[k] = pdfutil.imgBboxToPdfBbox(ul, lr, maxY)
    return diPdfBbox


def getTextInsideBboxMult(lstPdfBbox, diTags):
    diBboxText = {}
    for pdfBbox in lstPdfBbox:
        diBboxText[pdfBbox] = pdfutil.getTextInsideBbox(diTags, pdfBbox)
    return diBboxText



def bboxesToTable(di,diComp):

    def partitioning(di,diComp):
        diNew={}
        for ulComp, lrComp in diComp.items():
            for ul, lr in di.items():
                if ul[0]<=ulComp[0]<lrComp[0]<=lr[0] and ul[1]<=ulComp[1]<lrComp[1]<=lr[1]:
                    diNew[ulComp + lrComp]=ul + lr
        return diNew


    def finalShape(diNew):
        rows = []
        for y in sorted(list(set([k[1] for k in diNew.keys()]))):
            row = []
            for c, p in sorted(diNew.items(), key=lambda tup: (tup[0][1], tup[0][0])):
                if c[1] == y:
                    row.append(p)
            rows.append(row)
        return rows

    diNew=partitioning(di, diComp)
    return finalShape(diNew)

def bboxesToTableOld(di):
    def desolveOvrlapCk(ck, ck1, ixLow, ixUp, ixCmnLow, ixCmnUp, dslTyp):
        cmnLow, cmnUp = ck[ixCmnLow], ck[ixCmnUp]
        ckLow, ckUp, ck1Low, ck1Up = ck[ixLow], ck[ixUp], ck1[ixLow], ck1[ixUp]

        if ckLow == ck1Low:
            if dslTyp == 'hr':
                return [(cmnLow, ckLow, cmnUp, ckUp), (cmnLow, ckUp, cmnUp, ck1Up)]
            elif dslTyp == 'vr':
                return [(ckLow, cmnLow, ckUp, cmnUp), (ckUp, cmnLow, ck1Up, cmnUp)]
        elif ckLow < ck1Low:
            if dslTyp == 'hr':
                return [(cmnLow, ckLow, cmnUp, ck1Low), (cmnLow, ck1Low, cmnUp, ckUp), (cmnLow, ckUp, cmnUp, ck1Up)]
            elif dslTyp == 'vr':
                return [(ckLow, cmnLow, ck1Low, cmnUp), (ck1Low, cmnLow, ckUp, cmnUp), (ckUp, cmnLow, ck1Up, cmnUp)]

    def getNonOvrLapCk(chunk, lstDslvd, dslType):
        if dslType == 'hr':
            ixLow, ixUp = 1, 3
            ixCmnLow, ixCmnUp = 0, 2
        elif dslType == 'vr':
            ixLow, ixUp = 0, 2
            ixCmnLow, ixCmnUp = 1, 3
        lstFlat = [ck for sbLst in [di.keys() for di in lstDslvd] for ck in sbLst]
        flag = True
        while (flag):
            lstSrt = sorted(list(set(lstFlat)), key=lambda tup: (tup[ixLow], tup[ixUp] - tup[ixLow]))
            for ix in range(len(lstSrt) - 1):
                ck, ck1 = lstSrt[ix], lstSrt[ix + 1]
                if not (ck[ixLow] <= ck1[ixLow] < ck[ixUp]):
                    continue
                lstDsl = desolveOvrlapCk(ck, ck1, ixLow, ixUp, ixCmnLow, ixCmnUp, dslType)
                if lstDsl:
                    lstFlat.remove(ck)
                    lstFlat.remove(ck1)
                    lstFlat.extend(lstDsl)
                    break

            else:
                flag = False
                diNonOLCk = {ck: chunk for ck in set(lstSrt)}
        return diNonOLCk

    def desolveVr(ck, ck1, bbox, bbox1):
        tDi, tDi1 = {}, {}
        ck_p1_x, ck_p1_y, ck_p2_x, ck_p2_y = ck[0], ck[1], ck[2], ck[3]
        ck1_p1_x, ck1_p1_y, ck1_p2_x, ck1_p2_y = ck1[0], ck1[1], ck1[2], ck1[3]
        ckLow, ckUp = ck_p1_x, ck_p2_x
        ck1Low, ck1Up = ck1_p1_x, ck1_p2_x

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


        elif ckLow < ck1Up < ckUp and ckLow > ck1Low:
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

        elif ckLow < ck1Low < ckUp and ckUp < ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p1_y): bbox,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p2_y): bbox1,
                    (ck1_p1_x, ck_p2_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Low < ckUp and ckUp == ck1Up:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p1_y): bbox,
                   (ck_p1_x, ck1_p1_y, ck_p2_x, ck_p2_y): bbox}


        elif ckLow < ck1Up < ckUp and ckLow > ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p2_y): bbox,
                   (ck_p1_x, ck1_p2_y, ck_p2_x, ck_p2_y): bbox}
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p1_y): bbox1,
                    (ck1_p1_x, ck_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ckLow < ck1Up < ckUp and ckLow == ck1Low:
            tDi = {(ck_p1_x, ck_p1_y, ck_p2_x, ck1_p2_y): bbox,
                   (ck_p1_x, ck1_p2_y, ck_p2_x, ck_p2_y): bbox}

        elif ck1Low < ckUp < ck1Up and ck1Low == ckLow:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p2_y): bbox1,
                    (ck1_p1_x, ck_p2_y, ck1_p2_x, ck1_p2_y): bbox1}

        elif ck1Low < ckLow < ck1Up and ck1Up == ckUp:
            tDi1 = {(ck1_p1_x, ck1_p1_y, ck1_p2_x, ck_p1_y): bbox1,
                    (ck1_p1_x, ck_p1_y, ck1_p2_x, ck1_p2_y): bbox1}

        return tDi, tDi1

    def desolveChunks(chunks, bbox, chunks1, bbox1, desolveType):
        chunksCp = copy.deepcopy(chunks)
        diP, di1P, delCk, delCk1 = {}, {}, [], []

        for ck1 in sortLstBtmRight(chunks1):
            di, tDelCk, lstTdi1 = {}, [], []
            for ck in sortLstBtmRight(chunks):
                if desolveType == "hr":
                    if not getDiLeftToRight(ck, {ck1: ck1}):
                        continue
                    tDi, tDi1 = desolveHr(ck, ck1, bbox, bbox1)

                elif desolveType == "vr":
                    if not getDiTopToBtm(ck, {ck1: ck1}):
                        continue
                    tDi, tDi1 = desolveVr(ck, ck1, bbox, bbox1)

                di.update(tDi)
                if tDi:
                    tDelCk.append(ck)

                if tDi1 and tDi1 not in lstTdi1:
                    lstTdi1.append(tDi1)

            if di:
                oldChunks = {c: bbox for c in chunks}
                for c in tDelCk:
                    oldChunks.pop(c)
                    if c in chunksCp:
                        delCk.append(c)
                oldChunks.update(di)
                chunks = oldChunks.keys()
            if lstTdi1:
                di1P.update(getNonOvrLapCk(bbox1, lstTdi1, desolveType))
                delCk1.append(ck1)
        if set(chunks) != set(chunksCp):
            diP = {c: bbox for c in chunks}
        return diP, di1P, delCk + delCk1

    def reverseDi(di):
        diReverse = {}
        for k, v in di.items():
            diReverse.setdefault(v, []).append(k)
        return diReverse

    def getDiTopToBtm(bbox, di):
        diReverse = reverseDi(di)

        bboxLow, bboxUp = bbox[0], bbox[2]
        bboxOthUp = bbox[3]
        diTopToBtm = {}
        for k, v in diReverse.items():
            kLow, kUp = k[0], k[2]
            kOthLow = k[1]
            if ((kLow <= bboxLow <= kUp) or (kLow <= bboxUp <= kUp) or (
                    (bboxLow <= kLow <= bboxUp) and (bboxLow <= kUp <= bboxUp))) and (
                    (bboxLow != kUp) and (bboxUp != kLow)) and not (
                    (bboxLow, bboxUp) == (kLow, kUp)) and bboxOthUp <= kOthLow:
                diTopToBtm[k] = v

        return diTopToBtm

    def getDiLeftToRight(bbox, di):
        diReverse = reverseDi(di)

        bboxLow, bboxUp = bbox[1], bbox[3]
        bboxOthUp = bbox[2]
        diLeftToRight = {}
        for k, v in diReverse.items():
            kLow, kUp = k[1], k[3]
            kOthLow = k[0]
            if ((kLow <= bboxLow <= kUp) or (kLow <= bboxUp <= kUp) or (
                    (bboxLow <= kLow <= bboxUp) and (bboxLow <= kUp <= bboxUp))) and (
                    (bboxLow != kUp) and (bboxUp != kLow)) and not (
                    (bboxLow, bboxUp) == (kLow, kUp)) and bboxOthUp <= kOthLow:
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

    diNew = {ul + lr: ul + lr for ul, lr in di.items()}

    lstBboxSrt = sortLstBtmRight(diNew.keys())
    for bbox in list(lstBboxSrt):
        diTopToBtm = sortDiBtmRight(getDiTopToBtm(bbox, diNew))
        for bbx, lstChunks in diTopToBtm.items():
            di1, di2, delK = desolveChunks(reverseDi(diNew)[bbox], bbox, lstChunks, bbx, "vr")
            for elm in set(delK):
                diNew.pop(elm)
            diNew.update(di1)
            diNew.update(di2)

        diLeftToRight = sortDiBtmRight(getDiLeftToRight(bbox, diNew))
        for bbx, lstChunks in diLeftToRight.items():
            di1, di2, delK = desolveChunks(reverseDi(diNew)[bbox], bbox, lstChunks, bbx, "hr")
            for elm in set(delK):
                diNew.pop(elm)
            diNew.update(di1)
            diNew.update(di2)
    # print(diNew)
    return finalShape(diNew)


def htmlTable(lol,pgNo):
    diBboxGrp = {}
    for row in lol:
        tDi = {}
        for bbox in row:
            tDi.setdefault(bbox, []).append(bbox)
        for k, v in tDi.items():
            diBboxGrp.setdefault(k, []).append(v)
    diSpanInfo = {}
    for k, v in diBboxGrp.items():
        colSpan = len(v[0])
        rowSpan = len(v)
        diSpanInfo.setdefault(k, {})['cSpan'] = colSpan
        diSpanInfo.setdefault(k, {})['rSpan'] = rowSpan

    srtLstBbx = sorted(diBboxGrp.keys(), key=lambda tup: (tup[1], tup[0]))
    grpd = groupby(srtLstBbx, lambda tup: tup[1])
    theadCSpan=len(lol[0]) if lol else 1
    tblString = '''<table border="1"><thead><tr><th colspan="{0}">Page: {1}</th></tr></thead><tbody>'''.format(theadCSpan,pgNo)
    for _, g in grpd:
        trString = '''<tr style="height: 15.0pt;">'''
        for elm in g:
            tdString = r'''<td rowspan="{0}" colspan="{1}">{{{2}}}</td>'''
            rSpan = diSpanInfo[elm]['rSpan']
            cSpan = diSpanInfo[elm]['cSpan']
            tdString = tdString.format(rSpan, cSpan, elm)
            trString += tdString
        trString += '''</tr>'''
        tblString += trString
    tblString += '''</tbody></table>'''
    return tblString, diSpanInfo


def temp():
    lstDi = [{(0, 0): (5, 3), (5, 0): (10, 5), (10, 0): (15, 3), (0, 3): (3, 5), (3, 3): (5, 5), (10, 3): (15, 5)},
             {(0, 0): (4, 2), (0, 2): (2, 4), (2, 2): (4, 4), (0, 4): (4, 8), (4, 0): (8, 4), (4, 4): (6, 5),
              (6, 4): (8, 5), (4, 5): (8, 7), (4, 7): (8, 8), (8, 0): (12, 2), (8, 2): (12, 4),
              (8, 4): (10, 5), (10, 4): (12, 5), (8, 5): (10, 6), (10, 5): (12, 6), (8, 6): (10, 7), (10, 6): (12, 7),
              (8, 7): (10, 8), (10, 7): (12, 8)
              },
             {(0, 0): (4, 2), (0, 2): (2, 4), (2, 2): (4, 4), (0, 4): (4, 8), (4, 0): (8, 4), (4, 4): (6, 5),
              (6, 4): (8, 5), (4, 5): (8, 7), (4, 7): (8, 8), (8, 0): (12, 2), (8, 2): (12, 4),
              (8, 4): (10, 6), (10, 4): (12, 5), (10, 5): (12, 6), (8, 6): (10, 7), (10, 6): (12, 8),
              (8, 7): (10, 8)
              },
             {(0, 0): (4, 2), (0, 2): (2, 4), (2, 2): (4, 4), (0, 4): (4, 8), (4, 0): (8, 4), (4, 4): (6, 5),
              (6, 4): (8, 5), (4, 5): (8, 7), (4, 7): (8, 8), (8, 0): (12, 2), (8, 2): (12, 4),
              (8, 4): (10, 6), (10, 4): (12, 5), (10, 5): (12, 6), (8, 6): (10, 7), (10, 6): (11, 8), (11, 6): (12, 8),
              (8, 7): (10, 8)
              },
             {(0, 4): (4, 8), (4, 4): (6, 5), (6, 4): (8, 6), (8, 4): (10, 7), (4, 5): (6, 7), (6, 6): (8, 7),
              (4, 7): (8, 8), (8, 7): (10, 8)},
             {(10, 4): (18, 8), (10, 8): (12, 9), (12, 8): (18, 9), (10, 9): (14, 10), (14, 9): (18, 10),
              (10, 10): (16, 11), (16, 10): (18, 11), (10, 11): (12, 12), (12, 11): (14, 12), (14, 11): (18, 12)}]
    for di in lstDi[-1:]:
        lol = bboxesToTable(di)
        htm, diSpanInfo = htmlTable(lol)
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

    newEdges = None
    _, cnts, hrchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    hrchy = hrchy[0]
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





def findAllTbls(img, diTagsPg, edges, imgDir, imgFNm, minLsLen,tblBbox=None):
    def intraConnectLines(lstLines, ixLow, ixUp,tol=constants.tblTol,intraCLsLen=constants.intraCLsLen):
        diLs={}
        for lnIx, ln in enumerate(lstLines): #loops over all lines
            flag = True
            lsIx=0
            while (flag):
                '''sorts line by the low index. i.e for hLs (1,4,10,4) ixLow would be 0 and ixUp would be 2'''
                lnSort = sorted((ln), key=lambda tup: (tup[ixLow],(tup[ixUp]-tup[ixLow])))
                lstTmp=[]
                for ix,ls in list(enumerate(lnSort))[lsIx:-1]:
                    ls1 = lnSort[ix + 1] #takes two successive ls (line segment)
                    lsLen,ls1Len=ls[ixUp]+1-ls[ixLow],ls1[ixUp]+1-ls1[ixLow]
                    if lsLen>intraCLsLen and ls1Len>intraCLsLen and (0 < ls1[ixLow] - ls[ixUp] < tol or ls[ixLow]<=ls1[ixLow]<=ls[ixUp]): #checks if the distance between them is less than
                        lstTmp.append(ls)
                    else:
                        lstTmp.append(ls)
                        lsLow=min([ls[ixLow] for ls in lstTmp])
                        lsUp=max([ls[ixUp] for ls in lstTmp])
                        lsStatic=lstTmp[0][ixLow+1]
                        if ixLow==0:
                            keyTup=(lsLow,lsStatic,lsUp,lsStatic)
                        else:
                            keyTup = (lsStatic,lsLow,lsStatic,lsUp)
                        diLs[keyTup]=lstTmp
                        lstTmp=[]
                        lsIx=ix+1
                        break
                else:
                    lstTmp.append(lnSort[-1])
                    lsLow = min([ls[ixLow] for ls in lstTmp])
                    lsUp = max([ls[ixUp] for ls in lstTmp])
                    lsStatic = lstTmp[0][ixLow + 1]
                    if ixLow == 0:
                        keyTup = (lsLow, lsStatic, lsUp, lsStatic)
                    else:
                        keyTup = (lsStatic, lsLow, lsStatic, lsUp)
                    diLs[keyTup] = lstTmp
                    flag = False

        return diLs


    def reshpMrgdLs(lstMrgdLs, ixLow, ixSrt):
        lstLines = []
        steps = sorted(list(set([ls[ixLow] for ls in lstMrgdLs])))
        for ix, step in enumerate(steps):
            lstStep = []
            for mrgdLs in lstMrgdLs:
                if mrgdLs[ixLow] == step:
                    lstStep.append(mrgdLs)
            lstLines.append(sorted(lstStep, key=lambda tup: tup[ixSrt]))
        return lstLines
    def completeBbox(hLs,vLs,tol):
        xStatic = vLs[0]  # x value is static for any vLs
        yStatic = hLs[1]  # y value is static for any hLs
        xDif, xDifAbs = hLs[0] - xStatic, abs(hLs[0] - xStatic)  # dif and absolute dif between hls lower x value and xStatic
        xDif2, xDifAbs2 = xStatic - hLs[2], abs(xStatic - hLs[2])  # dif and absolute dif between hls lower x value and xStatic
        yDif, yDifAbs = vLs[1] - yStatic, abs(vLs[1] - yStatic)  # dif and absolute dif between vls lower y value and yStatic
        yDif2, yDifAbs2 = yStatic - vLs[3], abs(yStatic - vLs[3])  # dif and absolute dif between vls lower y value and yStatic
        if ((0 <= xDif <= tol and 0 <= yDif <= tol) or (
                0 <= xDifAbs <= tol and 0 <= yDifAbs <= tol)):  # if both xDif and yDif are within tolerance or both xDifAbs and yDifAbs are within tolerance
            if not (0 <= xDif <= tol and 0 <= yDif <= tol):
                ''' if both xDifAbs and yDifAbs are within tolerance , take lower x of hls and yStatic'''
                pt_x, pt_y = hLs[0], yStatic
            else:
                '''if both xDif and yDif are within tolerance, take xStatic and yStatic'''
                pt_x, pt_y = xStatic, yStatic
            return (pt_x,pt_y,hLs[2],vLs[3])
        elif ((0 <= xDif2 <= tol and 0 <= yDif <= tol) or (
                0 <= xDifAbs2 <= tol and 0 <= yDifAbs <= tol)):  # if both xDif and yDif are within tolerance or both xDifAbs and yDifAbs are within tolerance
            if not (0 <= xDif2 <= tol and 0 <= yDif <= tol):
                ''' if both xDifAbs and yDifAbs are within tolerance , take lower x of hls and yStatic'''
                pt_x, pt_y = hLs[2], yStatic
            else:
                '''if both xDif and yDif are within tolerance, take xStatic and yStatic'''
                pt_x, pt_y = xStatic, yStatic
            return (hLs[0],pt_y,pt_x,vLs[3])
        elif ((0 <= xDif2 <= tol and 0 <= yDif2 <= tol) or (
                0 <= xDifAbs2 <= tol and 0 <= yDifAbs2 <= tol)):  # if both xDif and yDif are within tolerance or both xDifAbs and yDifAbs are within tolerance
            if not (0 <= xDif2 <= tol and 0 <= yDif2 <= tol):
                ''' if both xDifAbs and yDifAbs are within tolerance , take lower x of hls and yStatic'''
                pt_x, pt_y = hLs[2], yStatic
            else:
                '''if both xDif and yDif are within tolerance, take xStatic and yStatic'''
                pt_x, pt_y = xStatic, yStatic
            return (hLs[0],vLs[1],pt_x,pt_y)

        elif ((0 <= xDif <= tol and 0 <= yDif2 <= tol) or (
                0 <= xDifAbs <= tol and 0 <= yDifAbs2 <= tol)):  # if both xDif and yDif are within tolerance or both xDifAbs and yDifAbs are within tolerance
            if not (0 <= xDif <= tol and 0 <= yDif2 <= tol):
                ''' if both xDifAbs and yDifAbs are within tolerance , take lower x of hls and yStatic'''
                pt_x, pt_y = hLs[0], yStatic
            else:
                '''if both xDif and yDif are within tolerance, take xStatic and yStatic'''
                pt_x, pt_y = xStatic, yStatic
            return (pt_x,vLs[1],hLs[2],pt_y)

    def overlappingBbox(bbx1,bbx2):
        overlap=False
        if (bbx1 == bbx2):
            overlap=True #both bbx1 and bbx2 are equal
        elif (bbx2[0] <= bbx1[0] < bbx1[2] <= bbx2[2]) and (bbx2[1] <=bbx1[1] < bbx1[3] <= bbx2[3]):#bbx1 is contained in bbx2
            overlap=True
        elif (bbx1[0] <= bbx2[0] < bbx2[2] <= bbx1[2]) and (bbx1[1] <=bbx2[1] < bbx2[3] <= bbx1[3]):#bbx2 is contained in bbx1
            overlap=True
        elif (bbx2[1]<=bbx1[1]<bbx2[3] or bbx2[1]<bbx1[3]<=bbx2[3]) and (bbx1[0]<=bbx2[0]<bbx1[2] or bbx1[0]<bbx2[2]<=bbx1[2]):
            overlap=True
        return overlap

    def distinctTables(lst):
        lstDistinct = []
        ignore = []
        for ix, tup in enumerate(lst):
            if tup in ignore:
                continue
            for ix1, tup1 in enumerate(lst):
                if ix == ix1:
                    continue
                if ((tup1[0] <= tup[0] <= tup1[2] or tup1[0] <= tup[2] <= tup1[2]) and (
                        tup1[1] <= tup[1] <= tup1[3] or tup1[1] <= tup[3] <= tup1[3])):
                    if (tup[2] - tup[0]) * (tup[3] - tup[1]) < (tup1[2] - tup1[0]) * (tup1[3] - tup1[1]):
                        break
                    elif (tup[2] - tup[0]) * (tup[3] - tup[1]) == (tup1[2] - tup1[0]) * (tup1[3] - tup1[1]):
                        ignore.append(tup1)
            else:
                lstDistinct.append(tup)
        return lstDistinct
    def findTblMainBbox(lstHLines, lstVLines, tol=constants.tblTol):
        '''this function detects all tables on a page'''
        lstMainBbox = []
        hLsCovered = []
        lstCompletedMainBox=[]
        flag = True
        while (flag):
            brk = False
            for hLs in lstHLines:
                '''loops over all hls from topleft to lower right
                and tries to locate leftmost vls with respect
                to any particular hls. If it finds one then it determines if there
                exist corresponding bottommost hls and rightmost vls and if found then
                together these four ls (two hls and two vls) define a particular table'''
                if hLs in hLsCovered or any(
                        [bbx[0] <= hLs[0] <= bbx[2] and bbx[1] <= hLs[1] <= bbx[3] for bbx in lstMainBbox]):
                    '''continues if an hls is already a exhausted (could not become a part of a table) or a part of already identified table'''
                    if constants.debugTblMainBbox:
                        print('hLs {} is either is captured or exhausted'.format(hLs))
                    continue
                lenLstVLines = len(lstVLines)
                for ix, vLs in enumerate(lstVLines):
                    if all([not(tup[0]<=hLs[0]<hLs[2]<=tup[2] and tup[1]<=vLs[1]<vLs[3]<=tup[3]) for tup in lstCompletedMainBox]):
                        completedBbox=completeBbox(hLs,vLs,tol)
                        if completedBbox  and (completedBbox[2] - completedBbox[0] >= constants.minTblOutBorder and completedBbox[3] - completedBbox[1] >= constants.minTblOutBorder) and not any([overlappingBbox(completedBbox,tup)  for tup in lstCompletedMainBox]):
                            lstCompletedMainBox.append(completedBbox)

                    if not (vLs[0] + tol >= hLs[0] and vLs[1] >= hLs[1]-tol) or any(
                            [bbx[0] <= vLs[0] <= bbx[2] and bbx[1] <= vLs[1] <= bbx[3] for bbx in lstMainBbox]):
                        '''continues if a vls is not within the tolerance of the hls under consideration or if vls is a part of already identified table'''
                        if constants.debugTblMainBbox:
                            print('vLs {} is either is captured or out of bbox'.format(vLs))
                        continue
                    xStatic = vLs[0] # x value is static for any vLs
                    yStatic = hLs[1] # y value is static for any hLs
                    xDif, xDifAbs = hLs[0] - xStatic, abs(hLs[0] - xStatic) # dif and absolute dif between hls lower x value and xStatic
                    yDif, yDifAbs = vLs[1] - yStatic, abs(vLs[1] - yStatic) # dif and absolute dif between vls lower y value and yStatic


                    if ((0 <= xDif <= tol and 0 <= yDif <= tol) or (0 <= xDifAbs <= tol and 0 <= yDifAbs <= tol)): # if both xDif and yDif are within tolerance or both xDifAbs and yDifAbs are within tolerance
                        if (0 <= xDif <= tol):
                            pt1_x=xStatic
                        elif (0 <= xDifAbs <= tol):
                            pt1_x=hLs[0]
                        if (0 <= yDif <= tol):
                            pt1_y=yStatic
                        elif (0 <= yDifAbs <= tol):
                            pt1_y=vLs[1]
                        '''point1_x and point1_y are determined. now point2_x and point2_y should be determined'''
                        tmpX1 = [ls for ls in sorted(lstVLines, key=lambda tup: (-tup[0], tup[1])) if #temporary list of rightmost vertical ls based on within tolerance signed dif
                                 0 <= ls[0] - hLs[2] <= tol and 0 <= ls[1] - yStatic <= tol]
                        tmpX2 = [ls for ls in sorted(lstVLines, key=lambda tup: (-tup[0], tup[1])) if #temporary list of rightmost vertical ls based on within tolerance absolute dif
                                 0 <= abs(ls[0] - hLs[2]) <= tol and 0 <= abs(ls[1] - yStatic) <= tol]
                        tmpY1 = [ls for ls in sorted(lstHLines, key=lambda tup: (-tup[1], tup[0])) if #temporary list of bottommost horizontal ls based on within tolerance signed dif
                                 0 <= ls[0] - xStatic <= tol and 0 <= ls[1] - vLs[3] <= tol]
                        tmpY2 = [ls for ls in sorted(lstHLines, key=lambda tup: (-tup[1], tup[0])) if #temporary list of bottommost horizontal ls based on within tolerance absolute dif
                                 0 <= abs(ls[0] - xStatic) <= tol and 0 <= abs(ls[1] - vLs[3]) <= tol]
                        pt2_x, pt2_y = None, None
                        if tmpX1:
                            '''if signed dif criterion results a non empty list of vls
                            then the first item of the list is considered for setting pt2_x'''
                            pt2_x = tmpX1[0][0]
                        elif tmpX2:
                            '''else if absolute dif criterion results a non empty list of vls
                            then the first item of the list is considered for setting pt2_x'''
                            pt2_x = hLs[2]
                        if tmpY1:
                            '''if signed dif criterion results a non empty list of hls
                            then the first item of the list is considered for setting pt2_y'''
                            pt2_y = tmpY1[0][1]
                        elif tmpY2:
                            '''else if absolute dif criterion results a non empty list of hls
                            then the first item of the list is considered for setting pt2_y'''
                            pt2_y = vLs[3]

                        if not (pt2_x and pt2_y):
                            '''continue if both pt2_x and pt2_y are not determined'''
                            if constants.debugTblMainBbox:
                                print('continuing for vLs {} ix {} remaining {}'.format(vLs, ix, lenLstVLines - ix))
                            continue
                        if pt2_x - pt1_x >= constants.minTblOutBorder and pt2_y - pt1_y >= constants.minTblOutBorder:
                            '''if pt2_x and pt2_y are determined and the identified table border is above the threshold then accept that table
                            and break from all for loops and continue to the next iteration of while loop'''
                            lstMainBbox.append((pt1_x, pt1_y, pt2_x, pt2_y))
                            brk = True
                            if constants.debugTblMainBbox:
                                print('breaking for hLs{}, vLs {} ix {} remaining {}'.format(hLs, vLs, ix,
                                                                                             lenLstVLines - ix))
                            break

                hLsCovered.append(hLs) #collect those hls which are not part of any table
                if brk:
                    break
            if not brk:
                flag = False
        if lstCompletedMainBox==lstMainBbox:
            lstMainBbox=lstMainBbox
        else:
            lstMainBbox=distinctTables(list(set(lstCompletedMainBox + lstMainBbox)))

        return lstMainBbox

    def getExtendedMainBbox(lstMainBbox,lstHLines, lstVLines,minLsLen):

        def extendMainBbox(mainBbox,lstMrgBktHLines, lstMrgBktVLines):
            tmpH = [tup[0] for hLnBkt in lstMrgBktHLines for tup in hLnBkt]
            tmpV = [tup[0] for vLnBkt in lstMrgBktVLines for tup in vLnBkt]

            xLft=min([mainBbox[0]]+[hLn[0][0] for hLn in tmpH if (mainBbox[0]<=hLn[0][0]<hLn[0][2]<=mainBbox[2] or hLn[0][0]<=mainBbox[0]<=hLn[0][2] or hLn[0][0]<=mainBbox[2]<=hLn[0][2])])
            xRht=max([mainBbox[2]]+[hLn[-1][2] for hLn in tmpH if (mainBbox[0]<=hLn[-1][0]<hLn[-1][2]<=mainBbox[2] or hLn[-1][0]<=mainBbox[0]<=hLn[-1][2] or hLn[-1][0]<=mainBbox[2]<=hLn[-1][2])])
            yTop=min([mainBbox[1]]+[vLn[0][1] for vLn in tmpV if (mainBbox[1]<=vLn[0][1]<vLn[0][3]<=mainBbox[3] or vLn[0][1]<=mainBbox[1]<=vLn[0][3] or vLn[0][1]<=mainBbox[3]<=vLn[0][3])])
            yBtm=max([mainBbox[3]]+[vLn[-1][3] for vLn in tmpV if (mainBbox[1]<=vLn[-1][1]<vLn[-1][3]<=mainBbox[3] or vLn[-1][1]<=mainBbox[1]<=vLn[-1][3] or vLn[-1][1]<=mainBbox[3]<=vLn[-1][3])])
            return (xLft,yTop,xRht,yBtm)

        lstExtendedMainBbox=[]
        for mainBbox in lstMainBbox:
            filtLstHLines, lstMrgBktHLines = filt(reshpMrgdLs(lstHLines, 1, 0), 1, minLsLen, returnMrgBkt=True, customFilt=True)
            filtLstVLines, lstMrgBktVLines = filt(reshpMrgdLs(lstVLines, 0, 1), 0, minLsLen, returnMrgBkt=True, customFilt=True)
            lstMrgBktHLinesSubset=[mrgBkt for mrgBkt in lstMrgBktHLines if all([mainBbox[1]<=tup[0][0][1]<=mainBbox[3] for tup in mrgBkt])]
            lstMrgBktVLinesSubset=[mrgBkt for mrgBkt in lstMrgBktVLines if all([mainBbox[0]<=tup[0][0][0]<=mainBbox[2] for tup in mrgBkt])]
            extendedMainBbox=extendMainBbox(mainBbox, lstMrgBktHLinesSubset, lstMrgBktVLinesSubset)
            lstExtendedMainBbox.append(extendedMainBbox)
        return lstExtendedMainBbox

    def interConnectLines(lstVLines, lstHLines,tol=constants.tblTol):
        lstVLinesCp = [[list(ls) for ls in ln] for ln in copy.deepcopy(lstVLines)]
        lstHLinesCp = [[list(ls) for ls in ln] for ln in copy.deepcopy(lstHLines)]
        flag = True
        while (flag):
            brk = False
            for hLnIx, hLn in enumerate(copy.deepcopy(lstHLinesCp)):
                for hLsIx, hLs in enumerate(hLn):
                    for vLnIx, vLn in enumerate(copy.deepcopy(lstVLinesCp)):
                        for vLsIx, vLs in enumerate(vLn):
                            xStatic = vLs[0]
                            yStatic = hLs[1]
                            if vLs[3] < yStatic:
                                dif = yStatic - vLs[3]
                                if dif <= tol:
                                    lstVLinesCp[vLnIx][vLsIx][3] += dif

                            elif yStatic < vLs[1]:
                                dif = vLs[1] - yStatic
                                if dif <= tol:
                                    lstVLinesCp[vLnIx][vLsIx][1] -= dif

                            if hLs[2] < xStatic:
                                dif = xStatic - hLs[2]
                                if dif <= tol:
                                    lstHLinesCp[hLnIx][hLsIx][2] += dif
                                    brk = True
                                    break

                            elif xStatic < hLs[0]:
                                dif = hLs[0] - xStatic
                                if dif <= tol:
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
                flag = False
        lstVLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstVLinesCp)]
        lstHLines = [[tuple(ls) for ls in ln] for ln in copy.deepcopy(lstHLinesCp)]
        return lstVLines, lstHLines

    def getDiPdfBbxErase(diTagsPg, pdfBbx):
        diPdfBbxErase = {}

        for bbx, tup in diTagsPg:
            if (tup[0] in constants.eraseTags) and (
                    bbx[0] > pdfBbx[0] and bbx[1] > pdfBbx[1] and bbx[2] < pdfBbx[2] and bbx[3] < pdfBbx[3]):
                if tup[0] == 'text':
                    if tup[1].xpath('normalize-space(.)').strip():
                        diPdfBbxErase[bbx] = tup[0]
                else:
                    diPdfBbxErase[bbx] = tup[0]
        return diPdfBbxErase

    def eraseCellElm(imgDir, imgFNm, lstMainBbox, diTagsPg, edges):
        diBbox = {(bbx[0], bbx[1]): (bbx[2], bbx[3]) for bbx in lstMainBbox}
        imgShp = edges.shape
        diPdfBbox = pdfutil.imgBboxToPdfBboxMult(diBbox, imgShp[0]) #converting Image Bbox to Pdf Bbox
        imgBbx, pdfBbx=list(diPdfBbox.items())[0]

        cpEdges = copy.deepcopy(edges) #creates a copy of edges
        diPdfBbxErase = getDiPdfBbxErase(diTagsPg, pdfBbx) # collects bboxes of all tags to be erased
        lstImgBbxErase = [pdfutil.translateBbox(list(pdfBbx), imgShp[0]) for pdfBbx in diPdfBbxErase.keys()] #converts collected bboxes to corresponding image bboxes
        if constants.debugCrop:
            pdfutil.cropMultiBoxes(imgFNm + '.png', diPdfBbxErase.items(), inpDir=imgDir,
                                   outDir=constants.tblCropPath.format(imgFNm)) #crops them and saves to disk for debugging purpose
        for imgBbxErase in lstImgBbxErase:
            '''loops over bboxes and erases all content within them'''
            pt1_x, pt1_y, pt2_x, pt2_y = imgBbxErase[0] - constants.eraseTol, imgBbxErase[1] - constants.eraseTol, \
                                         imgBbxErase[
                                             2] + constants.eraseTol, imgBbxErase[3] + constants.eraseTol

            cpEdges[pt1_y:pt2_y, pt1_x:pt2_x] = 0 #erase operation by means of setting pixel value from 255 to 0

        return cpEdges

    def getDiLines(lstMainBbox, diHLs, diVLs):
        diHLines = {}
        diVLines = {}
        for bbx in lstMainBbox:
            for mrgdHLs, lstHLs in diHLs.items():
                if ((bbx[0] <= mrgdHLs[0] < mrgdHLs[2] <= bbx[2]) or (mrgdHLs[0] < bbx[0] < mrgdHLs[2]) or (mrgdHLs[0] < bbx[2] < mrgdHLs[2])) and bbx[1] <= mrgdHLs[1] <= bbx[3]:
                    newMrgdHLs = mrgdHLs
                    if (mrgdHLs[0] < bbx[0] < mrgdHLs[2]):
                        newMrgdHLs = (bbx[0], newMrgdHLs[1], newMrgdHLs[2], newMrgdHLs[3])
                    if (mrgdHLs[0] < bbx[2] < mrgdHLs[2]):
                        newMrgdHLs = (newMrgdHLs[0], newMrgdHLs[1], bbx[2], newMrgdHLs[3])
                    diHLines.setdefault(bbx, {}).update({newMrgdHLs: lstHLs})

            for mrgdVLs, lstVLs in diVLs.items():
                if bbx[0] <= mrgdVLs[0] <= bbx[2] and ((bbx[1] <= mrgdVLs[1] < mrgdVLs[3] <= bbx[3]) or (mrgdVLs[1] <= bbx[1] < mrgdVLs[3]) or (mrgdVLs[1] < bbx[3] < mrgdVLs[3])):
                    newMrgdVLs = mrgdVLs
                    if (mrgdVLs[1] < bbx[1] < mrgdVLs[3]):
                        newMrgdVLs = (newMrgdVLs[0], bbx[1], newMrgdVLs[2], newMrgdVLs[3])
                    if (mrgdVLs[1] < bbx[3] < mrgdVLs[3]):
                        newMrgdVLs = (newMrgdVLs[0], newMrgdVLs[1], newMrgdVLs[2], bbx[3])
                    diVLines.setdefault(bbx, {}).update({newMrgdVLs: lstVLs})


        diLines = {}
        for bbx in lstMainBbox:
            if constants.tblWithoutLn:
                if not diHLines.get(bbx):
                    diHLines[bbx]={(bbx[0],bbx[1],bbx[2],bbx[1]):[(bbx[0],bbx[1],bbx[2],bbx[1])],
                                   (bbx[0],bbx[3],bbx[2],bbx[3]):[(bbx[0],bbx[3],bbx[2],bbx[3])]}
                if not diVLines.get(bbx):
                    diVLines[bbx]={(bbx[0],bbx[1],bbx[0],bbx[3]):[(bbx[0],bbx[1],bbx[0],bbx[3])],
                                   (bbx[2],bbx[1],bbx[2],bbx[3]):[(bbx[2],bbx[1],bbx[2],bbx[3])]}
            diLines[bbx] = (diHLines[bbx], diVLines[bbx])
        return diLines
    def removeJunkLsNew(diBbox,lstHLines, lstVLines):
        lstHLinesNew,lstVLinesNew=[],[]
        for ln in lstHLines:
            lnNew=[]
            for ls in ln:
                if all([not((ul[0]<ls[0]<ls[2]<=lr[0] or ul[0]<=ls[0]<ls[2]<lr[0]) and ul[1]<ls[1]<lr[1]) for ul,lr in diBbox.items()]):
                    lnNew.append(ls)
            if lnNew:
                lstHLinesNew.append(lnNew)
        for ln in lstVLines:
            lnNew = []
            for ls in ln:
                if all([not(ul[0]<ls[0]<lr[0] and (ul[1]<ls[1]<ls[3]<=lr[1] or ul[1]<=ls[1]<ls[3]<lr[1])) for ul,lr in diBbox.items()]):
                    lnNew.append(ls)
            if lnNew:
                lstVLinesNew.append(lnNew)
        return lstHLinesNew,lstVLinesNew
    def removeJunkBbxNew(lstHLines, lstVLines,img,imgFNm):
        lstIntersections = captureIntersections(lstHLines, lstVLines)
        debugPoints(img, lstIntersections, imgFNm,text=False)
        diBbox = getBBox(lstIntersections, lstHLines, lstVLines)
        # debugBbox(img, diBbox, imgFNm,text=False,iter=True)
        debugBbox(img, diBbox, imgFNm)
        lstHLines, lstVLines = removeJunkLsNew(diBbox,lstHLines, lstVLines)
        return lstHLines, lstVLines
    def removeJunkBbx(lstHLines, lstVLines,img,imgFNm,diHLs,diVLs):
        lstIntersections = captureIntersections(lstHLines, lstVLines)
        debugPoints(img, lstIntersections, imgFNm,text=False)
        diBbox = getBBox(lstIntersections, lstHLines, lstVLines)
        # debugBbox(img, diBbox, imgFNm,text=False,iter=True)
        debugBbox(img, diBbox, imgFNm)
        diHLs, diVLs = removeJunkLs(diBbox,diHLs,diVLs)
        return diHLs, diVLs

    def getLinesSbst(lstLines, tblBbox,ixStatic):
        if ixStatic == 0:
            l, u = 1, 3
        else:
            l, u = 0, 2
        lstLinesSbst=[]
        for ln in lstLines:
            lnNew=[]
            for ls in ln:
                if tblBbox[ixStatic] <= ls[ixStatic] <= tblBbox[ixStatic + 2]:
                    if tblBbox[l] <= ls[l] < ls[u] <=tblBbox[u]:
                        lnNew.append(ls)
                    elif ls[l] <= tblBbox[l] < tblBbox[u] <=ls[u]:
                        newLs=list(copy.deepcopy(tblBbox))
                        newLs[ixStatic],newLs[ixStatic+2]=ls[ixStatic],ls[ixStatic]
                        lnNew.append(tuple(newLs))
                    elif tblBbox[l] <= ls[l] <=tblBbox[u]:
                        newLs = list(copy.deepcopy(ls))
                        newLs[u]=tblBbox[u]
                        lnNew.append(tuple(newLs))
                    elif tblBbox[l] <= ls[u] <=tblBbox[u]:
                        newLs = list(copy.deepcopy(ls))
                        newLs[l] = tblBbox[l]
                        lnNew.append(tuple(newLs))
            if lnNew:
                lstLinesSbst.append(lnNew)
        return lstLinesSbst
    def allignTblBbox(lstHLines,lstVLines):
        minX=min([ls[0] for ln in lstHLines for ls in ln])
        maxX=max([ls[2] for ln in lstHLines for ls in ln])
        minY=min([ls[1] for ln in lstVLines for ls in ln])
        maxY=max([ls[3] for ln in lstVLines for ls in ln])
        return (minX,minY,maxX,maxY)
    def getMrgdLn(lstHLines,lstVLines,tblBbox):
        st=datetime.now()
        tblBboxNew=[]
        if tblBbox:
            lstHLines = getLinesSbst(lstHLines, tblBbox, 1)
            lstVLines = getLinesSbst(lstVLines, tblBbox, 0)
            tblBboxNew=allignTblBbox(lstHLines,lstVLines)
        pdfutil.debugTimeTaken(st,datetime.now(),'getLsSgmt')
        debugLS(img, lstHLines, lstVLines, imgFNm)
        lstHLines = reshpMrgdLs(handleIsectOfChrAndClBrdr(lstHLines, 1,img,imgFNm), 1, 0)
        lstVLines = reshpMrgdLs(handleIsectOfChrAndClBrdr(lstVLines, 0,img,imgFNm), 0, 1)


        debugLS(img, lstHLines, lstVLines, imgFNm)
        st = datetime.now()
        diHLs = intraConnectLines(lstHLines, 0, 2)
        diVLs = intraConnectLines(lstVLines, 1, 3)
        pdfutil.debugTimeTaken(st,datetime.now(),'intraConnect')
        diHLs={k:v for k,v in diHLs.items() if k[2]-k[0]>=constants.mrgdHLsLen}
        diVLs={k:v for k,v in diVLs.items() if k[3]-k[1]>=constants.mrgdVLsLen}

        debugLS(img, [diHLs.keys()], [diVLs.keys()], imgFNm)
        return diHLs,diVLs,tblBboxNew

    def allignWithTblMainBBox(lstHLines, lstVLines):
        topLn = lstHLines[0]
        btmLn = lstHLines[-1]
        lftLn = lstVLines[0]
        rhtLn = lstVLines[-1]
        if topLn[0][0] < lftLn[0][0]:
            lftLn = [(topLn[0][0], lftLn[0][1], topLn[0][0], lftLn[0][3])]
        if topLn[0][2] > rhtLn[0][0]:
            rhtLn = [(topLn[0][2], rhtLn[0][1], topLn[0][2], rhtLn[0][3])]
        if topLn[0][0] < btmLn[0][0]:
            btmLn = [(topLn[0][0], btmLn[0][1], btmLn[0][2], btmLn[0][3])]
        if topLn[0][2] > btmLn[0][2]:
            btmLn = [(btmLn[0][0], btmLn[0][1], topLn[0][2], btmLn[0][3])]
        if lftLn[0][3] > btmLn[0][1]:
            btmLn = [(btmLn[0][0], lftLn[0][3], btmLn[0][2], lftLn[0][3])]

        lstHLines[0] = topLn
        lstHLines[-1] = btmLn
        lstVLines[0] = lftLn
        lstVLines[-1] = rhtLn
        return lstHLines, lstVLines
    def checkOverlap(tup,tup1,ixStatic,overlapTol):
        if ixStatic == 0:
            l, u = 1, 3
        else:
            l, u = 0, 2
        return (tup[l]<=tup1[l]<tup1[u]<=tup[u] or tup1[l]<=tup[l]<tup[u]<=tup1[u]) or ((tup1[l]-overlapTol<=tup[l]<tup[u]<=tup1[u]+overlapTol) or (tup[l]-overlapTol<=tup1[l]<tup1[u]<=tup[u]+overlapTol) or (tup1[l]-overlapTol<=tup[l]<=tup1[u]+overlapTol) or (tup1[l]-overlapTol<=tup[u]<=tup1[u]+overlapTol))
    def mergeClusters(lstLs,ixStatic,l,u):
        diScattered = {}
        diUnited = {}

        for ls in lstLs:
            for ls1 in lstLs:
                if checkOverlap(ls, ls1, ixStatic, constants.tblTol):
                    diScattered.setdefault(ls, []).append(ls1)

        for ls, scattered in diScattered.items():
            lstStatic = [ls[ixStatic] for ls in scattered]
            staticVal = math.ceil((min(lstStatic) + max(lstStatic)) / 2)
            lstL = [ls[l] for ls in scattered]
            lstU = [ls[u] for ls in scattered]
            lsNew = list(copy.deepcopy(ls))
            lsNew[l], lsNew[u] = min(lstL), max(lstU)
            lsNew[ixStatic], lsNew[ixStatic + 2] = staticVal, staticVal
            diUnited[ls] = tuple(lsNew)
        return diUnited
    def mergeClustersWrap(lstLs,ixStatic,l,u):
        diUnited=mergeClusters(lstLs, ixStatic, l, u)
        diUnited=mergeClusters(list(diUnited.values()),ixStatic,l,u)
        return diUnited
    def shiftToLastLnNew(lstLs,ixStatic,l,u):
        diUnited=mergeClustersWrap(lstLs,ixStatic,l,u)
        if ixStatic==0:
            lstMrgdLn = reshpMrgdLs(list(set(diUnited.values())), 0, 1)
        elif ixStatic==1:
            lstMrgdLn = reshpMrgdLs(list(set(diUnited.values())), 1, 0)
        return lstMrgdLn


    def shiftToLastLn(mrgBucket,ixStatic):
        firstLn=copy.deepcopy(mrgBucket[0])
        lastLn=copy.deepcopy(mrgBucket[-1])
        staticVal=math.ceil((firstLn[0][ixStatic]+lastLn[0][ixStatic])/2)
        shifted=[]
        for ls in lastLn:
            lsLst = list(ls)
            lsLst[ixStatic], lsLst[ixStatic + 2] = staticVal, staticVal
            shifted.append(tuple(lsLst))
        for ln in mrgBucket[0:-1]:
            for ls in ln:
                lsLst=list(ls)
                lsLst[ixStatic],lsLst[ixStatic+2]=staticVal,staticVal
                if tuple(lsLst) not in shifted:
                    shifted.append(tuple(lsLst))
        return list(set(shifted))


    def processMrgBucket(mrgBucket,ixStatic,ixLow,ixUp):
        mrgBucketFlat = [ls for ln in mrgBucket for ls in ln]
        shifted=shiftToLastLnNew(mrgBucketFlat,ixStatic,ixLow,ixUp)
        return shifted

    def processBucket(mrgBucket, ixStatic, ixLow,ixUp,filtLstLines):
        mrgdLn = processMrgBucket(mrgBucket,ixStatic,ixLow,ixUp)
        filtLstLines.extend(mrgdLn)
        mrgBucket = []
        return filtLstLines,mrgBucket


    def handleIsectOfChrAndClBrdr(lstLines, ixStatic,img,imgFNm):
        if ixStatic == 0:
            l, u = 1, 3
        else:
            l, u = 0, 2
        ixStaticTol=2
        lstLinesFlat=[tup for lst in lstLines for tup in lst]
        cellBorders = [tup for tup in lstLinesFlat if (tup[u] - tup[l]) > constants.minCellBorderLen]
        lstLinesFlatSbst = [tup for tup in lstLinesFlat if
                            any([0 <= tup[ixStatic] - clBrdr[ixStatic] <= ixStaticTol for clBrdr in cellBorders])]
        if ixStatic == 0:
            debugLS(img, [[ls] for ls in lstLinesFlatSbst], [], imgFNm)
        else:
            debugLS(img, [],[[ls] for ls in lstLinesFlatSbst], imgFNm)

        for clBrdr in cellBorders:
            lstLinesFlatSbst = [tup for tup in lstLinesFlat if 0 <= tup[ixStatic] - clBrdr[ixStatic] <= ixStaticTol]
            diUnited=mergeClustersWrap(lstLinesFlatSbst, ixStatic, l, u)
            for tup in lstLinesFlatSbst:
                lstLinesFlat.remove(tup)

            lstLinesFlat.extend(diUnited.values())
        lstLinesFlat = [tup for tup in lstLinesFlat if ((tup[u] - tup[l]) >= constants.intraCLsLen)]
        return lstLinesFlat

    def filt(lstLines, ixStatic, minLsLen,returnMrgBkt=False,customFilt=False):
        filtLstLines = []
        if ixStatic == 0:
            l, u = 1, 3
        else:
            l, u = 0, 2
        lstMrgBucket=[]
        mrgBucket = []
        mrgLenBucket = []
        for ix, ln in enumerate(lstLines):
            lnSpan = (ln[0][l], ln[-1][u])
            lnLen=lnSpan[1]-lnSpan[0]
            if 0 < lnSpan[1] - lnSpan[0] < minLsLen:
                continue
            staticCrnt = ln[0][ixStatic]
            if ix < len(lstLines) - 1:
                lnNxt = lstLines[ix + 1]
                staticNxt = lnNxt[0][ixStatic]

                lnNxtSpan = (lnNxt[0][l], lnNxt[-1][u])

                if lnNxtSpan[1] - lnNxtSpan[0] >= constants.intraCLsLen and 0 < (staticNxt - staticCrnt) < constants.filtTol:
                    if constants.customFilt or customFilt:
                        mrgBucket.append((ln, lnLen))
                    else:
                        if all([lnLen>=tup[1] for tup in mrgBucket]):
                            mrgBucket=[(ln,lnLen)]
                    continue
            if constants.customFilt or customFilt:
                mrgBucket.append((ln, lnLen))
            else:
                if all([lnLen >= tup[1] for tup in mrgBucket]):
                    mrgBucket = [(ln, lnLen)]
            lstMrgBucket.append(mrgBucket)
            filtLstLines, mrgBucket = processBucket([tup[0] for tup in mrgBucket], ixStatic, l, u, filtLstLines)
        if returnMrgBkt:
            return filtLstLines,lstMrgBucket
        return filtLstLines

    def filterLn(lstHLines, lstVLines, minLsLen):

        filtLstHLines = filt(lstHLines, 1, minLsLen)
        filtLstVLines = filt(lstVLines, 0, minLsLen)

        return filtLstHLines, filtLstVLines

    def removeJunkFrmBbox(lstHLines,lstVLines,diBbox):
        deleteHLines = []
        deleteVLines = []
        for k, v in diBbox.items():
            for ix, vLn in enumerate(lstVLines):
                if k[0] <= vLn[0][0] <= v[0] and k[1] <= vLn[0][1] < vLn[0][3] <= v[1] and vLn[0][1] != k[1]:
                    deleteVLines.append((ix, 0))

                if k[0] <= vLn[-1][0] <= v[0] and k[1] <= vLn[-1][1] < vLn[-1][3] <= v[1] and vLn[-1][1] != k[1]:
                    deleteVLines.append((ix, -1))

            for ix, hLn in enumerate(lstHLines):
                if k[0] <= hLn[0][0] < hLn[0][2] <= v[0] and k[1] <= hLn[0][1] <= v[1] and hLn[0][2] != v[0]:
                    deleteHLines.append((ix, 0))

                if k[0] <= hLn[-1][0] < hLn[-1][2] <= v[0] and k[1] <= hLn[-1][1] <= v[1] and hLn[-1][2] != v[0]:
                    deleteHLines.append((ix, -1))
        for tup in deleteHLines:
            ixLn, ixLs = tup
            if len(lstHLines[ixLn]) > 0:
                lstHLines[ixLn].pop(ixLs)
        for tup in deleteVLines:
            ixLn, ixLs = tup
            if len(lstVLines[ixLn]) > 0:
                lstVLines[ixLn].pop(ixLs)
        filtLstHLines = [ln for ln in lstHLines if ln]
        filtLstVLines = [ln for ln in lstVLines if ln]
        return filtLstHLines,filtLstVLines

    def getOuterBbox(lstLines):
        prntBbox = (lstLines[0][0][0], lstLines[0][0][1], lstLines[-1][0][2], lstLines[-1][0][3])
        return prntBbox

    def getOpenEndedOuterBbox(diBbox, yTop, yBtm, xLft, xRht,img,imgFNm):
        # if not diBbox and constants.tblWithoutLn:
        #     diBbox[(xLft,yTop)]=(xRht,yBtm)
        lstBbox = sorted([k + v for k, v in zip(diBbox.keys(), diBbox.values())], key=lambda tup: (tup[1], tup[0]))
        prntBbox = (lstBbox[0][0], lstBbox[0][1], lstBbox[-1][2], lstBbox[-1][3])
        # debugBbox(img, {(prntBbox[0], prntBbox[1]): (prntBbox[2], prntBbox[3])}, imgFNm)
        lftCol = {(xLft, k[1]): (k[0], v[1]) for k, v in diBbox.items() if k[0] == prntBbox[0]}
        rhtCol = {(v[0], k[1]): (xRht, v[1]) for k, v in diBbox.items() if v[0] == prntBbox[2]}
        topRow = {(k[0], yTop): (v[0], k[1]) for k, v in diBbox.items() if k[1] == prntBbox[1]}
        btmRow = {(k[0], v[1]): (v[0], yBtm) for k, v in diBbox.items() if v[1] == prntBbox[3]}
        mrgAll = {}
        for di in [lftCol, rhtCol, topRow, btmRow]:
            mrgAll.update(di)

        #update the 4 corner bboxes
        cornerBboxes={(xLft, yTop): (prntBbox[0], prntBbox[1]), (prntBbox[2], yTop): (xRht, prntBbox[1]),
                       (xLft, prntBbox[3]): (prntBbox[0], yBtm), (prntBbox[2], prntBbox[3]): (xRht, yBtm)}
        mrgAll.update({k:v for k,v in cornerBboxes.items() if k not in mrgAll})
        return prntBbox,mrgAll

    def giveOuterBorders(diBbox,filtLstHLines, filtLstVLines,img, imgFNm):
        yTop=min(filtLstHLines[0][0][1],sorted([vLn[0] for vLn in filtLstVLines], key=lambda tup: tup[1])[0][1])
        yBtm=max(filtLstHLines[-1][0][1],sorted([vLn[-1] for vLn in filtLstVLines], key=lambda tup: tup[3])[-1][3])
        xLft=min(filtLstVLines[0][0][0],sorted([hLn[0] for hLn in filtLstHLines], key=lambda tup: tup[0])[0][0])
        xRht=max(filtLstVLines[-1][0][0],sorted([hLn[-1] for hLn in filtLstHLines], key=lambda tup: tup[2])[-1][2])
        topLn=(xLft,yTop,xRht,yTop)
        btmLn=(xLft,yBtm,xRht,yBtm)
        lftLn=(xLft,yTop,xLft,yBtm)
        rhtLn=(xRht,yTop,xRht,yBtm)
        prntBbox,openEndedOuterBbox=getOpenEndedOuterBbox(diBbox,yTop,yBtm,xLft,xRht,img,imgFNm)
        debugBbox(img, openEndedOuterBbox, imgFNm)

        filtLstHLines, filtLstVLines=removeJunkFrmBbox(filtLstHLines,filtLstVLines,openEndedOuterBbox)
        debugLS(img, filtLstHLines, filtLstVLines, imgFNm)
        for ix,hLn in enumerate(filtLstHLines):
            if len(hLn)>1:
                lftHLs=hLn[0]
                rhtHLs=hLn[-1]
                if lftHLs[0]<prntBbox[0]:
                    filtLstHLines[ix][0]=(xLft,lftHLs[1],lftHLs[2],lftHLs[3])
                if lftHLs[2]>prntBbox[2]:
                    filtLstHLines[ix][-1]=(rhtHLs[0],rhtHLs[1],xRht,rhtHLs[3])
            elif len(hLn)==1:
                hLs = hLn[0]
                newXLft,newXRht=hLs[0],hLs[2]
                if newXLft < prntBbox[0]:
                    newXLft=xLft
                if newXRht > prntBbox[2]:
                    newXRht=xRht
                filtLstHLines[ix][0] = (newXLft, hLs[1], newXRht,hLs[3])

        for ix,vLn in enumerate(filtLstVLines):
            if len(vLn)>1:
                topVLs=vLn[0]
                btmVLs=vLn[-1]
                if topVLs[1]<prntBbox[1]:
                    filtLstVLines[ix][0]=(topVLs[0],yTop,topVLs[2],topVLs[3])
                if btmVLs[3]>prntBbox[3]:
                    filtLstVLines[ix][-1]=(btmVLs[0],btmVLs[1],btmVLs[2],yBtm)
            elif len(vLn)==1:
                vLs = vLn[0]
                newYTop, newYBtm = vLs[1], vLs[3]
                if newYTop<prntBbox[1]:
                    newYTop=yTop
                if newYBtm>prntBbox[3]:
                    newYBtm=yBtm
                filtLstVLines[ix][0] = (vLs[0],newYTop, vLs[2], newYBtm)

        if topLn not in filtLstHLines[0]:
            filtLstHLines=[[topLn]]+filtLstHLines
        if btmLn not in filtLstHLines[-1]:
            filtLstHLines=filtLstHLines+[[btmLn]]
        if lftLn not in filtLstVLines[0]:
            filtLstVLines=[[lftLn]]+filtLstVLines
        if rhtLn not in filtLstVLines[-1]:
            filtLstVLines=filtLstVLines+[[rhtLn]]
        return filtLstHLines, filtLstVLines

    def completeLines(outerBbox,interCHLines, interCVLines):
        interCHLinesComp=[[(outerBbox[0],ln[0][1],outerBbox[2],ln[0][3])] for ln in interCHLines]
        interCVLinesComp=[[(ln[0][0],outerBbox[1],ln[0][2],outerBbox[3])] for ln in interCVLines]
        return interCHLinesComp, interCVLinesComp

    def adjoinOuterBbx(lstMainBbox,diHLs,diVLs):
        for bbx in lstMainBbox:
            lstLn=convertBbxtoLn(bbx)
            topLn=lstLn[0]
            btmLn=lstLn[1]
            lftLn=lstLn[2]
            rhtLn=lstLn[3]
            diHLs[topLn]=[topLn]
            diHLs[btmLn]=[btmLn]
            diVLs[lftLn]=[lftLn]
            diVLs[rhtLn]=[rhtLn]

        return diHLs,diVLs

    def findExtension(ls, lstMrgBkt,ixStatic,ixLow,ixUp):
        if not lstMrgBkt:
            return None
        firstCandidates=lstMrgBkt[1]
        lastCandidates=lstMrgBkt[-2]
        first=any([lstMrgBkt[0][-1][0][0][ixStatic]<ls[ixLow]<candLs[ixStatic]<=ls[ixUp]+constants.tblTol  for candLs in firstCandidates[0][0]])
        last=any([ls[ixLow]-constants.tblTol<=candLs[ixStatic]<ls[ixUp]<lstMrgBkt[-1][0][0][0][ixStatic] for candLs in lastCandidates[-1][0]])
        if first and last:
            return 3
        return 1 if first else 2 if last else None


    def extendLines(bbx,tupLines,minLsLen):
        diHLines=tupLines[0]
        diVLines=tupLines[1]
        diHLinesNew={}
        lstHLines = reshpMrgdLs(diHLines.keys(), 1, 0)
        lstVLines = reshpMrgdLs(diVLines.keys(), 0, 1)
        interCVLines, interCHLines = interConnectLines(lstVLines, lstHLines)
        for hLs,lstHLs in list(diHLines.items()):
            newHLs=hLs
            ixStatic=1
            staticVal=hLs[ixStatic]
            subsetVLn=[vLn for vLn in interCVLines if any([vLs[1]<=staticVal<=vLs[3] for vLs in vLn])]
            filtLstVLines,lstMrgBkt=filt(subsetVLn,0, minLsLen,returnMrgBkt=True,customFilt=True)
            extend=findExtension(hLs,lstMrgBkt,0,0,2)
            if extend==1:
                newHLs=(bbx[0],newHLs[1],newHLs[2],newHLs[3])
            elif extend==2:
                newHLs = (newHLs[0], newHLs[1], bbx[2], newHLs[3])
            elif extend==3:
                newHLs = (bbx[0], newHLs[1], bbx[2], newHLs[3])
            diHLinesNew[newHLs]=lstHLs

        diVLinesNew = {}
        for vLs,lstVLs in list(diVLines.items()):
            newVLs=vLs
            ixStatic=0
            staticVal=vLs[ixStatic]
            subsetHLn=[hLn for hLn in interCHLines if any([hLs[0]<=staticVal<=hLs[2] for hLs in hLn])]
            filtLstHLines,lstMrgBkt=filt(subsetHLn,1, minLsLen,returnMrgBkt=True,customFilt=True)
            extend=findExtension(vLs,lstMrgBkt,1,1,3)
            if extend==1:
                newVLs=(newVLs[0],bbx[1],newVLs[2],newVLs[3])
            elif extend==2:
                newVLs = (newVLs[0], newVLs[1], newVLs[2], bbx[3])
            elif extend==3:
                newVLs = (newVLs[0], bbx[1], newVLs[2], bbx[3])
            diVLinesNew[newVLs]=lstVLs
        return (diHLinesNew,diVLinesNew)



    if constants.isPdfTbl:
        '''if pdf is editable then a few native elements like textbox,image,figure can be removed safely from the corresponding image file.
        This will give performance boost to the process since otherwise all line segments (timy ones too) have to be processed and removed separately'''
        debugImage(edges, imgFNm, outFNm=constants.debugLsBefEraseFNm)
        edges = eraseCellElm(imgDir, imgFNm, [(0,0,edges.shape[1],edges.shape[0])], diTagsPg, edges) #identifies and removes tags from edges file
        debugImage(edges, imgFNm, outFNm=constants.debugLsAftEraseFNm)

    lstHLines = getLSgmt(edges, minLsLen, 'H')
    lstVLines = getLSgmt(edges.transpose(), minLsLen, 'V')
    origTblBbox = copy.deepcopy(tblBbox)
    if tblBbox:
        diHLs,diVLs={},{}
        newTblBbox=[]
        for bbx in tblBbox:
            diHLsBbx, diVLsBbx,tblBboxNew=getMrgdLn(copy.deepcopy(lstHLines),copy.deepcopy(lstVLines),bbx)
            diHLs.update(diHLsBbx)
            diVLs.update(diVLsBbx)
            newTblBbox.append(tblBboxNew)
        tblBbox=newTblBbox
    else:
        diHLs, diVLs,_ = getMrgdLn(copy.deepcopy(lstHLines),copy.deepcopy(lstVLines),tblBbox)  # find,intraconnect and merge line segments

    debugLS(img, [diHLs.keys()], [diVLs.keys()],imgFNm)

    st = datetime.now()
    lstMainBbox = tblBbox if tblBbox else findTblMainBbox(diHLs.keys(), diVLs.keys()) # determines the outer bounding boxes of all tables present on a page
    if origTblBbox:
        mapOrigNewBbox=dict(zip(lstMainBbox,origTblBbox))
    for bbx in lstMainBbox:
        debugBboxAsRect(bbx,img,imgFNm)
    if constants.extendMainBbox:
        lstMainBbox=getExtendedMainBbox(lstMainBbox,diHLs.keys(), diVLs.keys(),minLsLen)
        for bbx in lstMainBbox:
            debugBboxAsRect(bbx,img,imgFNm)
    diHLs,diVLs=adjoinOuterBbx(lstMainBbox,diHLs, diVLs)
    pdfutil.debugTimeTaken(st,datetime.now(),'findTblMainBbox')

    diMainBbox={(tup[0],tup[1]):(tup[2],tup[3]) for tup in lstMainBbox} #reshape lstMainBbox for writing to file
    debugBbox(img, diMainBbox, imgFNm)

    diLines = getDiLines(lstMainBbox, diHLs, diVLs) #assigns lige segments to the their corresponding table

    for bbx, tupLines in list(diLines.items()):
        if constants.extendTable:
            tupLines=extendLines(bbx, tupLines, minLsLen)
        diHLsTbl,diVLsTbl=tupLines[0],tupLines[1]
        debugLS(img, [diHLsTbl.keys()], [diVLsTbl.keys()], imgFNm)
        lstHLines = reshpMrgdLs(diHLsTbl.keys(), 1, 0)
        lstVLines = reshpMrgdLs(diVLsTbl.keys(), 0, 1)
        filtLstHLines, filtLstVLines = filterLn(lstHLines, lstVLines, minLsLen)
        debugLS(img, filtLstHLines, filtLstVLines, imgFNm)
        interCVLines, interCHLines = interConnectLines(filtLstVLines,filtLstHLines) # connect every pair of one horizontal lsgmt and one vertical lsgmt if their corner points are within tolerenc limit with respect to each other
        debugLS(img, interCHLines, interCVLines, imgFNm)
        st = datetime.now()

        # diHLsTbl, diVLsTbl = removeJunkBbx(interCHLines, interCVLines,img,imgFNm,diHLsTbl,diVLsTbl) #removes bboxes and/or lsgmt of embedded figures and tables in a table cell. This can also work for embedded text in a cell
        # pdfutil.debugTimeTaken(st,datetime.now(),'removeJunkBbx')
        # debugLS(img, [diHLsTbl.keys()], [diVLsTbl.keys()], imgFNm)
        # tblLstHLines = reshpMrgdLs(diHLsTbl.keys(), 1, 0) #reshapes lstHLinesMrgd to list of lists
        # tblLstVLines = reshpMrgdLs(diVLsTbl.keys(), 0, 1) #reshapes lstHLinesMrgd to list of lists
        ''' discards lines which are away from each other by less than the tolerance.
        This is mainly done to avoid double edges for the same line'''
        filtLstHLines, filtLstVLines = filterLn(interCHLines, interCVLines,minLsLen)
        debugLS(img, filtLstHLines, filtLstVLines, imgFNm)

        filtLstHLines, filtLstVLines = allignWithTblMainBBox(filtLstHLines, filtLstVLines)
        debugLS(img, filtLstHLines, filtLstVLines, imgFNm)

        interCVLines, interCHLines = interConnectLines(filtLstVLines, filtLstHLines)
        interCHLines, interCVLines=removeJunkBbxNew(interCHLines, interCVLines, img, imgFNm)
        debugLS(img, interCHLines, interCVLines, imgFNm)
        outerBbox = getOuterBbox(interCHLines)
        interCHLinesComp, interCVLinesComp=completeLines(bbx,interCHLines, interCVLines)
        # debugLS(img, interCHLinesComp, interCVLinesComp, imgFNm)
        diLines[bbx] = (interCHLines, interCVLines, interCHLinesComp, interCVLinesComp)
    if origTblBbox:
        diLinesNew = {mapOrigNewBbox[k]: v for k, v in diLines.items()}
    else:
        diLinesNew = diLines
    return diLinesNew


def auto_canny(image, sigma=0.33):
    # compute the median of the single channel pixel intensities
    v = np.median(image)

    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edged = cv2.Canny(image, lower, upper)

    # return the edged image
    return edged


def cleanBBox(diBbox):
    removed = []
    for ul, lr in list(diBbox.items()):
        for ul1, lr1 in list(diBbox.items()):
            if ul == ul1 and lr == lr1:
                continue
            if ul[0] > ul1[0] and ul[1] > ul1[1] and lr[0] < lr1[0] and lr[1] < lr1[1]:
                diBbox.pop(ul)
                removed.append(ul + lr)
                if constants.debugTblEraseJunk:
                    print('removed bbx: {}'.format(ul + lr))
                break
    return diBbox, removed


def removeJunkLs(diBbox,diHLs,diVLs):
    def removeJnk(ul,lr,diLs):
        removed = []
        for mrgdLs,lstLs in list(diLs.items()):
            for ls in lstLs:
                pt1_x, pt1_y, pt2_x, pt2_y = ls[0], ls[1], ls[2], ls[3]
                if pt1_x > ul[0] and pt1_y > ul[1] and pt2_x < lr[0] and pt2_y < lr[1]:
                    diLs.pop(mrgdLs)
                    removed.append(mrgdLs)
                    if constants.debugTblEraseJunk:
                        print('removed Ls: {}'.format(mrgdLs))
                    break
        return diLs,removed
    removedHLs=[]
    removedVLs=[]
    for ul, lr in list(diBbox.items()):
        diHLs,removed=removeJnk(ul,lr,diHLs)
        removedHLs.extend(removed)
        diVLs,removed=removeJnk(ul,lr,diVLs)
        removedVLs.extend(removed)
        
    return diHLs,diVLs



def extractTable(fNm, pgNo, pagesInFile, diTagsPg,tblBbox=None,imgBytes=None):
    '''the main wrapper for extraction of table from one single pdf page'''

    '''determinig minimum line segment length based on whether the image is taken from a editable pdf or not
    If image is of editable pdf then all the textlines can be erased and minLSLen can be set to a bare minimum like 5 pixels 
    otherwise it should be set higher (30 or above) depending on the table'''
    if constants.isPdfTbl:
        minLsLen = constants.pdfTblMinLsLen
    else:
        minLsLen = constants.tblMinLsLen
    # justPgNo = utils.lJustPgNo(pgNo, pagesInFile) # Left justifying page number (i.e. 1 to 01 or 1 to 001 depending on the total number of pages)
    justPgNo = pgNo # Left justifying page number (i.e. 1 to 01 or 1 to 001 depending on the total number of pages)
    imgFNmNoExt = '{0}-{1}'.format('p', justPgNo)
    imgFNm = imgFNmNoExt + '.png'
    imgDir = constants.imageDir + fNm + '/'
    imgPath = imgDir + imgFNm # complete image path
    if imgBytes:
        nparr = np.fromstring(imgBytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(imgPath) #reading image in numpy array using opencv
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) #grayscale image
    if constants.microEdges:
        edges = cv2.Canny(gray, 10,100, apertureSize=3)
    else:
        if constants.triageEdges:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        else:
            edges = auto_canny(gray) #Canny edge detection #added for document_comparison
    debugImage(edges, imgFNmNoExt, outDir=constants.debugTblPath, outFNm=constants.debugEdgesFNm) #writing edges image to file
    debugImage(gray, imgFNmNoExt, outDir=constants.debugTblPath, outFNm=constants.debugGrayFNm) #writing grayscale image to file

    diTbls = findAllTbls(img, diTagsPg, edges, imgDir, imgFNmNoExt, minLsLen,tblBbox) #detect all tables on a page and assign the corresponding hLs (horizontal line segment) an vLs (vertical line segment) to each on of them

    diTblsNew = {}
    lstHLinesAllTbls=[]
    lstVLinesAllTbls=[]
    for tbl, tupLines in diTbls.items(): #capturing all cells of table and converting corresponding bounding boxes to final table
        lstHLines, lstVLines = tupLines[0], tupLines[1] #collecting horizontal and vertical lines
        lstHLinesAllTbls.extend(lstHLines)
        lstVLinesAllTbls.extend(lstVLines)
        lstHLinesComp, lstVLinesComp = tupLines[2], tupLines[3] #collecting horizontal and vertical lines
        # debugLS(img, lstHLines, lstVLines,imgFNmNoExt)
        imgShp = edges.shape
        lstIntersections = captureIntersections(lstHLines, lstVLines) #capture intersection points of every pair of horizontal and vertical lines
        lstIntersectionsComp = captureIntersections(lstHLinesComp, lstVLinesComp) #capture intersection points of every pair of horizontal and vertical lines
        debugPoints(img, lstIntersections, imgFNmNoExt)
        diBbox = getBBox(lstIntersections, lstHLines, lstVLines) #capture bounding box using intersection points and lines
        diBboxComp = getBBox(lstIntersectionsComp, lstHLinesComp, lstVLinesComp) #capture bounding box using intersection points and lines

        debugBbox(img, diBbox, imgFNmNoExt)
        # lol = bboxesToTableOld(diBbox) #list of lists where each sublist represents one row of a table
        lol = bboxesToTable(diBbox,diBboxComp) #list of lists where each sublist represents one row of a table
        print('pg {}'.format(pgNo),lol)
        htmTbl, diSpanInfo = htmlTable(lol,pgNo) #converts lol to html table
        diTblsNew[tbl] = {'diBbox': diBbox, 'lol': lol, 'htmTbl': htmTbl, 'diSpanInfo': diSpanInfo, 'imgShp': imgShp}
    debugLS(img,lstHLinesAllTbls,lstVLinesAllTbls,imgFNmNoExt)
    return diTblsNew


if __name__ == '__main__':
    # temp()
    # exit(0)
    # fNm = 'UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059_91-95'
    fNm = 'ocr-table'
    # pageNo = "1"
    # minLLen = 14
    extractTable(fNm, 1, 1, "")
    img = cv2.imread(r'../output/{0}-{1}.png'.format(fNm, pageNo))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    cv2.imwrite('edges-50-150.jpg', edges)
    cv2.imwrite('gray-50.jpg', gray)
    lstHLines = getLSgmt(edges, minLLen, 'H')
    lstVLines = getLSgmt(edges.transpose(), minLLen, 'V')
    lstHLines, lstVLines = clnLS(lstHLines, lstVLines)
    debugLS(img, lstHLines, lstVLines, fNm)
    imgShp = edges.shape

    lstIntersections = captureIntersections(lstHLines, lstVLines)
    imgPts = copy.deepcopy(img)
    debugPoints(imgPts, lstIntersections, fNm)

    diBbox = getBBox(lstIntersections, lstHLines, lstVLines)
    debugBbox(img, diBbox, fNm)
    diPdfBbox = imgBboxToPdfBboxMult(diBbox, imgShp[0])
    xmlFNm = r'{0}.xml'.format(fNm)
    tree = pdfutil.readXml(xmlFNm)
    diTags = pdfutil.queryXml(tree, pdfutil.diSel['textline'].format(int(pageNo)))
    textInsideBbox = getTextInsideBboxMult(diPdfBbox.values(), diTags)
    lol = bboxesToTable(diBbox)
    htmTbl = htmlTable(lol)
    print(htmTbl)
    print("Done")
