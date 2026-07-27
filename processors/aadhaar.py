import re
from typing import Dict, Any
from .base import BaseDocumentProcessor

class AadhaarProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "Aadhaar Card",
        }
        
        # Use finditer to find all 12-digit candidates and pick the most likely one
        candidates = list(re.finditer(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text))
        best_num = None
        
        if candidates:
            for match in candidates:
                best_num = match.group(1).replace(" ", "")
                break # Take the first matching pattern
            
            if best_num:
                data["aadhaar_number"] = f"{best_num[:4]} {best_num[4:8]} {best_num[8:]}"

        dob_patterns = [
            r"(?:DOB|Date\s*of\s*Birth)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})", 
            r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b"
        ]
        for p in dob_patterns:
            dob_match = re.search(p, text, re.IGNORECASE)
            if dob_match:
                found_date = dob_match.group(1).replace("/", "-")
                if "2026" not in found_date and "2025" not in found_date:
                    data["dob"] = found_date
                    break
            
        if "dob" not in data:
             yob_match = re.search(r"Year\s*of\s*Birth\s*[:\-]?\s*(\d{4})", text, re.IGNORECASE)
             if yob_match:
                 data["dob"] = f"01-01-{yob_match.group(1)}"
        
        if "gender" not in data:
            data["gender"] = self.extract_gender_normalized(text)
            
        lines = [line.strip() for line in full_text_lines if line.strip()]
        
        # Name extraction logic
        addr_markers = ["to,", "to:", "address:", "address :"]
        for i, line in enumerate(lines):
            if any(m in line.lower() for m in addr_markers):
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate.lower() for x in ["govt", "india", "uidai", "enrollment", "dob", "year", "male", "female"]):
                        if not self.is_likely_address(candidate):
                            data["name"] = candidate.strip()
                            break

        parentage_markers = ["s/o", "w/o", "d/o", "c/o", "m/o", "f/o", "slo", "wlo", "dlo"]
        for i, line in enumerate(lines):
            if any(m in line.lower() for m in parentage_markers):
                if i - 1 >= 0:
                    candidate = lines[i-1]
                    if not any(x in candidate.lower() for x in ["govt", "india", "unique", "authorit", "enrollment"]):
                        cand_strip = candidate.strip()
                        if len(cand_strip) >= 3 and len(cand_strip.split()) >= 2 and not any(c.isdigit() for c in cand_strip):
                            data["name"] = cand_strip
                            break

        header_patterns = ["government of india", "bhaarat sarakaar", "unique identification"]
        for i, line in enumerate(lines):
            if any(h in line.lower() for h in header_patterns):
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j]
                    if any(x in candidate.lower() for x in ["enrollment", "help", "www", "dob", "year", "male", "female", "uidai"]):
                        continue
                    if len(candidate.split()) >= 2 and (re.match(r"^[A-Z][a-zA-Z\.\s]+$", candidate) or re.match(r"^[A-Z\s]+$", candidate)):
                        cand_strip = candidate.strip()
                        if len(cand_strip) >= 3 and len(cand_strip.split()) >= 2 and not any(c.isdigit() for c in cand_strip):
                            data["name"] = cand_strip
                            break
                break

        if "aadhaar_number" in data:
            target_no = data["aadhaar_number"]
            for i, line in enumerate(lines):
                if target_no in line or target_no.replace(" ", "") in line:
                    for j in range(i - 1, max(-1, i - 5), -1):
                        candidate = lines[j]
                        if any(x in candidate.lower() for x in ["govt", "india", "unique", "authorit", "enrollment", "dob", "year", "male", "female"]):
                             continue
                        if len(candidate.split()) >= 2 and (re.match(r"^[A-Z][a-zA-Z\.\s]+$", candidate) or re.match(r"^[A-Z\s]+$", candidate)):
                             cand_strip = candidate.strip()
                             if len(cand_strip) >= 3 and not any(c.isdigit() for c in cand_strip):
                                 data["name"] = cand_strip
                                 break

        addr_trigger = re.search(r"(?:Address|Address\s*:)\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        if addr_trigger:
            raw_addr = addr_trigger.group(1).strip()
            stop_words = ["help@uidai", "www.uidai", "1947", "Unique Identification"]
            for stop in stop_words:
                if stop.lower() in raw_addr.lower():
                    raw_addr = raw_addr[:raw_addr.lower().find(stop.lower())].strip()
            
            raw_addr = re.sub(r"\d{4}\s?\d{4}\s?\d{4}.*", "", raw_addr).strip()
            raw_addr = raw_addr.lstrip(":/ ").strip()
            if len(raw_addr) > 10:
                data["address"] = raw_addr
        return data
