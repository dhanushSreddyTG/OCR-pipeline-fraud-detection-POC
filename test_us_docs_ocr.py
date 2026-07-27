import os
import sys
import json
import pytesseract
from PIL import Image

# Ensure the project root is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processors.registry import DocumentProcessorRegistry
from schemas.california_dl_schema import CaliforniaDLSchema
from schemas.florida_dl_schema import FloridaDLSchema
from schemas.suny_transcript_schema import SUNYTranscriptSchema
from schemas.us_bank_statement_schema import USBankStatementSchema

US_DOCS_DIR = "./US-docs"

def main():
    print("=" * 70)
    print("STARTING US DOCUMENTS OCR & PIPELINE VERIFICATION")
    print("=" * 70)

    files = [
        ("california-dl.jpg", "US_DL_CA", CaliforniaDLSchema),
        ("florida-dl.jpg", "US_DL_FL", FloridaDLSchema),
        ("state-university-of-new-york.jpg", "SUNY_TRANSCRIPT", SUNYTranscriptSchema),
        ("us-bank-statement.jpg", "US_BANK_STATEMENT", USBankStatementSchema)
    ]

    success_count = 0

    for filename, expected_type, schema_class in files:
        filepath = os.path.join(US_DOCS_DIR, filename)
        print("\n" + "-"*50)
        print(f"File: {filename}")
        print(f"Expected Class: {expected_type}")
        print("-"*50)

        if not os.path.exists(filepath):
            print(f"Error: File {filepath} not found!")
            continue

        try:
            # 1. Run OCR to extract text
            img = Image.open(filepath)
            raw_text = pytesseract.image_to_string(img)
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            # 2. Extract dynamically via the pipeline registry
            extracted_data = DocumentProcessorRegistry.extract_document(raw_text, lines)
            
            # Print dynamically classified type
            classified_type = extracted_data.get("document_type", "Unknown")
            print(f"Dynamic Classification: {classified_type}")

            # Print raw parsed fields
            print("Extracted Data Fields:")
            print(json.dumps(extracted_data, indent=2))

            # 3. Validate against Pydantic Schema
            # Cast the dict to the pydantic schema
            # We map registry classification key to actual schemas (since registry doc_type might have spaces/casing)
            schema_instance = schema_class(**extracted_data)
            print(f"Pydantic Validation: SUCCESS")
            print(f"Validated Schema Dump:")
            print(schema_instance.model_dump_json(indent=2))
            
            success_count += 1
        except Exception as e:
            print(f"Verification FAILED for {filename}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {success_count}/{len(files)} documents parsed & validated successfully")
    print("=" * 70)
    
    if success_count == len(files):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
