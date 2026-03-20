import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID
from uuid import uuid5

import pyarrow as pa
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter
from docling.document_converter import PdfFormatOption
from docling.utils.model_downloader import download_models
from langchain_pinecone import PineconeEmbeddings
from nxd.data_product.context import AzureDataLakeStorage
from pinecone.core.openapi.inference.model.embeddings_list import EmbeddingsList
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed
from utils import parquet_to_adls

_logger = logging.getLogger("transform.main")
_logger.setLevel(logging.INFO)


def transform(
    # pinecone: PineconeOutput,
    adls: AzureDataLakeStorage,
) -> None:
    _logger.info("Starting aps-330-public-disclosure transformation...")

    # read
    documents = [
        (
            "Westpac Banking Corporation",
            "https://www.westpac.com.au/content/dam/public/wbc/documents/pdf/aw/ic/wbc-pillar-3-report-march-2025.pdf",
        ),
        (
            "Australia and New Zealand Banking Group Limited",
            "https://www.anz.com/content/dam/anzcom/shareholder/2025-half-year-results-announcement/march-2025-pillar3-disclosure.pdf",
        ),
        (
            "Macquarie Group Limited",
            "https://www.macquarie.com/assets/macq/investor/regulatory-disclosures/2025/mbl-basel-III-pillar-3-capital-disclosures-mar-2025-restated.pdf",
        ),
    ]

    # transform

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(60))
    def _embed_texts(self, texts: list[str], model: str, parameters: dict) -> EmbeddingsList:
        return self._client.inference.embed(model=model, inputs=texts, parameters=parameters)

    # monkey patch to enforce backoff
    PineconeEmbeddings._embed_texts = _embed_texts

    # embeddings = PineconeEmbeddings(
    #     model="llama-text-embed-v2",
    #     api_key=pinecone.password,  # type: ignore
    # )

    # vectorstore = PineconeVectorStore(
    #     # index_name=pinecone.index,
    #     index_name="finance-documents-pilot",  # indexes set within manifest.yaml are not respected and will always default to the data product name
    #     namespace=pinecone.namespace,
    #     pinecone_api_key=pinecone.password,
    #     embedding=embeddings,
    # )

    docling_artifacts_path = Path.home() / "docling" / "models"

    _logger.info(f"Downloading Docling Models to: {docling_artifacts_path}")
    download_models(output_dir=docling_artifacts_path)

    pipeline_options = PdfPipelineOptions(artifacts_path=docling_artifacts_path)
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )

    uuid_namespace = UUID("00000000-0000-0000-0000-000000000000")

    disclosures = []
    for company, url in documents:
        conversion = converter.convert(url)
        _logger.info(f"File: {url} processed by Docling")

        document = conversion.document
        markdown = document.export_to_markdown()
        filename = Path(url).name
        processed_at = datetime.now()
        metadata = {
            "document_id": str(uuid5(uuid_namespace, url)),
            "company": company,
            "filename": filename,
            "url": url,
            "pages": len(document.pages),
            "tables": len(document.tables),
            "doc_elements": len(document.texts),
            "document_hash": (str(document.origin.binary_hash) if document.origin else None),
            "size": len(markdown),
            "source": filename,
        }

        # chunk and write to Pinecone
        #  avoid use of langchain_docling.loader.DoclingLoader so we can access "true"
        #  DoclingDocument for use within the PyArrow Table
        # chunker = HybridChunker(
        #     tokenizer=OpenAITokenizer(
        #         tokenizer=tiktoken.encoding_for_model("gpt-4o-mini"),
        #         max_tokens=2048,  # llama-text-embed-v2 max input tokens
        #     )
        # )
        # vectorstore.add_documents(
        #     documents=[
        #         Document(
        #             page_content=chunker.serialize(chunk=chunk),
        #             metadata=metadata | {"processed_at": processed_at.isoformat()},
        #         )
        #         for chunk in chunker.chunk(document)
        #     ],
        #     batch_size=64,
        #     id_prefix=filename,
        # )
        _logger.info(f"Documents from: {url} written to Pinecone")

        # PyArrow records
        document = metadata | {
            "contents": markdown,
            "processed_at": processed_at,
        }
        disclosures.append(document)

        _logger.info(f"File: {url} processed by Docling")

    table = pa.Table.from_pylist(disclosures)

    parquet_to_adls(
        adls,
        table,
        adls.model_paths["disclosures"].path,
    )

    _logger.info("Transform completed successfully")
