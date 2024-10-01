from bin import utils
import os
os.chdir('UI')
pdf2htmlExePath=r'..\pdf2htmlEX-win32-0.14.6-upx-with-poppler-data\pdf2htmlEX.exe'
inpPath='../input/'
outPath='../output/'
configPath='../config/'
# refFilePath=inpPath+'QA Crosswalk_8.2.xlsx'
# refDf=utils.readFile(refFilePath,type='xlsx',colAsStr=True)
inpColMapPath=configPath+'inputCols.json'
inpColMap=utils.readFile(inpColMapPath,type='json')
outputColMapPath=configPath+'outputCols.json'
outputColMap=utils.readFile(outputColMapPath,type='json')
outputFilePath=outPath+'output.xlsx'
stdPath=configPath+'standards.json'
std=utils.readFile(stdPath,type='json')
outJsnKeysMapPath=configPath+'outJsnKeys.json'
outJsnKeysMap=utils.readFile(outJsnKeysMapPath,type='json')
skipConv=True
diSel={'tagsWithNoChildren':".//page[@id='{0}']//*[@bbox and  not(*)]",'imgTxtLn2':".//page[@id='{0}']//*[local-name()='textline' or local-name()='figure']",'pgChildrenTags':".//page[@id='{0}']/*",'rect':".//page[@id='{0}']//rect",'fig':".//page[@id='{0}']//figure",'textline':".//page[@id='{0}']//textline",'curve':".//page[@id='{0}']//curve",'line':".//page[@id='{0}']//line","fig-curve-rect":".//page[@id='{0}']//*[self::curve or self::figure or self::rect]","textbox":".//page[@id='{0}']//textbox","textPg":".//text"}
diBound={"SP":{"RX_BIN":{"param":("Si tiene preguntas, comuníquese con su representante","de ventas con licencia:"),"type":"txtLn","subType":""},"RX_PCN":{"param":("de ventas con licencia:","Nombre y N.° de ID del representante de ventas con licencia"),"type":"txtLn","subType":""},"RX_GRP":{"param":("Nombre y N.° de ID del representante de ventas con licencia","N.º de teléfono del representante de ventas con licencia"),"type":"txtLn","subType":""},"COMP_CODE": {"param":2,"type":"tagPos","subType":"nthTop","filter":{"name":"ANONYMOUS_TAIL","order_by":"x","reverse":False}},"CMS_CODE": {"param":1,"type":"tagPos","subType":"nthTop","filter":{"name":"ANONYMOUS_TAIL","order_by":"x","reverse":False}},"filters":{"ANONYMOUS_TAIL":{"param":2,"type":"tagPos","subType":"tail"}}},
         "E": {"RX_BIN": {"param":("if  you  have  any", "questions:"),"type":"txtLn","subType":""},"RX_PCN": {"param":("questions:", "Licensed Sales Representative Name and ID Number"),"type":"txtLn","subType":""}, "RX_GRP": {"param":("Licensed Sales Representative Name and ID Number", "Licensed Sales Representative Phone No."),"type":"txtLn","subType":""},"COMP_CODE": {"param":2,"type":"tagPos","subType":"nthTop","filter":{"name":"ANONYMOUS_TAIL","order_by":"x","reverse":False}},"CMS_CODE": {"param":1,"type":"tagPos","subType":"nthTop","filter":{"name":"ANONYMOUS_TAIL","order_by":"x","reverse":False}},"filters":{"ANONYMOUS_TAIL":{"param":2,"type":"tagPos","subType":"tail"}}}}
pageLocatorPath = configPath+'pageLocator.json'
pageLocator = utils.readFile(pageLocatorPath, type='json')
imageDir='../images/'
contentLocatorPath = configPath+'contentLocator.json'
contentLocator = utils.readFile(contentLocatorPath, type='json')
outDir = '../extracted_temp/'
templateDriversPath = configPath + 'templateDrivers.json'
templateDrivers = utils.readFile(templateDriversPath, type='json')
medChartPath = configPath + 'EOC_MAOnly_medChart.json'
medChartJson = utils.readFile(medChartPath, type='json')
pdfDir='../input/'
tmpDir='../tmp/'
# pdfToImgToolPath = r"../pfoppler-0.51_x86/poppler-0.51/bin/pdftoppm.exe"
pdfToImgToolPath = r"../pdfbox/pdfbox-app-2.0.21.jar"
pklPathDiOut=tmpDir+'diOut'
pklPathDiTags=tmpDir+'diTags'
pklPathDiTagsFigs=tmpDir+'diTagsFigs'
pklPathDiTagsText_Font=tmpDir+'diTagsText_Font'
pklPathDiTagsFigAndTextWithFont=tmpDir+'diTagsFigAndTextWithFont'
debugTable=False
createState=False
useState=False
isPdfTbl=False
tblTol=5
icTol=15
pdfTblMinLsLen=tblTol+1
tblMinLsLen=1
intraCLsLen=15
mrgdHLsLen=15
mrgdVLsLen=15
filtTol=5
eraseTol=tblTol-2
tblFltTol=tblTol-2
minTblOutBorder=50
minCellBorderLen=30
tblDebugExt='.png'
debugTblPath=tmpDir+'/table/{}/'
debugLsFNm='mylines'
debugPtsFNm='myPts'
debugIsectPtsFNm='myIsectPts'
debugLsBefEraseFNm='befEraseTags'
debugLsAftEraseFNm='aftEraseTags'
debugEdgesFNm='edges'
debugGrayFNm='gray'
debugImgFNm='temp_image'
debugLsAftJunkEraseFNm='aftEraseJunk'
eraseTags=['text']
tblCropPath=tmpDir+'table/crops/{}/'
debugCropLog=False
debugCrop=False
debugTblMainBbox=False
debugTblEraseJunk=False
debugTblImg=False
debugDiTbl=True
combineDbgImg=False
debugTime=False
debubTblTime=True
combineDf=True
customFilt=True
tblWithoutLn=False
extendTable=False
extendMainBbox=False
microEdges=False
combineTbls=True

tblApiPort= '8098'
triageEdges=True