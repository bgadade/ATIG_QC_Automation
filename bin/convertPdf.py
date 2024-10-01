from bin import constants
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter, XMLConverter, HTMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import BytesIO,StringIO


converters={"xml":XMLConverter,"html":HTMLConverter,"text":TextConverter}

def convert_pdf_doc_v1(path,output_type="xml",codec="utf-8",password=""):
    rsrcmgr = PDFResourceManager()
    retstr = BytesIO()
    laparams = LAParams()
    device = converters[output_type](rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    maxpages = 0
    caching = True
    pagenos = set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue().decode()
    fp.close()
    device.close()
    retstr.close()
    return text


def convert_pdf_doc(pdf_path,output_type="xml"):
    resource_manager = PDFResourceManager()
    fake_file_handle = BytesIO()
    converter = converters[output_type](resource_manager, fake_file_handle,laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(pdf_path, 'rb') as fh:
        for page in PDFPage.get_pages(fh,
                                      caching=constants.skipConv,
                                      check_extractable=True):
            page_interpreter.process_page(page)

        text = fake_file_handle.getvalue()

    # close open handles
    converter.close()
    fake_file_handle.close()

    if text:
        return text


def convert_pdf_by_page(pdf_path,output_type="xml"):
    with open(pdf_path, 'rb') as fh:
        for page in PDFPage.get_pages(fh,
                                      caching=True,
                                      check_extractable=True):
            resource_manager = PDFResourceManager()
            fake_file_handle = BytesIO()
            converter = converters[output_type](resource_manager, fake_file_handle)
            page_interpreter = PDFPageInterpreter(resource_manager, converter)
            page_interpreter.process_page(page)

            text = fake_file_handle.getvalue()+b'</pages>'
            yield text

            # close open handles
            converter.close()
            fake_file_handle.close()

def extract_text(pdf_path):
    # print(extract_text_by_page(pdf_path))
    for page in convert_pdf_by_page(pdf_path):
        print(page)
        print("------------------------------------------------------")

if __name__ == '__main__':
    path='..\input\AAAL18HM4089873_000_SP_H0432001_EnrollmentReceipt.pdf'
    out_typ = "xml"
    output_type = out_typ
    print((convert_pdf_doc(path,output_type = out_typ)))
    # print((convert_pdf_doc_v1(path,output_type = out_typ)))
    # print(list(convert_pdf_by_page(path)))
    # extract_text(path)