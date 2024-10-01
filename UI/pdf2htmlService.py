from pdf2Html import main as mn
from bin import constants
from pdf2Html import constants as const
from flask import Flask, render_template,request,jsonify
import sys
app = Flask(__name__)
@app.route('/')
def main():
    return render_template('starter.html')

@app.route("/convertPdfToHtml",methods=['POST'])
def convertPdfToHtml():
    pdfFile = request.files['pdfFile']
    fNm = request.form.get('tkn','')
    pdfPath = constants.pdfDir + fNm + '.pdf'
    pdfFile.save(pdfPath)
    html=mn.mainFunc(fNm)
    return jsonify({"html": html,"tkn":fNm,"len": len(html)})

if __name__ == "__main__":
    if len(sys.argv)>1:
        app.run(host='0.0.0.0', port=int(sys.argv[1]), threaded=True)
    else:
        app.run(host='0.0.0.0', port=const.pdf2HtmlApiPort, threaded=True)