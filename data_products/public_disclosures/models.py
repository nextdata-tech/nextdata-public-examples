# ruff: noqa: F403, F405
from nxd_models import *

disclosures = (
    semantic_model(
        name="disclosures",
        description="Parsed representation of APS 330 Public Disclosure documents, including metadata, extracted text, and structural elements for analysis.",
    )
    .sampling(method=SamplingMethod.Head)
    .schema(
        {
            "document_id": (
                string(),
                "Unique identifier assigned to the disclosure document in the system.",
            ),
            "company": (
                string(),
                "Name of the financial institution or entity publishing the APS 330 Public Disclosure.",
            ),
            "filename": (
                string(),
                "Original filename of the uploaded or processed document.",
            ),
            "url": (
                string(),
                "Direct link to the document source or downloadable file.",
            ),
            "contents": (
                string(),
                "Full extracted text content of the PDF disclosure.",
            ),
            "pages": (
                int64(),
                "Total number of pages in the disclosure document.",
            ),
            "tables": (
                int64(),
                "Count of tabular data elements extracted from the document.",
            ),
            "doc_elements": (
                int64(),
                "Total number of structured elements (e.g., headings, paragraphs, tables, lists) identified in the parsed output.",
            ),
            "document_hash": (
                string(),
                "Cryptographic hash of the document file used to verify integrity and detect duplicates.",
            ),
            "size": (
                int64(),
                "File size of the document in bytes.",
            ),
            "processed_at": (
                timestamp(unit=DurationUnit.Nanoseconds),
                "Timestamp of when the document was parsed and processed, stored in nanosecond precision.",
            ),
        }
    )
)
