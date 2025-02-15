import azure.functions as func
from GenerateEmbeddings import generatePdfEmbeddings
import logging

async def main(req: func.HttpRequest, starter: str) ->  func.HttpResponse:
    response = generatePdfEmbeddings.blobTrigger()
    return "Uploaded"
