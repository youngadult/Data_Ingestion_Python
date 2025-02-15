import pdfplumber
from io import BytesIO
import logging
from  config import Config
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import AzureOpenAI
from azure.search.documents import SearchClient

def extractContentFromPdf(blobContent):
    text = str()
    tables = list()
    with pdfplumber.open(BytesIO(blobContent)) as pdf:
        for page in pdf.pages:
            # Extract text normally
            page_text = page.extract_text() or ""
            text += page_text

            # Extract tables separately
            extractedTables = page.extract_tables()
            if extractedTables:
                tables.append(extractedTables)
    return text, tables

def processPdfContent(blobContent, fileName,searchServiceEndpoint,credential,indexName):
    # try:        
        logging.info("Camer here")
        text, tables= extractContentFromPdf(blobContent)
        table_strings = []
        for table in tables:
            table_string = '\n'.join([' | '.join([str(cell) for cell in row]) for row in table])
            table_strings.append(table_string)
        combined_content = '\n\n'.join([text] + table_strings)

        chunks =  chunkText(combined_content)
        if(len(chunks)>0):
            documents = list()
            fileId = fileName
            for chunkCount, chunk in enumerate(chunks,1):
                contentVector = generateEmbeddings(chunk)
                fileId = fileName.replace('.', '_')
                key = fileId + '_' + str(chunkCount)
                uploadDocument = generateDocument(key,chunk,contentVector,fileName,fileId)
                documents.append(uploadDocument)
                logging.info('DONE')
            uploadDocumentToIndex(documents,searchServiceEndpoint,credential,indexName)
    # except Exception as  e:
    #     logging.info(e)

def chunkText(text, chunkSize=1024, chunk_overlap=0):
    try:
        openaiModel = Config.AZURE_OPENAI_EMBEDDING_MODEL
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name=str(openaiModel),
            chunk_size=chunkSize,
            chunk_overlap=chunk_overlap
        )
        chunks=splitter.split_text(text)
        return chunks
    except Exception as e:
        logging.info("Error in  ChunkText"+e)

def generateEmbeddings(chunks):
    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_key=Config.AZURE_OPENAI_KEY,
        api_version=Config.AZURE_OPENAI_VERSION
    )
    for retry in range (int(10)):
        try:
            response = client.embeddings.create(
                model=Config.AZURE_OPENAI_EMBEDDING_MODEL,
                input=chunks
            )
            if(response.data != None):
                return response.data[0].embedding
            else:
                return str()
        except Exception as e:
            logging.info('Error in Generate Embeddings'+e)


def generateDocument(key, chunk, vector,fileName,fileId):
    document = {
        'id': key,
        'content': chunk,
        'contentVector': vector,
        'fileName': fileName,
        'fileId':  fileId
    }
    return document

def uploadDocumentToIndex(document, searchServiceEndpoint, credential, indexName):
    try:
        logging.info('CAME TO UPLOAD DOCUMENT')
        searchClient = SearchClient(endpoint=searchServiceEndpoint, credential=credential, index_name=indexName)
        searchClient.upload_documents(documents=document)
        logging.info("Document Uploaded")
    except Exception as e:
        logging.info(e)    