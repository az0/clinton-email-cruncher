"""

Quickly extract PDF metadata from each PDF and write to
the SQLite database.

This step does not perform OCR or extract any text from
the PDFs.

Copyright (C) 2024 by Andrew Ziem. See LICENSE for details.


"""
import json
import os
import pprint
import glob
import hashlib
import re

from datetime import datetime

from hrcemail_common import Document

import PyPDF2


def hash_file(file_path):
    """Returns the MD5 hash of a file"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def media_box_to_inches(media_box):
    """Converts a PyPDF2 media box tuple to inches

    The dimensions are rounded to two decimal places.
    """
    return (round(media_box[2]/72, 2), round(media_box[3]/72, 2))


def get_pdf_date(metadata, field):
    """
    Given PDF timestamp, this returns a Python native datetime.
    """
    if not field in ('/CreationDate', '/ModDate'):
        raise ValueError(
            f"field must be '/CreationDate' or '/ModDate' not {field}")
    if field not in metadata:
        return None
    val = metadata[field]
    val = val.replace('D:', '')  # Remove the 'D:' prefix
    # If format is like "D:19970409113550"
    if re.match(r"^\d{14}$", val):
        return datetime.strptime(val, '%Y%m%d%H%M%S')
    # If format is like "D:19970409113550Z" in C06166610
    if re.match(r"^\d{14}Z$", val):
        # Change the Z to -00'00'
        val = val.replace('Z', '-00\'00\'')
    # If format is like "D:20180830113411-04'00'"
    if re.match(r"^\d{14}-\d{2}'00'$", val):
        val = val.replace("'", "")
        return datetime.strptime(val, '%Y%m%d%H%M%S%z')

    raise ValueError(f"unrecognized PDF timestamp {val}")


def extract_pdf_metadata(docID):
    """
    Given document ID (e.g., C06130675), return a dictionary of metadata.
    """
    print(f"extracting PDF metadata from {docID}")
    pdf_file_path = 'pdfs/'+docID+'.pdf'
    with open(pdf_file_path, 'rb') as pdf_f:
        pdf_reader = PyPDF2.PdfReader(pdf_f)
        info = pdf_reader.metadata
        pages = pdf_reader.pages
        mediabox = pdf_reader.pages[0].mediabox
    creation_date = get_pdf_date(info, '/CreationDate')
    mod_date = get_pdf_date(info, '/ModDate')
    file_size = os.path.getsize(pdf_file_path)
    hash_sum = hash_file(pdf_file_path)
    page_size = media_box_to_inches(mediabox)
    doc_metadata = {
        "fileSize": file_size,
        "hashSum": hash_sum,
        "pageWidth": page_size[0],
        "pageHeight": page_size[1],
        "pageCount": len(pages),
        "pdfCreationDate": creation_date,
        "pdfModificationDate": mod_date,
        "pdfCreatorSoftware": info.creator,
        "pdfProducerSoftware": info.producer if '/Producer' in info else None
    }
    for each_key in info.keys():
        if each_key not in ['/Creator', '/ModDate', '/CreationDate', '/Producer']:
            # The only Title is "HighView Page", and this is not interesting.
            # The only Author is MikeT, and this is not interesting.
            # There are no subjects.
            if info[each_key] not in ('', 'HighView Page', 'MikeT'):
                print(f"unexpected key found in pdf_peader.metadata: {
                      each_key} = {info[each_key]}")
    return doc_metadata


def main():
    docIDs = Document.select(Document.docID).where(Document.pageCount >> None)

    print(f'processing {len(docIDs)} PDFs.')
    for docID in docIDs:
        docID = docID.docID
        meta = extract_pdf_metadata(docID)
        update_query = Document.update(**meta).where(Document.docID == docID)
        update_query.execute()


if __name__ == '__main__':
    main()
