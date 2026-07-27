import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class DrivingLicenseRules(BaseRule):
    def __init__(self):
        super().__init__("Driving License")
        self.verification_method = "API Database Verification"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        # 1. DL number validation
        dl_no = data.get("dl_number")
        if dl_no:
            dl_no = re.sub(r"[^A-Z0-9]", "", dl_no.upper())
            # Indian Driving License: e.g. KA5120150002345 (15 chars)
            # Standard: State Code (2 letters) + RTO Code (2 digits) + Year (4 digits) + 7 digits serial
            if len(dl_no) < 10 or len(dl_no) > 16:
                self.add_flag("INVALID_DL_LENGTH", f"DL number length '{len(dl_no)}' is anomalous (expected 15 characters for standard Indian DL).", "Medium", 20)
            elif not re.match(r"^[A-Z]{2}[0-9]{2}", dl_no):
                self.add_flag("INVALID_DL_FORMAT", "DL number should start with a 2-letter state code followed by a 2-digit RTO code.", "Medium", 25)
            
            # --- DMV Database Authenticity Verification ---
            dmv_res = RegistryDatabaseClient.verify_indian_dl(dl_no)
            if not dmv_res.get("found"):
                self.add_flag("DMV_RECORD_NOT_FOUND", f"DL number '{dl_no}' was not found in the Parivahan database. Unverified license record.", "High", 100)
            else:
                record = dmv_res["record"]
                
                # Verify status
                status = record.get("status", "ACTIVE")
                if status != "ACTIVE":
                    self.add_flag("DMV_RECORD_INACTIVE", f"Parivahan registry reports driving license status as '{status}'.", "High", 45)
                
                # Verify name (overlap matching to allow minor OCR variance)
                extracted_name = data.get("name")
                if extracted_name:
                    ext_words = set(re.sub(r"[^A-Z\s]", "", extracted_name.upper()).split())
                    act_words = set(re.sub(r"[^A-Z\s]", "", record["name"].upper()).split())
                    overlap = {w for w in ext_words.intersection(act_words) if len(w) > 1}
                    if not overlap:
                        self.add_flag("DMV_RECORD_NAME_MISMATCH", f"Extracted name '{extracted_name}' does not match Parivahan registry record '{record['name']}'.", "High", 45)
                
                # Verify DOB
                extracted_dob = data.get("dob") or data.get("date_of_birth")
                if extracted_dob:
                    ext_dt = self.parse_date(extracted_dob)
                    act_dt = self.parse_date(record["dob"])
                    if ext_dt and act_dt and ext_dt.date() != act_dt.date():
                        self.add_flag("DMV_RECORD_DOB_MISMATCH", f"Extracted DOB '{extracted_dob}' does not match Parivahan registry DOB '{record['dob']}'.", "High", 45)
        else:
            self.add_flag("MISSING_DL_NUMBER", "No Driving License number detected.", "High", 40)

        # 2. Date parsing
        dob_dt = self.parse_date(data.get("dob") or data.get("date_of_birth"))
        doi_dt = self.parse_date(data.get("doi") or data.get("date_of_issue"))
        doe_dt = self.parse_date(data.get("valid_till") or data.get("valid_to"))

        # Fact Check: Age Check
        if dob_dt and doi_dt:
            if doi_dt < dob_dt:
                self.add_flag("DL_CHRONOLOGY_ERROR", "Date of Issue cannot be before Date of Birth.", "High", 50)
            else:
                age_at_issue = (doi_dt - dob_dt).days / 365.25
                if age_at_issue < 18.0:
                    self.add_flag("DL_UNDERAGE_ISSUANCE", f"Driving License issued at age {age_at_issue:.2f} (Indian law requires a minimum age of 18).", "High", 50)

        # Fact Check: Expiry Chronology
        if doi_dt and doe_dt:
            if doe_dt < doi_dt:
                self.add_flag("DL_EXPIRED_BEFORE_ISSUE", "License validity expiry date is before the issue date.", "High", 50)

        # 3. Font checks
        if font_info:
            char_misalignment = font_info.get("character_misalignment", 0)
            if char_misalignment > 5:
                self.add_flag("DL_TEXT_MISALIGNMENT", "Detected horizontal alignment deviations in key fields.", "Medium", 20)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
