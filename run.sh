#!/bin/bash
VENVDIR=/tmp/venv/clinton-email-cruncher
if [ ! -d "$VENVDIR" ]; then
	echo "creating venv in $VENVDIR"
	python3 -m venv $VENVDIR
	source $VENVDIR/bin/activate
	echo "installing required packages"
	pip install -r requirements.txt
else
	echo "activating existing venv"
	source $VENVDIR/bin/activate
fi

mkdir -p pdf/

python downloadMetadata.py
if [ $? -ne 0 ]; then
	echo "downloadMetadata.py failed"
	exit 1
fi

python generatePDFList.py
if [ $? -ne 0 ]; then
	echo "downloadMetadata.py failed"
	exit 1
fi

if [ "$1" = "no-pdf-download" ]
then 
    echo "skipping PDF download"
else
    cd pdf/
	wget --no-check-certificate --no-clobber --timeout=5 --tries=20 -i ../pdflist.txt
	cd ..
fi

# Extract metadata such as page count, and store it in SQLite.
python extractPDFMetadata.py

# The ZIPs are not used by any other code here.
mkdir zip
python zipPDF.py

# Perform OCR, and store text and metadata in JSON.
mkdir json
python pdfTextToJson.py

python cleanText.py

# Extract text from each PDF (from OCR stored in PDF)
# and store it in SQLite.
# FIXME: broken
#python pdfTextToDatabase.py

deactivate
