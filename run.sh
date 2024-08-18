#!/bin/bash
mkdir -p pdfs/
mkdir -p zips/
python3 -m venv create virt-hrcemail
source virt-hrcemail/bin/activate
pip install -r requirements.txt
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
