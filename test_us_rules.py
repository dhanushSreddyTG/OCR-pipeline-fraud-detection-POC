import os
import sys
import json
import pytesseract
from PIL import Image

# Ensure project root and rule-engine directory are in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule-engine"))

from processors.registry import DocumentProcessorRegistry
from validator import DocumentRuleValidator

US_DOCS_DIR = "./US-docs"

def main():
    print("=" * 80)
    print("STARTING RULE ENGINE VERIFICATION FOR US DOCUMENTS")
    print("=" * 80)

    files = [
        ("california-dl.jpg", "US_DL_CA"),
        ("florida-dl.jpg", "US_DL_FL"),
        ("state-university-of-new-york.jpg", "SUNY_TRANSCRIPT"),
        ("us-bank-statement.jpg", "US_BANK_STATEMENT")
    ]

    success_count = 0

    for filename, doc_type in files:
        filepath = os.path.join(US_DOCS_DIR, filename)
        print("\n" + "-"*60)
        print(f"File: {filename}")
        print(f"Document Type: {doc_type}")
        print("-"*60)

        if not os.path.exists(filepath):
            print(f"Error: {filepath} not found!")
            continue

        try:
            # 1. Run OCR
            img = Image.open(filepath)
            raw_text = pytesseract.image_to_string(img)
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            # 2. Extract Data via Processor
            extracted_data = DocumentProcessorRegistry.extract_document(raw_text, lines)
            print("Extracted Data successfully.")

            # 3. Mock font info / visual details
            font_info = {
                "character_misalignment": 0,
                "font_size_anomaly": False,
                "multiple_fonts_detected": False
            }

            # 4. Evaluate Rules via Validator
            rule_report = DocumentRuleValidator.validate(
                doc_type=doc_type,
                extracted_data=extracted_data,
                full_text=raw_text,
                lines=lines,
                font_info=font_info,
                file_path=filepath
            )

            print("Rule Validation Report:")
            print(json.dumps(rule_report, indent=2))
            
            success_count += 1
        except Exception as e:
            print(f"Rule Engine validation FAILED for {filename}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"RULE ENGINE VERIFICATION SUMMARY: {success_count}/{len(files)} documents audited successfully")
    print("=" * 80)

    if success_count == len(files):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
