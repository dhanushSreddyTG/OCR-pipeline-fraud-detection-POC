import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class AadhaarRules(BaseRule):
    def __init__(self):
        super().__init__("Aadhaar Card")
        self.verification_method = "API Database Verification"

    def is_verhoeff_valid(self, num_str: str) -> bool:
        if not num_str.isdigit() or len(num_str) != 12:
            return False
        d = [
            [0,1,2,3,4,5,6,7,8,9], [1,2,3,4,0,6,7,8,9,5], [2,3,4,0,1,7,8,9,5,6], [3,4,0,1,2,8,9,5,6,7], [4,0,1,2,3,9,5,6,7,8],
            [5,9,8,7,6,0,4,3,2,1], [6,5,9,8,7,1,0,4,3,2], [7,6,5,9,8,2,1,0,4,3], [8,7,6,5,9,3,2,1,0,4], [9,8,7,6,5,4,3,2,1,0]
        ]
        p = [
            [0,1,2,3,4,5,6,7,8,9], [1,5,7,6,2,8,3,0,9,4], [5,8,0,3,7,9,6,1,4,2], [8,9,1,6,0,4,3,5,2,7],
            [9,4,5,3,1,2,6,8,7,0], [4,2,8,6,5,7,3,9,0,1], [2,7,9,3,8,0,6,4,1,5], [7,0,4,6,9,1,3,2,5,8],
            [0,1,2,3,4,5,6,7,8,9]
        ]
        c = 0
        num_array = [int(n) for n in reversed(num_str)]
        try:
            for i, num in enumerate(num_array):
                c = d[c][p[i % 8][num]]
            return c == 0
        except IndexError:
            return False

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        # 1. Aadhaar number checks
        aadhaar_no = data.get("aadhaar_number")
        if aadhaar_no:
            clean_no = re.sub(r"\s+", "", aadhaar_no)
            if len(clean_no) != 12 or not clean_no.isdigit():
                self.add_flag("INVALID_AADHAAR_LENGTH", "Aadhaar number must be exactly 12 digits.", "High", 45)
            elif not self.is_verhoeff_valid(clean_no):
                self.add_flag("AADHAAR_CHECKSUM_FAILED", "Aadhaar number failed Verhoeff checksum validation.", "High", 45)
            else:
                # --- Aadhaar Registry API Authenticity Verification ---
                api_res = RegistryDatabaseClient.verify_aadhaar(clean_no)
                source = api_res.get("source", "UIDAI Aadhaar API")
                if not api_res.get("found"):
                    self.add_flag("REGISTRY_RECORD_NOT_FOUND", f"Aadhaar number '{aadhaar_no}' was not found in the {source} database. Unverified registry record.", "High", 100)
                else:
                    record = api_res["record"]
                    
                    status = record.get("status", "ACTIVE")
                    if status != "ACTIVE":
                        self.add_flag("REGISTRY_RECORD_INACTIVE", f"{source} reports status as '{status}'.", "High", 45)
                    
                    # Verify name
                    extracted_name = data.get("name")
                    if extracted_name:
                        ext_words = set(re.sub(r"[^A-Z\s]", "", extracted_name.upper()).split())
                        act_words = set(re.sub(r"[^A-Z\s]", "", record["name"].upper()).split())
                        overlap = {w for w in ext_words.intersection(act_words) if len(w) > 1}
                        if not overlap:
                            self.add_flag("REGISTRY_NAME_MISMATCH", f"Extracted name '{extracted_name}' does not match {source} record '{record['name']}'.", "High", 45)
                    
                    # Verify DOB
                    extracted_dob = data.get("dob")
                    if extracted_dob:
                        ext_dt = self.parse_date(extracted_dob)
                        act_dt = self.parse_date(record["dob"])
                        if ext_dt and act_dt and ext_dt.date() != act_dt.date():
                            self.add_flag("REGISTRY_DOB_MISMATCH", f"Extracted DOB '{extracted_dob}' does not match {source} DOB '{record['dob']}'.", "High", 45)
                    
                    # Verify Gender
                    extracted_gender = data.get("gender")
                    if extracted_gender and extracted_gender != "Unknown":
                        if extracted_gender.upper()[0] != record["gender"].upper()[0]:
                            self.add_flag("REGISTRY_GENDER_MISMATCH", f"Extracted gender '{extracted_gender}' does not match {source} record '{record['gender']}'.", "Medium", 20)
        else:
            self.add_flag("MISSING_AADHAAR_NUMBER", "No 12-digit Aadhaar number found on the card.", "Medium", 20)

        # 2. DOB checks
        dob_str = data.get("dob")
        if dob_str:
            dob_dt = self.parse_date(dob_str)
            if dob_dt:
                now = datetime.now()
                if dob_dt > now:
                    self.add_flag("AADHAAR_FUTURE_DOB", f"Aadhaar Date of Birth '{dob_str}' cannot be in the future.", "High", 40)
                if dob_dt.year < 1900:
                    self.add_flag("AADHAAR_INVALID_DOB", f"Aadhaar Date of Birth year '{dob_dt.year}' is unrealistically old.", "Medium", 20)
            else:
                self.add_flag("AADHAAR_UNPARSABLE_DOB", f"Aadhaar DOB '{dob_str}' is in an unparsable format.", "Low", 10)

        # 3. Gender check
        gender = data.get("gender")
        if not gender or gender == "Unknown":
            self.add_flag("AADHAAR_MISSING_GENDER", "Gender is missing or could not be parsed.", "Low", 5)

        # 4. Font checking
        if font_info:
            char_misalignment = font_info.get("character_misalignment", 0)
            if char_misalignment > 5:
                self.add_flag("AADHAAR_TEXT_MISALIGNMENT", f"Detected {char_misalignment} misaligned characters on the card.", "High", 35)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
