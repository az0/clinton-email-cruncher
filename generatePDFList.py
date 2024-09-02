#!/usr/bin/env python
# encoding: utf-8

"""
generatePDFList.py

1. Get list of links from database
2. Write out file for wget to use
"""

from hrcemail_common import Document, pdf_list_fn

pdf_base = "https://foia.state.gov/"

with open(pdf_list_fn, 'w') as list_file:
	for doc in Document.select():
		pdf_link = doc.pdfLink.replace('\\','/')
		list_file.write(pdf_base+doc.pdfLink+"\n")
