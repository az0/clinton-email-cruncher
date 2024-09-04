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

mkdir -p pdfs/

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
    cd pdfs/
	wget --no-check-certificate --no-clobber --timeout=5 --tries=20 -i ../pdflist.txt
	cd ..
fi

python extractPDFMetadata.py

mkdir -p zips/
python zipPDFs.py # The ZIPs are not used by any other code here.
python pdfTextToDatabase.py
deactivate
