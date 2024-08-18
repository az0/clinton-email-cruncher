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
mkdir -p zips/
python downloadMetadata.py
python generatePDFList.py
if [ "$1" = "no-pdf-download" ]
then 
    echo "skipping PDF download"
else
    cd pdfs/
	wget --no-check-certificate --no-clobber --timeout=5 --tries=20 -i ../pdflist.txt
	cd ..
fi
python zipPDFs.py
python pdfTextToDatabase.py
deactivate
