import re
from typing import Dict, Any
from .base import BaseDocumentProcessor

class PanProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {"document_type": "PAN Card"}
        pan_match = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", text)
        if pan_match: 
            data["pan_number"] = pan_match.group(0)
            
        dob_match = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text)
        if dob_match: 
            data["dob"] = dob_match.group(1).replace('/', '-')
            
        lines = [line.strip() for line in full_text_lines if line.strip()]
        for i, line in enumerate(lines):
            if "Father" in line or "Mother" in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Signature", "Date", "DOB"]):
                         data["father_name"] = candidate
                         
            if "Name" in line and "Father" not in line and "Mother" not in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Father", "Mother"]):
                        if not self.is_likely_address(candidate):
                             data["name"] = candidate
        return data
