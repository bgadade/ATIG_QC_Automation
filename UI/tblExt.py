from flask import Flask,jsonify ,request
from bin import extractTableWrapper as tblExtWrap
from bin import pdfExtractionUtils as pdfUtil
import lxml.html
import pickle
from bin import constants
import json
import os
import shutil
import sys
app = Flask(__name__)


def readPickle(token,**kwargs):
    with open(kwargs.get('dirPath',"../tmp/") + token + '.pkl' , 'rb') as handle:
        pickledObj = pickle.load(handle)
    return pickledObj

def writePickle(token, input,**kwargs):
    with open(kwargs.get('dirPath',"../tmp/") + token + '.pkl', 'wb') as handle:
        pickle.dump(input,handle,2)


@app.route("/extractTable",methods=['GET'])
def extractTable():
    token = request.args.get('token')
    pklDir=request.args.get('pklDir')
    pdfDir=request.args.get('pdfDir')
    savedInput=readPickle(token,dirPath=pklDir)
    xml=savedInput['xml'].encode('utf-8') if not isinstance(savedInput['xml'],bytes) else savedInput['xml']
    fNm=savedInput['fNm']
    diPagesPdfBbx=savedInput['diPagesPdfBbx']
    diOut={fNm:xml}
    diTbl=tblExtWrap.triagePdfWrapper(diOut, fNm, diPagesPdfBbx,pdfDir)
    savedInput['diTbl']=diTbl
    writePickle(token, savedInput,dirPath=pklDir)
    return jsonify({'result':"Success"})

@app.route("/getTables",methods=['GET'])
def getTables():
    token = request.args.get('token')
    pklDir = request.args.get('pklDir')
    pdfDir = request.args.get('pdfDir')
    savedInput = readPickle(token, dirPath=pklDir)
    fNm = savedInput['fNm']
    diOut=savedInput['diOut']
    diTbl=tblExtWrap.findAllTables(fNm,diOut,pdfDir)
    savedInput['diTbl'] = diTbl
    writePickle(token, savedInput, dirPath=pklDir)
    return jsonify({'result': "Success"})

@app.route("/convertToXML",methods=['GET'])
def convertToXML():
    token = request.args.get('token')
    pklDir = request.args.get('pklDir')
    pdfDir = request.args.get('pdfDir')
    savedInput = readPickle(token, dirPath=pklDir)
    fNm = savedInput['fNm']
    diOut=pdfUtil.convertMultiple([fNm],pdfDir=pdfDir)
    savedInput['diOut'] = diOut
    writePickle(token, savedInput, dirPath=pklDir)
    return jsonify({'result': "Success"})

@app.route("/convertToXMLandExtractTables",methods=['POST'])
def convertToXMLandExtractTables():
    file=request.files.get('file')
    fNm=request.form.get('tkn')
    xmlParseInp=request.form.get('xmlParseInp')
    xmlParseInp=json.loads(xmlParseInp)
    pdfPath=constants.pdfDir + fNm + '.pdf'
    imgFNm=fNm+'-1'
    imgPath=constants.imageDir + fNm
    tblPath=constants.tmpDir +'table/'+imgFNm
    xmlPath=constants.tmpDir + fNm + '.xml'
    file.save(pdfPath)
    diOut=pdfUtil.convertMultiple([fNm])
    diTbl = tblExtWrap.findAllTables(fNm, diOut)
    diTags=tblExtWrap.parseXmlMultApi(diOut, xmlParseInp)
    diTblNew={pg:[(tblTup[0],None,tblTup[2],tblTup[3]) for tblTup in lstTbl] for pg,lstTbl in diTbl.items()}
    diOutNew={k:str(v) for k,v in diOut.items()}
    if os.path.exists(pdfPath):
        os.remove(pdfPath)
    if os.path.exists(imgPath):
        shutil.rmtree(imgPath)
    # if os.path.exists(tblPath):
    #     shutil.rmtree(tblPath)
    if os.path.exists(xmlPath):
        os.remove(xmlPath)
    data=str({"diTbl":diTblNew,"diOut":diOutNew,"diTags":diTags})
    return jsonify({"data":data,"len":len(data)})

