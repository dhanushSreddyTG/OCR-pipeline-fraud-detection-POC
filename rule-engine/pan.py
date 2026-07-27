import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class PanRules(BaseRule):
    def __init__(self):
        super().__init__("PAN Card")
        self.verification_method = "API Database Verification"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        pan_no = data.get("pan_number")
        if pan_no:
            # 1. Format check
            pan_no = pan_no.upper().strip()
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_no):
                self.add_flag("INVALID_PAN_FORMAT", f"PAN '{pan_no}' is not in standard XXXXXNNNNX format.", "High", 45)
            else:
                # 2. 4th character check (Status)
                status_char = pan_no[3]
                valid_status = ["P", "C", "H", "F", "A", "T", "B", "L", "J", "G"]
                if status_char not in valid_status:
                    self.add_flag("INVALID_PAN_STATUS", f"PAN status character '{status_char}' is invalid.", "Medium", 25)

                # 3. 5th character check (Surname matching)
                holder_name = data.get("name")
                if holder_name and status_char == "P": # Only for individuals
                    name_parts = [p.strip() for p in holder_name.split() if p.strip()]
                    if name_parts:
                        last_name = name_parts[-1].upper()
                        # Allow for potential OCR errors (e.g. matching first letter of last name)
                        expected_char = last_name[0]
                        if pan_no[4] != expected_char:
                            # Let's check if it matches first name as a fallback or flag mismatch
                            first_name = name_parts[0].upper()
                            if pan_no[4] != first_name[0]:
                                self.add_flag("PAN_NAME_MISMATCH", f"PAN 5th character '{pan_no[4]}' does not match name '{holder_name}' (expected first letter of last name '{expected_char}').", "High", 35)

                # --- NSDL PAN Registry API Authenticity Verification ---
                api_res = RegistryDatabaseClient.verify_pan(pan_no)
                source = api_res.get("source", "NSDL PAN API")
                if not api_res.get("found"):
                    self.add_flag("REGISTRY_RECORD_NOT_FOUND", f"PAN number '{pan_no}' was not found in the {source} database. Unverified registry record.", "High", 100)
                else:
                    record = api_res["record"]
                    
                    status = record.get("status", "ACTIVE")
                    if status != "ACTIVE":
                        self.add_flag("REGISTRY_RECORD_INACTIVE", f"{source} reports status as '{status}'.", "High", 45)
                    
                    # Verify name
                    if holder_name:
                        ext_words = set(re.sub(r"[^A-Z\s]", "", holder_name.upper()).split())
                        act_words = set(re.sub(r"[^A-Z\s]", "", record["name"].upper()).split())
                        overlap = {w for w in ext_words.intersection(act_words) if len(w) > 1}
                        if not overlap:
                            self.add_flag("REGISTRY_NAME_MISMATCH", f"Extracted name '{holder_name}' does not match {source} record '{record['name']}'.", "High", 45)
                    
                    # Verify DOB
                    extracted_dob = data.get("dob")
                    if extracted_dob:
                        ext_dt = self.parse_date(extracted_dob)
                        act_dt = self.parse_date(record["dob"])
                        if ext_dt and act_dt and ext_dt.date() != act_dt.date():
                            self.add_flag("REGISTRY_DOB_MISMATCH", f"Extracted DOB '{extracted_dob}' does not match {source} DOB '{record['dob']}'.", "High", 45)
        else:
            self.add_flag("MISSING_PAN_NUMBER", "No PAN number found on the document.", "High", 40)

        # 4. DOB checks
        dob_str = data.get("dob")
        if dob_str:
            dob_dt = self.parse_date(dob_str)
            if dob_dt:
                now = datetime.now()
                if dob_dt > now:
                    self.add_flag("PAN_FUTURE_DOB", f"PAN Date of Birth '{dob_str}' cannot be in the future.", "High", 40)
                if dob_dt.year < 1900:
                    self.add_flag("PAN_INVALID_DOB", f"PAN Date of Birth year '{dob_dt.year}' is invalid.", "Medium", 20)
            else:
                self.add_flag("PAN_UNPARSABLE_DOB", f"PAN DOB '{dob_str}' is in an unparsable format.", "Low", 10)

        # 5. Font check
        if font_info:
            char_misalignment = font_info.get("character_misalignment", 0)
            if char_misalignment > 5:
                self.add_flag("PAN_TEXT_MISALIGNMENT", "Detected misaligned text characters on PAN card.", "Medium", 25)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
