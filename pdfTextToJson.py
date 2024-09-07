#!/usr/bin/env python
# encoding: utf-8

"""
pdfTextToDatabase.py

1. Get a list of PDF names from the database
2. Open them
3. Extract text contents
4. Write contents to json directory

"""


import argparse
import json
import os
import sys
import tempfile
from joblib import Parallel, delayed

import fitz  # PyMuPDF
import pytesseract
from playhouse.shortcuts import model_to_dict  # peewee
from tqdm import tqdm
from PIL import Image

from hrcemail_common import Document


def ocr_pdf(docID, pdf_filename):
    """
    Perform OCR on a PDF file and return the extracted text.

    :param docID: Document ID
    :param pdf_path: Path to the PDF file
    :return: Extracted text from the PDF
    """
    extracted_text = ""
    lang = 'eng'
    if docID == 'C05778404':
        # Contains Arabic.
        lang += '+ara'

    with fitz.open(pdf_filename) as pdf_document:
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            # Increase resolution to improve OCR accuracy.
            zoom = 2
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            # Improve performance using ppm format and tmpfs directory.
            with tempfile.NamedTemporaryFile(
                    prefix='clinton',
                    suffix='.ppm',
                    dir='/dev/shm') as tmp:
                tmp.write(pix.tobytes('ppm'))
                text = pytesseract.image_to_string(tmp.name, lang=lang)
            extracted_text += text

    return extracted_text


def write_json(document, ocr_text):
    """Write OCR text to json/docID.json"""
    json_fn = 'json/'+document.docID+'.json'
    ret = model_to_dict(document)
    ret['text'] = ocr_text
    with open(json_fn, 'w', encoding='utf-8') as f:
        # JSON can't handle dates
        import datetime
        for k, v in ret.items():
            if isinstance(v, datetime.date):
                ret[k] = v.isoformat()
        json.dump(ret, f, indent=2)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-cpu-count',
        type=int,
        default=-1,
        help='how many CPUs to use for parallel processing')
    args = parser.parse_args(argv)

    document = Document.select()

    print(f'processing {len(document):,} PDFs.')
    # Filter out documents that have already been processed
    # to improve tqdm time estimate.
    docs_to_process = [doc for doc in document if not os.path.isfile(
        'json/'+doc.docID+'.json')]

    def process_doc(docID):
        this_docID = docID.docID
        pdf_filename = 'pdfs/'+this_docID+'.pdf'
        ocr_text = ocr_pdf(this_docID, pdf_filename)
        write_json(docID, ocr_text)

    Parallel(n_jobs=args.max_cpu_count)(delayed(process_doc)(docID)
                                        for docID in tqdm(docs_to_process, unit='PDF'))


if __name__ == '__main__':
    main()
