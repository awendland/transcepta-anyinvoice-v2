import os
from pathlib import Path

import openai


# Function to upload PDF and extract information
def extract_invoice_info_from_pdf(pdf_path):
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    f = client.files.create(file=pdf_path, purpose="assistants")

    assistant = client.beta.assistants.create(
        model="gpt-4o-2024-05-13",
        instructions="You are an accounts payable clerk. You extract information from submitted PDF invoices and call the provided function.",
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
                                    "InvoiceDate": {"type": "string"},
                                    "VendorNumber": {"type": "string"},
                                    "PurchaseOrder": {"type": "string"},
                                },
                                "required": [
                                    "SalesTaxAmount",
                                    "ShippingCharges",
                                    "InvoiceNumber",
                                    "InvoiceAmount",
                                    "InvoiceDate",
                                    "VendorNumber",
                                    "PurchaseOrder",
                                ],
                            },
                            "InvoiceLineItems": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "ItemDescription": {"type": "string"},
                                        "UnitOfMeasure": {"type": "string"},
                                        "UnitPrice": {"type": "number"},
                                        "Quantity": {"type": "number"},
                                        "LineItemNetTotal": {"type": "number"},
                                        "LineItemTotal": {"type": "number"},
                                        "SupplierPartNum": {"type": "string"},
                                    },
                                    "required": [
                                        "ItemDescription",
                                        "UnitOfMeasure",
                                        "UnitPrice",
                                        "Quantity",
                                        "LineItemNetTotal",
                                        "LineItemTotal",
                                        "SupplierPartNum",
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

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Call extract_invoice_info for the provided file",
        attachments=[{"file_id": f.id, "tools": [{"type": "file_search"}]}],
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )

    if run.required_action:
        print(run.required_action.submit_tool_outputs.to_json(indent=4))
    else:
        print("model did not call the tool")
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        print(messages)
        print(run.status)


# Example usage
pdf_path = Path(
    "2024-06-20_AI_Testing_3/105325341/115250086/invoice_30652556_665a29b897ae4.pdf"
)
invoice_info = extract_invoice_info_from_pdf(pdf_path)
# print(json.dumps(invoice_info, indent=2))
