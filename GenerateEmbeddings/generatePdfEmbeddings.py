from azure.storage.blob import BlobServiceClient
from config import Config
from utilities import constants
import logging
from utilities.processPdf import processPdfContent
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models  import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration
)

azureAccessKey = Config.AZURE_STORAGE_ACCESS_KEY
azureAccountName = Config.AZURE_STORAGE_ACCOUNT_NAME
azureBlobContainerName = Config.AZURE_BLOB_CONTAINER_NAME
azureConnectionString = constants.CONNECTION_STRING.format(azureAccountName=azureAccountName, azureAccessKey=azureAccessKey)
azureSearchEndpoint= Config.AZURE_SEARCH_ENDPOINT
azureSearchKey= Config.AZURE_SEARCH_KEY
credential=AzureKeyCredential(azureSearchKey)
azureIndexName=Config.AZURE_INDEX_NAME


def blobTrigger():
    # try:
        createIndex = createAzureIndex(azureSearchEndpoint,credential,azureIndexName)
        logging.info(createIndex)
        processedFileCount = 0
        blobContainerName = azureBlobContainerName
        blobServiceClient = BlobServiceClient.from_connection_string(azureConnectionString)
        containerClient =  blobServiceClient.get_container_client(blobContainerName)

        for blob in containerClient.list_blobs():
            blobName = blob.name
            blobClient = containerClient.get_blob_client(blobName)
            blobUrl  = blobClient.url
            blobContent  = blobClient.download_blob().readall()
            document = processPdfContent(blobContent, blobName, azureSearchEndpoint,credential,azureIndexName)
        return len(blob)
    # except Exception as e:
    #     logging.info(e)

def createAzureIndex(azureSearchEndpoint,credential,indexName):
    #Process to create index for text
    fields=[
            SimpleField(name='id', type=SearchFieldDataType.String, key=True,sortable=True, filterable=True, facetable=True),
            SearchableField(name='content', type=SearchFieldDataType.String,Searchable=True),
            SearchableField(name='fileName', type=SearchFieldDataType.String),
            SearchableField(name='fileId', type=SearchFieldDataType.String),
            SearchField(name='contentVector', type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, hidden=False,vector_search_dimensions=int(1536),  vector_search_profile_name="myHnswProfile")
        ]

    # Configure the vector search configuration
    vectorSearch = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
            )
        ]
    )

    # Optional: configure semantic reranking by passing your title, keywords, and content fields
    semanticConfig = SemanticConfiguration(
        name='my-semantic-config',
        prioritized_fields=SemanticPrioritizedFields(
        title_field=SemanticField(field_name='fileName'),
        keywords_fields=[SemanticField(field_name='fileName'),SemanticField(field_name='fileId')],
        content_fields=[SemanticField(field_name='content'),SemanticField(field_name='fileName'),SemanticField(field_name='fileId')]
    )
    )
    # Create the semantic settings with the configuration
    semanticSettings = SemanticSearch(configurations=[semanticConfig])

    indexClient = SearchIndexClient(
        endpoint=azureSearchEndpoint, credential=credential)

    indexExist = any(index == indexName for index in indexClient.list_index_names())

    # Create the index 
    if(indexExist is not True):
        index = SearchIndex(name=indexName, fields=fields, vector_search=vectorSearch, semantic_search=semanticSettings)
        result = indexClient.create_or_update_index(index)
        return f"{result.name} created"
    else:
        return "Index Already Exists"