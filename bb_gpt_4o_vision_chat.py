import base64
import difflib
import json
import logging
import os
from typing import Any, Generator

import openai
import pymupdf
import structlog

from a_ingestion import load_pdfs_and_manual_extraction
from models import ExtractedInvoice

logger = structlog.stdlib.get_logger()


def pdf_to_images(pdf_path: str) -> Generator[bytes, None, None]:
    logger.debug("opening pdf", pdf_path=pdf_path)
    doc = pymupdf.Document(pdf_path)
    logger.info("pdf details", pdf_path=pdf_path, pdf_page_count=len(doc))
    for page in doc:
        p: Any = page
        pix: pymupdf.Pixmap = p.get_pixmap(dpi=138)
        b = pix.tobytes()
        yield b


# Function to extract information from images using GPT-4o API
def extract_invoice_info_from_pdf(pdf_path):
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {
                "role": "system",
                "content": "You are an accounts payable clerk."
                + " You extract information from submitted PDF invoices and call the provided function."
                + " Unless otherwise instructured, preserve the case and formatting as is from the PDF."
                + " It is okay to leave fields blank if you don't know.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Generate a data object from this PDF"},
                    *(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64.b64encode(b).decode('utf-8')}"
                            },
                        }
                        for b in pdf_to_images(pdf_path)
                    ),
                ],
            },
        ],
        tool_choice={"type": "function", "function": {"name": "extract_invoice_info"}},
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_invoice_info",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "InvoiceHeaderInfo": {
                                "type": "object",
                                "properties": {
                                    "SalesTaxAmount": {"type": "number"},
                                    "ShippingCharges": {"type": "number"},
                                    "InvoiceNumber": {"type": "string"},
                                    "InvoiceAmount": {"type": "number"},
                                    "InvoiceDate": {
                                        "type": "string",
                                        "description": "Use YYYY-MM-DDTHH:mm:SS format, and specify 00:00:00 if the time is not known.",
                                    },
                                    "PurchaseOrder": {
                                        "type": "string",
                                        "description": "Usually an abbreviation, like PO. Do NOT use the 'Sales Order' or 'Invoice #' or 'Customer #' or similar as the purchase order.",
                                    },
                                    "VendorContactInfo": {
                                        "type": "object",
                                        "description": "Under a remit to or other vendor stated section. Do not use the purchaser's contact information.",
                                        "properties": {
                                            "ContactName": {"type": "string"},
                                            "ContactAddress1": {"type": "string"},
                                            "ContactAddress2": {"type": "string"},
                                            "ContactCity": {"type": "string"},
                                            "ContactState": {"type": "string"},
                                        },
                                    },
                                },
                                "required": [
                                    "InvoiceAmount",
                                    "InvoiceDate",
                                    "VendorNumber",
                                ],
                            },
                            "InvoiceLineItems": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "description": "Make sure to capture ALL line items on the document. Capture each item. Look for horizontal entries which have a price in them on the far right side.",
                                    "properties": {
                                        "ItemDescription": {
                                            "type": "string",
                                            "description": "Do not correct typos in the source document.",
                                        },
                                        "Quantity": {"type": "number"},
                                        "LineItemNetTotal": {"type": "number"},
                                        "LineItemTotal": {"type": "number"},
                                        "SupplierPartNum": {
                                            "type": "string",
                                            "description": "This may be called 'Model', 'Product', or similar names.",
                                        },
                                        "UnitOfMeasure": {"type": "string"},
                                        "UnitPrice": {"type": "number"},
                                    },
                                    "required": [
                                        "ItemDescription",
                                        "LineItemTotal",
                                    ],
                                },
                            },
                        },
                        "required": ["InvoiceHeaderInfo", "InvoiceLineItems"],
                    },
                },
            }
        ],
    )

    logger.info(
        "model response for extract_invoice_info",
        llm_usage=response.usage.model_dump(),  # pyright: ignore[reportOptionalMemberAccess]
    )
    raw = json.loads(
        response.choices[0]  # pyright: ignore[reportOptionalSubscript]
        .message.tool_calls[0]  # pyright: ignore[reportOptionalSubscript]
        .function.arguments
    )
    e = ExtractedInvoice(**raw)
    return e.model_dump()


# Example usage
if __name__ == "__main__":
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
    )
    _, pdfs_with_manual_extractions, _ = load_pdfs_and_manual_extraction()
    for i, invoice in enumerate(pdfs_with_manual_extractions.values()):
        if i >= 3:
            break
        print(invoice.file_path)

        ai_bb_invoice = extract_invoice_info_from_pdf(invoice.file_path)

        manual_invoice = json.dumps(
            invoice.to_extracted().model_dump(), indent=4, sort_keys=True
        )
        ai_bb_invoice = json.dumps(ai_bb_invoice, indent=4, sort_keys=True)

        diff = difflib.unified_diff(
            manual_invoice.splitlines(),
            ai_bb_invoice.splitlines(),
            fromfile="manual_invoice",
            tofile="ai_bb_invoice",
            lineterm="",
            n=10,
        )

        for line in diff:
            print(line)