@app.route("/convertToXMLandExtractTablesImg",methods=['POST'])
def convertToXMLandExtractTablesImg():
    pdfFile=request.files.get('pdfFile')
    imgFile=request.files.get('imgFile')
    fNm=request.form.get('tkn')
    xmlParseInp=request.form.get('xmlParseInp')
    xmlParseInp=json.loads(xmlParseInp)
    pdfPath=constants.pdfDir + fNm + '.pdf'
    imgFNm=fNm+'-1'
    imgPath=constants.imageDir + fNm
    if not os.path.exists(imgPath):
        os.makedirs(imgPath)
    tblPath=constants.tmpDir +'table/'+imgFNm
    xmlPath=constants.tmpDir + fNm + '.xml'
    pdfFile.save(pdfPath)
    imgFile.save(imgPath+'/{}-1.png'.format(fNm))
    diOut=pdfUtil.convertMultiple([fNm])
    diTbl = tblExtWrap.findAllTablesNew(fNm, diOut)
    diTags=tblExtWrap.parseXmlMultApi(diOut, xmlParseInp)
    diTblNew={pg:[(tblTup[0],None,tblTup[2],tblTup[3]) for tblTup in lstTbl] for pg,lstTbl in diTbl.items()}
    diOutNew={k:str(v) for k,v in diOut.items()}
    if os.path.exists(pdfPath):
        os.remove(pdfPath)
    if os.path.exists(imgPath):
        shutil.rmtree(imgPath)
    # if os.path.exists(tblPath):
    #     shutil.rmtree(tblPath)
    if os.path.exists(xmlPath):
        os.remove(xmlPath)
    data=str({"diTbl":diTblNew,"diOut":diOutNew,"diTags":diTags})
    return jsonify({"data":data,"len":len(data)})


@app.route("/convertToXMLandExtractTablesImgXml",methods=['POST'])
def convertToXMLandExtractTablesImgXml():
    xmlFile=request.files.get('xmlFile')
    imgFile=request.files.get('imgFile')
    fNm=request.form.get('tkn')
    xmlParseInp=request.form.get('xmlParseInp')
    xmlParseInp=json.loads(xmlParseInp)
    diOut=pdfUtil.convertMultipleNew([(fNm,xmlFile.read())])
    diTbl = tblExtWrap.findAllTablesNew(fNm, diOut,imgBytes=imgFile.read())
    diTags=tblExtWrap.parseXmlMultApi(diOut, xmlParseInp)
    diTblNew={pg:[(tblTup[0],None,tblTup[2],tblTup[3]) for tblTup in lstTbl] for pg,lstTbl in diTbl.items()}
    diOutNew={k:str(v) for k,v in diOut.items()}
    data=str({"diTbl":diTblNew,"diOut":diOutNew,"diTags":diTags})
    return jsonify({"data":data,"len":len(data)})

@app.route("/getDiTags",methods=['POST'])
def getDiTags():
    xmlFile = request.files.get('xmlFile')
    fNm = request.form.get('tkn')
    pg= request.form.get('pg')
    bounds=request.form.get('bounds')
    xmlParseInp = request.form.get('xmlParseInp')
    xmlParseInp = json.loads(xmlParseInp)
    diOut = pdfUtil.convertMultipleNew([(fNm, xmlFile.read())])
    diTags = tblExtWrap.parseXmlMultApi(diOut, xmlParseInp)
    data = str({"diTags": diTags})
    return jsonify({"data": data, "len": len(data),"pg":pg,"fNm":fNm,"bounds":bounds})

@app.route("/parseXmlMult",methods=['GET'])
def parseXmlMult():
    token = request.args.get('token')
    pklDir = request.args.get('pklDir')
    savedInput = readPickle(token, dirPath=pklDir)
    diOut=savedInput['diOut']
    funcInp=savedInput['funcInp']
    diTags=pdfUtil.parseMultiple(diOut, selKey=funcInp['selKey'], text=funcInp['text'])
    diTagsNew = {}
    for fNm, diPg in diTags.items():
        for pgNm, lstTags in diPg.items():
            for tgTup in lstTags:
                bbx = tgTup[0]
                tgInfo = tgTup[1]
                tgTyp, tgObj = tgInfo[0], tgInfo[1]
                tgObjStr = lxml.html.tostring(tgObj)
                diTagsNew.setdefault(fNm, {}).setdefault(pgNm, []).append((bbx, (tgTyp, tgObjStr)))
    savedInput['diTags'] = diTagsNew
    writePickle(token, savedInput, dirPath=pklDir)
    return jsonify({'result': "Success"})


@app.route("/parseTree",methods=['GET'])
def parseTree():
    token = request.args.get('token')
    pklDir = request.args.get('pklDir')
    savedInput = readPickle(token, dirPath=pklDir)
    funcInp = savedInput['funcInp']
    diTags=pdfUtil.parseTree(lxml.html.fromstring(funcInp['tree']), selKey=funcInp['selKey'],tagAttribAndText=funcInp['tagAttribAndText'])
    diTagsNew = []
    for tgTup in diTags:
        bbx = tgTup[0]
        tgInfo = tgTup[1]
        tgTyp, tgObj, attrDi,txt = tgInfo[0], tgInfo[1], tgInfo[2],tgInfo[3]
        tgObjStr = lxml.html.tostring(tgObj)
        diTagsNew.append((bbx, (tgTyp, tgObjStr, attrDi,txt)))

    savedInput['diTags1'] = diTagsNew
    writePickle(token, savedInput, dirPath=pklDir)
    return jsonify({'result': "Success"})


if __name__ == "__main__":
    if len(sys.argv)>1:
        app.run(host='0.0.0.0', port=int(sys.argv[1]), threaded=True)
    else:
        app.run(host='0.0.0.0', port=constants.tblApiPort, threaded=True)