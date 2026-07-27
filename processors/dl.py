import re
from typing import Dict, Any
from .base import BaseDocumentProcessor

class DrivingLicenseProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {"document_type": "Driving License"}
        
        # DL Number Regex
        dl_patterns = [
            r"\b([A-Z]{2}\s*\d{2}\s*\d{4}\s*\d{4,11})\b",
            r"(?:DL|LICENCE)\s*NO\.?\s*[:\- \.]+\s*([A-Z0-9\s]+)",
            r"\b([A-Z]{2}\d{2}\s\d{11})\b"
        ]
        
        for p in dl_patterns:
            dl_match = re.search(p, text, re.IGNORECASE)
            if dl_match:
                raw_dl = dl_match.group(1).strip()
                clean_dl = re.sub(r"[^A-Z0-9]", "", raw_dl.upper())
                if len(clean_dl) >= 10:
                    data["dl_number"] = clean_dl
                    break
        dob_match = re.search(r"D\.?O\.?B\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE)
        if not dob_match:
            dob_match = re.search(r"D\.?O\.?B.*?(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE | re.DOTALL)
        if dob_match: 
            data["dob"] = dob_match.group(1).replace("/", "-")
        
        # Address Extraction
        addr_match = re.search(r"ADDRESS\s*[:\-]?\s*(.*?)(?=Sign\.|CHANDAPURA|BENGALURU RTO|$)", text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            data["address"] = re.sub(r"\s+", " ", addr_match.group(1).strip())
        
        lines = [l.strip() for l in full_text_lines if l.strip()]
        for i, line in enumerate(lines):
            line_upper = line.upper()
            if "NAME" in line_upper and "FATHER" not in line_upper:
                if ":" in line:
                    data["name"] = line.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    data["name"] = lines[i+1]
            if "S/O" in line_upper or "D/O" in line_upper or "FATHER" in line_upper:
                 if ":" in line:
                    data["father_name"] = line.split(":", 1)[1].strip()
                 elif i + 1 < len(lines):
                    data["father_name"] = lines[i+1]

        # Clean leading punctuation from names
        if "name" in data:
            data["name"] = re.sub(r"^[^A-Za-z0-9]+", "", data["name"]).strip()
        if "father_name" in data:
            data["father_name"] = re.sub(r"^[^A-Za-z0-9]+", "", data["father_name"]).strip()

        return data
