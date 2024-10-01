import os
import sys
import random
import string
import json
import datetime
from flask import Flask, render_template, json, request,jsonify,send_file,send_from_directory
from werkzeug import secure_filename
# from flask_cors import CORS, cross_origin
sys.path.append('../bin/')
from bin import main as mn
from bin import constants
import pandas as pd

app = Flask(__name__)
# CORS(app)

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = '../input/'

# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set([".htm",".html","pdf","xlsx"])

# For a given file, returns whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def main():
    return render_template('starter.html')

@app.route('/uploadFiles/upload/',methods=['GET','POST'])
def upload():
    print("inside flask")
    uploaded_files = request.files
    data = {'filenames':[]}
    for j in range(0,len(uploaded_files)):
        fileInList = 'file[0]['+str(j)+']'
        file = uploaded_files[fileInList]
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                data['filenames'].append(filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            except Exception as e:
                return 'Invalid Template', 500
    #print('uploaded data : ',data)
    return json.dumps(data)




@app.route('/uploadFiles/Excel/',methods=['GET','POST'])
def uploadExcel():
    print("inside flask")
    uploaded_files = request.files
    file = uploaded_files['file[0]']
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except Exception as e:
            return 'Invalid Template', 500
    allowed_chars = ''.join((string.ascii_lowercase, string.ascii_uppercase, string.digits))
    unique_id = ''.join(random.choice(allowed_chars) for _ in range(32)) + str(datetime.datetime.now()).replace(":","-")
    data = {'filename':filename,'token':unique_id}
    #print('uploaded data : ',data)
    return json.dumps(data)
#
@app.route('/convertPDF/<fileList>',methods=['GET','POST'])
def parsePdf(fileList):
    fileList = json.loads(fileList)['filenames']
    fileList1 = [file.split('.pdf')[0] for file in fileList]
    data = mn.main(fileList1)
    for idx,row in enumerate(data['data']):
        row['SNo'] = idx+1
    #print("data",data)
    return json.dumps(data)

@app.route('/signin/',methods=['POST'])
def signUp():
    _name = request.json['name']
    _password = request.json['password']
    _domain = request.json['selectedDomain']
    return mn.validateCredentials(_name,_password,_domain)


@app.route('/getOutputdata/<outputData1>',methods=['GET','POST'])
def generateOutput(outputData1):
    data = json.loads(outputData1)
    keys = ['SNo','file_name', 'Component Code', 'Comments', 'Pass_Fail']
    data = [{k:v for k,v in each_row.items() if k in keys} for each_row in data]
    return json.dumps(data);

@app.route('/getJSON/',methods=['POST'])
def getJSON():
    filename = request.json['filename']
    data = mn.getFileJSON(filename)
    #print("filename:",filename,"fileData:",data)
    return json.dumps(data)

@app.route('/addNewUser/',methods=['POST'])
def addNewUser():
    data = request.json
    #print("new user:",data)
    mn.addCredentials(data)
    return 'success'

@app.route('/setJSON/',methods=['POST'])
def setDataList():
    data = request.json['data']
    filename = request.json['filename']
    #print("data:",data)
    mn.setJSONData(data,filename)
    return 'success'

@app.route('/signout/',methods=['GET'])
def signOut():
    print('Signed out successfully')
    return 'success'

@app.route('/saveInputFile/<fileList>',methods=['GET','POST'])
def saveinputFile(fileList):
    data = json.loads(fileList)
    mn.createPickle(data['token'], data['filename'],data['selectedYear'])
    print("Pickle created")
    return "success"

@app.route('/validatePDF/<fileList>',methods=['GET','POST'])
def validatePDF(fileList):
    data = json.loads(fileList)
    PdfFileList = data[0]['filenames']
    token = data[1]
    validationResult = mn.validatePdfWrapper(token,PdfFileList)
    #print(validationResult)
    return json.dumps(validationResult)


@app.route('/result/',methods=['GET','POST'])
def getResult():
    return json.dumps([{'filename': 'UHEX18PP4241065_001_16174_GRP_EOC_07062018_153059.pdf', 'comments': ['Checkpoint:CheckPoint2 Issue Description:Acupuncture Services In Network Custom Only: Acupuncture- value mismatch Actual (Output):20.00% Expected (SOT):$35.00', 'Checkpoint:CheckPoint2 Issue Description:Acupuncture Services Out of Network Custom Only: Acupuncture- value mismatch Actual (Output):20.00% Expected (SOT):$35.00', 'Checkpoint:CheckPoint2 Issue Description:Ambulance Services In Network AMBULANCE_EMERGENCY ROOM_URGENT CARE: Ambulance Services- value mismatch Actual (Output):$175.00 Expected (SOT):$50.00', 'Checkpoint:CheckPoint2 Issue Description:Ambulance Services Out of Network AMBULANCE_EMERGENCY ROOM_URGENT CARE: Ambulance Services- value mismatch Actual (Output):$175.00 Expected (SOT):$50.00', 'Checkpoint:CheckPoint2 Issue Description:Annual Routine Physical Exam In Network Annual Routine Physical Exam- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Annual Routine Physical Exam Out of Network Annual Routine Physical Exam- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Annual Wellness Visit In Network PREVENTIVE SERVICES:  Annual Wellness Exam and One-time Welcome to Medicare Exam (Medicare Covered)- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Annual Wellness Visit Out of Network PREVENTIVE SERVICES:  Annual Wellness Exam and One-time Welcome to Medicare Exam (Medicare Covered)- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Bone Mass Measurement In Network PREVENTIVE SERVICES: Bone Mass Measurement (Bone Density)- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Bone Mass Measurement Out of Network PREVENTIVE SERVICES: Bone Mass Measurement (Bone Density)- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Breast Cancer Screening (Mammograms) In Network PREVENTIVE SERVICES: Mammography- missing in PDF Actual (Output):N/A Expected (SOT):$0.00', 'Checkpoint:CheckPoint2 Issue Description:Breast Cancer Screening (Mammograms) Out of Network PREVENTIVE SERVICES: Mammography- missing in PDF Actual (Output):N/A Expected (SOT):$0.00'], 'status': 'Fail'}])

@app.route('/getPdfFile/<fileName>',methods=['GET','POST'])
def send_pdf(fileName):
    print(fileName)
    pdfFileName = json.loads(fileName)
    return send_from_directory('../input/', pdfFileName)

@app.route('/getExcelFile/',methods=['GET','POST'])
def getExcelFileData():
    print("inside excels")
    data = request.json['outputData']
    token  = request.json['token']
    for file_data in data: file_data['comments'] = '\n\n'.join(file_data['comments'])
    keys = ['SNo', 'filename', 'comments', 'status']
    data = [{k: v for k, v in each_row.items() if k in keys} for each_row in data]
    outData = mn.exportReviewedData(data, token, keys)
    outputData = {
        "filename": outData,
        "token":token
    }
    return json.dumps(outputData)

@app.route('/getDwnldfile/<token>',methods=['GET','POST'])
def get_file(token):
    # print("token:",token)
    outputFile = token
    return send_file('static/output/'+outputFile+'.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name='Outpit_123'+'.xlsx', as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8098, threaded=True)
