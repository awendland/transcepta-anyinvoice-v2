import collections
import glob
import json
from typing import Dict, List, Tuple, cast

import duckdb
import pymupdf

from models import Invoice, InvoiceDenormalized

INFIX_INVOICES_MANUAL_EXTRACT_INFO = (
    "2024-07-01_Prod_Infinx_Invoices_2024-6-3to17_AllInfo_v2.json"
)
PDFS_FOR_COMPARISON_DIR = "2024-06-20_AI_Testing_3"


def load_pdfs_and_manual_extraction() -> (
    Tuple[duckdb.DuckDBPyConnection, Dict[str, Invoice], List[str]]
):
    # Create an in-memory DuckDB connection
    con = duckdb.connect(database=":memory:")

    # Execute the query to load the data
    con.execute(
        f"""
        CREATE TABLE prod_data AS 
        SELECT * FROM read_json_auto('{INFIX_INVOICES_MANUAL_EXTRACT_INFO}')
    """
    )

    pdfs_with_manual_extractions = collections.OrderedDict[str, Invoice]()
    missing_item_ids = []
    for file_path in sorted(glob.glob(f"{PDFS_FOR_COMPARISON_DIR}/*/*/*")):
        # dir1 is "message id" which is not in the JSON (note from Chris's slack on 2024-07-01)
        _, dir1, og_msg_item_id, file = file_path.split("/")
        query = (
            f"SELECT * FROM prod_data WHERE OriginalMessageItemId = '{og_msg_item_id}'"
        )
        cursor = con.execute(query)
        items = list(InvoiceDenormalized.from_db_cursor(cursor))
        if len(items) == 0:
            missing_item_ids.append(og_msg_item_id)
        else:
            invoice = Invoice.from_denormalized(items, file_path)
            pdfs_with_manual_extractions[og_msg_item_id] = invoice

    return con, pdfs_with_manual_extractions, missing_item_ids


if __name__ == "__main__":
    (
        con,
        pdfs_with_manual_extractions,
        missing_item_ids,
    ) = load_pdfs_and_manual_extraction()

    # Print out the table
    schema = con.execute("DESCRIBE prod_data").fetchall()
    print("Table Schema:")
    for column in schema:
        print(f"\t{column[0]} {column[1]}")
    # Print the number of rows in the table
    row_count = cast(
        Tuple[int], con.execute("SELECT COUNT(*) FROM prod_data").fetchone()
    )[0]
    print(f"Number of rows in the table: {row_count}")

    print(f"Number of pdfs with manual extraction: {len(pdfs_with_manual_extractions)}")
    print(f"Number of missing OriginalMessageItemIds: {len(missing_item_ids)}")
    if pdfs_with_manual_extractions:
        first_valid_item_key = next(iter(pdfs_with_manual_extractions))
        first_valid_item = pdfs_with_manual_extractions[first_valid_item_key]
        print(f"First item (OriginalMessageItemId: {first_valid_item_key}):")
        print(f"Number of line items for the entry: {len(first_valid_item.line_items)}")
        print(json.dumps(first_valid_item.to_dict(), indent=4))
        # TBD: we now have the raw validation data to start the new LLM's pipeline around Invoice.file_path.
        # TBD: we also need to figure out performance of this existing pipeline, which means ingesting data from Chris's folder and comparing it against the .json.
    else:
        print("No valid items found.")

    page_count_dict = collections.defaultdict(int)
    page_paths_dict = collections.defaultdict(list)
    for file_path in glob.glob(f"{PDFS_FOR_COMPARISON_DIR}/*/*/*"):
        if file_path.endswith(".pdf"):
            doc = pymupdf.open(file_path)
            num_pages = len(doc)
            page_count_dict[num_pages] += 1
            if num_pages > 10:
                page_paths_dict[num_pages].append(file_path)
    print("Number of documents for each page length:")
    for num_pages, count in sorted(page_count_dict.items()):
        print(f"\t{num_pages} pages: {count} document(s)")
        if num_pages > 10:
            for path in page_paths_dict[num_pages]:
                print(f"\t\t{path}")
