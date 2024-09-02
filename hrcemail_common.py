# encoding: utf-8

from peewee import SqliteDatabase, Model, CharField, DateField, TextField, IntegerField, FloatField, DateTimeField

sqlite_db_fn = "hrcemail.sqlite"
requests_cache_fn = "HRCEMAIL_metadata_cache"
pdf_list_fn = 'pdflist.txt'
db = SqliteDatabase(sqlite_db_fn)

class BaseModel(Model):
	class Meta:
		database = db

class Document(BaseModel):
	docID = CharField(max_length=9,unique=True,primary_key=True)
	subject = CharField(null=True)
	documentClass = CharField()
	pdfLink = CharField()
	originalLink = CharField(null=True)
	docDate = DateField(null=True)
	postedDate = DateField()
	#from is a reserved word
	messageFrom = CharField(db_column="from",null=True)
	to = CharField(null=True)
	messageNumber = CharField(null=True)
	caseNumber = CharField()
	docText = TextField(null=True)
	# Below fields added August 2024.
	hashSum = CharField(null=True, max_length=32)
	fileSize = IntegerField(null=True)
	pageWidth = FloatField(null=True)
	pageHeight = FloatField(null=True)
	pageCount = IntegerField(null=True)
	#pdfAuthor = CharField(max_length=255)
	pdfCreationDate = DateTimeField(null=True)
	pdfModificationDate = DateTimeField(null=True)
	pdfCreatorSoftware = CharField(null=True)
	pdfProducerSoftware = CharField(null=True)

		
class Name(BaseModel):
	originalName = CharField(primary_key=True)
	commonName = CharField()

db = SqliteDatabase(sqlite_db_fn)
db.connect()
# If they don't exist, create tables.
db.create_tables([Document,Name])
