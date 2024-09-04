#!/usr/bin/env python
# encoding: utf-8

"""
downloadMetadata.py

1. Page through the Clinton_Email collection on state.foia.gov
2. Write rows to sqlite db, ON DUPLICATE KEY UPDATE VALUES

"""

from datetime import datetime
import requests
import requests_cache
import certifi
import re
import json
import sys

from peewee import IntegrityError

from hrcemail_common import db, requests_cache_fn, Document

# 1800 seconds = 30 minutes
requests_cache.install_cache(requests_cache_fn,expire_after=1800)

base_url = "https://foia.state.gov/"
api_endpoint = base_url + "/api/Search/SubmitSimpleQuery"

def getAPIPage(start=0,limit=1000,page=1):
	params = {"searchText": "*",
	"beginDate": "false",
	"endDate": "false",
	"collectionMatch": "Clinton_Email",
	"postedBeginDate": "false",
	"postedEndDate": "false",
	"caseNumber": "false",
	"page":page,
	"start": start,
	"limit": limit}
	
	#SSL certificate not verified by certifi module for some reason	
	print(f"getAPIPage({start},{limit},{page})")
	request = requests.get(api_endpoint,params=params)

	if not request.status_code == 200:
		print(f'ERROR: request.get() in getAPIPage() has status code {request.status_code}')
	return_json = request.text
	#date objects not valid json, extract timestamp
	return_json = re.sub(r'new Date\(([0-9]{1,})\)',r'\1',return_json)
	#negitive dates are invalid, and can sometimes be shown as newDate()
	return_json = re.sub(r'new ?Date\((-[0-9]{1,})\)',r'null',return_json)
	try:
		return_dict = json.loads(return_json)
	except ValueError:
		print('ValueError in loads()')
		import pdb;pdb.set_trace()

	return return_dict

def compileResultsList(results_list=[],start=0, limit=1000):
	metadata_response = getAPIPage(start=start,limit=limit)
	results_list.extend(metadata_response["Results"])
	if len(results_list) < metadata_response["totalHits"]:
		start += limit
		compileResultsList(results_list=results_list,start=start,limit=limit)
	elif len(results_list) > metadata_response["totalHits"]:
		sys.exit("error, results count mismatch")
	return results_list
	
def formatTimestamp(timestamp):
	# If timestamp is an integer (or a string with an integer) then...
	if isinstance(timestamp, int):
		return datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d")
	# If timestamp is in format "2019-05-14T00:00:00" return just the date.
	# As of 2024-08-31, this is the only format seen.
	if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",timestamp):
		# As of 2024-08-31, this is the only format seen.
		return timestamp[0:10]

results_list = compileResultsList()

print(f"got {len(results_list)} total document rows")
print("writing rows to SQLite database ...")

with db.transaction():
	for result in results_list:
		result["pdfLink"] = base_url + result["pdfLink"]
		result["messageFrom"] = result["from"]
		del result["from"]
		if result['docDate'].startswith('0001-01-01'):
			result['docDate'] = None
		else:
			result["docDate"] = formatTimestamp(result["docDate"])
			if result["docDate"] < "1995-01-01":
				raise ValueError(f"docDate {result['docDate']} is before 1995")
			if result["docDate"] > datetime.now().strftime("%Y-%m-%d"):
				raise ValueError(f"docDate {result['docDate']} is after today")
		result["postedDate"] = formatTimestamp(result["postedDate"])
		result["docID"] = result["pdfLink"][-13:][0:9]
		result["attachmentOf"] = None
		try:
			Document.create(**result)
		except IntegrityError as e:
			# Only insert new rows; don't update existing rows
			# If "UNIQUE constraint failed: document.docID", then ignore the exception.
			if not "UNIQUE constraint failed: document.docID" in str(e):
				print(e)
				import pdb;pdb.set_trace()			

db.commit()

