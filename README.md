# Get and analyze Hillary Clinton's email

In response to a public records request, the U.S. State Department released Hillary Clinton's email messages from her time as Secretary of State. Every month, newly released messages were posted to [foia.state.gov](https://foia.state.gov/) as PDFs with some metadata.

This collection of tools automates downloading and helps analyze the messages. The Wall Street Journal's interactive graphics team uses some of this code to power the [Clinton inbox search](http://graphics.wsj.com/hillary-clinton-email-documents/) interactive.

## What's in the toolkit
* **run.sh** runs all of the Python scripts in the toolkit automatically, allowing easy updates when messages are released.

* **downloadMetadata.py** scrapes sender, recipient, message date and subject from [the message list](https://foia.state.gov/Search/Results.aspx?collection=Clinton_Email) and writes this metadata to a sqlite database, `hrcemail.sqlite`.
* **generatePDFList.py** writes `pdflist.txt`, a newline-delimited list of HTTPS URLs of the message PDFs.
* **zipPDFs.py** makes a zip file of PDFs for each release of messages.
* **pdfTextToDatabase.py** extracts text from the PDF files (which are OCR'd by State) and writes the text to a sqlite database, `hrcemail.sqlite`.

* **HRCEMAIL_names.csv** is a list that pairs sender and recipient names provided by the State Department website with that person's commonly-used name. For example, `HRC` becomes `Hillary Clinton`.

## Requirements

* git
* Python 3.x
* wget

Mac OS X users can install wget using [homebrew](http://brew.sh/).

Downloading the PDFs can take around 30 minutes. If you don't want to download the PDFs, run `./run.sh no-pdf-download`.

On Ubuntu, install tesseract for English and Arabic.

```
sudo apt install tesseract tesseract-ocr-ara tesseract-ocr-script-arab
```

## How to get started

Clone the repo.
```
git clone https://github.com/az0/clinton-email-cruncher.git
cd clinton-email-cruncher
```

Run the shell script.

```
./run.sh
```

Finally, load `HRCEMAIL_names.csv` into the `hrcemail.sqlite` database.
```
csvsql --db "sqlite:///hrcemail.sqlite" --insert --no-create --blanks --table name  HRCEMAIL_names.csv 
```

## Let's do some analysis!

How many messages did everyone send and receive? Run this SQL query:

```
sql2csv --db "sqlite:///hrcemail.sqlite" --query 'SELECT commonName,sum(to_count) to_sum, sum(from_count) from_sum, sum(from_count+to_count) total_sum FROM (
SELECT toName.`commonName`,0 from_count, count(distinct docID) to_count
FROM document d
JOIN name toName ON toName.`originalName` = d.`to`
JOIN name fromName ON fromName.`originalName` = d.`from`
group by toName.`commonName`
UNION ALL
SELECT fromName.`commonName`,count(distinct docID) from_count, 0 to_count
FROM document d
JOIN name toName ON toName.`originalName` = d.`to`
JOIN name fromName ON fromName.`originalName` = d.`from`
group by fromName.`commonName`
) t GROUP BY commonName
ORDER BY total_sum DESC;' | head | csvlook
```

## How you can help

Are there any names in the `document` table that are not resolved in the `name` table? Use this query to check:
```
SELECT d.originalName d,n.originalName n FROM (SELECT distinct `to` originalName
FROM document
UNION
SELECT distinct `from` originalName
FROM document) d
LEFT JOIN name n ON TRIM(d.originalName) LIKE n.originalName
WHERE n.originalName IS NULL;
```
Find anything that needs to be updated? Fix the `name` table, export to `HRCEMAIL_names.csv`, and make a pull request.
```
sqlite3 -header -csv hrcemail.sqlite "SELECT * FROM name ORDER BY commonName,originalName;" > HRCEMAIL_names.csv 
```

## Future work

* Extract the time the message was sent or received from the full text
* Split the full text into constituent messages
* Develop a list of phrases to remove from the full text (e.g., "PRODUCED TO HOUSE SELECT BENGHAZI COMM")
* Infer message threads
* Pair attachments with their messages
