#!/usr/bin/env python
# encoding: utf-8

"""
zipPDFs.py

1. Get a list of files from the database
2. For each distinct documentClass, create a zip file
3. Write the PDFs into each zip file from pdfs/

"""

import zipfile
import os

from peewee import fn

from hrcemail_common import Document

docClasses = (Document.select(fn.Distinct(Document.documentClass).alias("docClass")))

for docClass in docClasses:
	zip_fn = "zips/"+docClass.docClass+".zip"
	if not os.path.isfile(zip_fn):
		with zipfile.ZipFile(zip_fn, "w") as zf:
			docIDs = (Document.select(Document.docID).where(Document.documentClass == docClass.docClass))
			print(f"Archiving {len(docIDs)} PDFs in class {docClass.docClass} into {zip_fn}") 
			for docID in docIDs:
				if os.path.isfile("pdfs/"+docID.docID+".pdf"):
					zf.write("pdfs/"+docID.docID+".pdf", docID.docID+".pdf")
				else:
					print(f"Could not find {docID.docID}.pdf")
	else:
		print(f"{zip_fn} already exists. Skipping.")
