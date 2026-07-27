import re
from typing import Dict, Any
from .base import BaseDocumentProcessor

class PassportProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {"document_type": "Passport"}
        
        # 1. Broad search for passport number (accepts 1 or 2 prefix letters, and 6 or 7 digits)
        passport_match = re.search(r"\b([A-Z]{1,2}[0-9]{6,7})\b", text)
        if passport_match: 
            data["passport_number"] = passport_match.group(1)
        
        data["gender"] = self.extract_gender_normalized(text)
        
        # 2. Extract slash-based dates
        date_candidates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
        if len(date_candidates) >= 3:
            data["dob"] = date_candidates[0].replace("/", "-")
            data["doi"] = date_candidates[1].replace("/", "-")
            data["doe"] = date_candidates[2].replace("/", "-")
        elif len(date_candidates) == 2:
            data["doi"] = date_candidates[0].replace("/", "-")
            data["doe"] = date_candidates[1].replace("/", "-")

        lines = [l.strip() for l in full_text_lines if l.strip()]
        for i, line in enumerate(lines):
            line_clean = line.replace(" ", "")
            
            # --- MRZ Line 1 parsing ---
            if line_clean.startswith("P<") or (line_clean.startswith("P") and "<<" in line_clean):
                mrz_name_part = line_clean[2:] if line_clean.startswith("P<") else line_clean[1:]
                # The next 3 characters are the country code (e.g. IND)
                if len(mrz_name_part) > 3:
                    mrz_name_part = mrz_name_part[3:]
                if "<<" in mrz_name_part:
                    parts = mrz_name_part.split("<<")
                    surname = parts[0].replace("<", " ").strip()
                    given_name = parts[1].replace("<", " ").strip()
                    data["surname"] = surname
                    data["given_names"] = given_name
                    data["name"] = f"{given_name} {surname}".strip()
            
            # --- MRZ Line 2 parsing ---
            passport_num_match = re.match(r"^([A-Z]{1,2}[0-9]{6,7})", line_clean)
            if passport_num_match and len(line_clean) > 25:
                passport_no = passport_num_match.group(1)
                data["passport_number"] = passport_no
                
                # Extract details based on standard ICAO Doc 9303 layout (second line)
                if len(line_clean) >= 27:
                    # DOB at indices 13-18 (format YYMMDD)
                    dob_raw = line_clean[13:19]
                    if dob_raw.isdigit():
                        yy = dob_raw[0:2]
                        mm = dob_raw[2:4]
                        dd = dob_raw[4:6]
                        data["dob"] = f"{dd}-{mm}-20{yy}" if int(yy) <= 30 else f"{dd}-{mm}-19{yy}"
                    
                    # Gender at index 20
                    gender_raw = line_clean[20]
                    if gender_raw in ["M", "F"]:
                        data["gender"] = gender_raw
                    
                    # Expiry at indices 21-26 (format YYMMDD)
                    doe_raw = line_clean[21:27]
                    if doe_raw.isdigit():
                        yy = doe_raw[0:2]
                        mm = doe_raw[2:4]
                        dd = doe_raw[4:6]
                        data["doe"] = f"{dd}-{mm}-20{yy}"
            
            # --- Text-based fallback checks ---
            line_upper = line.upper()
            if "DATE OF BIRTH" in line_upper or "D.O.B" in line_upper:
                match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                if match: 
                    data["dob"] = match.group(1).replace("/", "-")
            if "DATE OF ISSUE" in line_upper or "D.O.I" in line_upper:
                match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                if match: 
                    data["doi"] = match.group(1).replace("/", "-")
            if "DATE OF EXPIRY" in line_upper or "D.O.E" in line_upper:
                match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                if match: 
                    data["doe"] = match.group(1).replace("/", "-")
            if "NATIONALITY" in line_upper:
                if ":" in line: 
                    data["nationality"] = line.split(":", 1)[1].strip()
            if "PLACE OF ISSUE" in line_upper:
                if i + 1 < len(lines): 
                    data["place_of_issue"] = lines[i+1].strip()

            # --- Visual Name Field Fallbacks (for documents lacking MRZ) ---
            # Handled outside the line loop to leverage global line positioning and layout context
            pass

        # --- Layout-based visual name parser ---
        # 1. Search for Given Names marker
        given_idx = -1
        surname_idx = -1
        for idx, line in enumerate(lines):
            line_upper = line.upper()
            if "GIVEN" in line_upper or "NOMES" in line_upper or ("NAMES" in line_upper and "SURNAME" not in line_upper):
                given_idx = idx
            if "SURNAME" in line_upper:
                surname_idx = idx

        # Extract Given Names if marker found
        extracted_given = ""
        if given_idx != -1:
            collected = []
            for j in range(given_idx + 1, min(given_idx + 5, len(lines))):
                next_line = lines[j].strip()
                next_upper = next_line.upper()
                # Stop conditions
                if any(k in next_upper for k in ["DATE", "BIRTH", "DOB", "SEX", "PLACE", "NATIONALITY", "PASSPORT", "ISSUE", "EXPIRY"]):
                    break
                if re.search(r"\d", next_line): # contains digits
                    break
                # Validate name part (letters, spaces, dots, hyphens)
                cleaned_part = re.sub(r"[^A-Za-z\s.-]", "", next_line).strip()
                if len(cleaned_part) > 1:
                    collected.append(cleaned_part)
            if collected:
                extracted_given = " ".join(collected)

        # Extract Surname if marker found, or infer from Given Names marker
        extracted_surname = ""
        if surname_idx != -1:
            collected = []
            for j in range(surname_idx + 1, min(surname_idx + 4, len(lines))):
                next_line = lines[j].strip()
                next_upper = next_line.upper()
                if given_idx != -1 and j >= given_idx:
                    break
                if any(k in next_upper for k in ["GIVEN", "NOMES", "DATE", "BIRTH", "SEX", "PLACE", "NATIONALITY", "PASSPORT"]):
                    break
                if re.search(r"\d", next_line):
                    break
                cleaned_part = re.sub(r"[^A-Za-z\s.-]", "", next_line).strip()
                if len(cleaned_part) > 1:
                    collected.append(cleaned_part)
            if collected:
                extracted_surname = " ".join(collected)
        
        # If Surname marker is missing but Given Names marker is present, infer Surname from line above
        if not extracted_surname and given_idx != -1:
            for j in range(given_idx - 1, max(-1, given_idx - 3), -1):
                prev_line = lines[j].strip()
                prev_upper = prev_line.upper()
                if any(k in prev_upper for k in ["PASSPORT", "REPUBLIC", "INDIA", "TYPE", "CODE", "NATIONALITY", "GIVEN", "NOMES"]):
                    continue
                if re.search(r"\d", prev_line):
                    continue
                cleaned_part = re.sub(r"[^A-Za-z\s.-]", "", prev_line).strip()
                if len(cleaned_part) > 1:
                    extracted_surname = cleaned_part
                    break

        if extracted_surname and not data.get("surname"):
            data["surname"] = extracted_surname
        if extracted_given and not data.get("given_names"):
            data["given_names"] = extracted_given

        return data
