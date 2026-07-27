import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class USDrivingLicenseRules(BaseRule):
    def __init__(self):
        super().__init__("US Driver License")
        self.verification_method = "API Database Verification"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        doc_type = data.get("document_type", "US Driver License")
        self.evaluate_document_colors(file_path, doc_type)

        dl_number = data.get("dl_number", "")
        clean_dl = re.sub(r"[^A-Z0-9]", "", dl_number.upper())

        # 1. State-specific DL Format Validation & DMV Verification
        dmv_res = None
        if "California" in doc_type:
            # California DL: usually 1 letter and 7 digits (8 chars) or just 7-8 digits
            if len(clean_dl) < 7 or len(clean_dl) > 9:
                self.add_flag("INVALID_CA_DL_LENGTH", f"California DL length '{len(clean_dl)}' is anomalous (expected 7-9 characters).", "Medium", 20)
            if clean_dl:
                dmv_res = RegistryDatabaseClient.verify_california_dl(clean_dl)
        elif "Florida" in doc_type:
            # Florida DL: 1 letter followed by 12 digits (13 chars)
            if len(clean_dl) != 13:
                self.add_flag("INVALID_FL_DL_LENGTH", f"Florida DL length '{len(clean_dl)}' is anomalous (expected 13 characters).", "High", 35)
            elif not clean_dl[0].isalpha() or not clean_dl[1:].isdigit():
                self.add_flag("INVALID_FL_DL_FORMAT", "Florida DL must begin with a letter followed by 12 digits.", "High", 40)
            if clean_dl:
                dmv_res = RegistryDatabaseClient.verify_florida_dl(dl_number)
        else:
            if not clean_dl:
                self.add_flag("MISSING_DL_NUMBER", "No Driver License number detected.", "High", 40)

        # DMV database match verification
        if dmv_res:
            source = dmv_res.get("source", "DMV API")
            if not dmv_res.get("found"):
                self.add_flag("DMV_RECORD_NOT_FOUND", f"DL number '{dl_number}' was not found in the {source} database. Unverified license record.", "High", 100)
            else:
                record = dmv_res["record"]
                status = record.get("status", "ACTIVE")
                if status != "ACTIVE":
                    self.add_flag("DMV_RECORD_INACTIVE", f"{source} registry reports driving license status as '{status}'.", "High", 45)
                
                # Verify name (overlap matching to allow minor OCR variance)
                extracted_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
                if not extracted_name or len(extracted_name) <= 1:
                    extracted_name = data.get("name", "")
                if extracted_name:
                    ext_words = set(re.sub(r"[^A-Z\s]", "", extracted_name.upper()).split())
                    act_words = set(re.sub(r"[^A-Z\s]", "", record["name"].upper()).split())
                    overlap = {w for w in ext_words.intersection(act_words) if len(w) > 1}
                    if not overlap:
                        self.add_flag("DMV_RECORD_NAME_MISMATCH", f"Extracted name '{extracted_name}' does not match {source} record '{record['name']}'.", "High", 45)
                
                # Verify DOB
                extracted_dob = data.get("dob") or data.get("date_of_birth")
                if extracted_dob:
                    ext_dt = self.parse_date(extracted_dob)
                    act_dt = self.parse_date(record["dob"])
                    if ext_dt and act_dt and ext_dt.date() != act_dt.date():
                        self.add_flag("DMV_RECORD_DOB_MISMATCH", f"Extracted DOB '{extracted_dob}' does not match {source} DOB '{record['dob']}'.", "High", 45)

        # 2. Date Chronology Validation
        dob_dt = self.parse_date(data.get("dob"))
        issue_dt = self.parse_date(data.get("issue_date") or data.get("doi"))
        exp_dt = self.parse_date(data.get("expiry_date") or data.get("valid_till"))

        if dob_dt and issue_dt:
            if issue_dt < dob_dt:
                self.add_flag("DL_CHRONOLOGY_ERROR", "Date of Issue cannot be before Date of Birth.", "High", 50)
            else:
                age_at_issue = (issue_dt - dob_dt).days / 365.25
                if age_at_issue < 16.0:
                    self.add_flag("DL_UNDERAGE_ISSUANCE", f"Driver License issued at age {age_at_issue:.2f} (US state laws require minimum age of 15-16).", "High", 45)

        if issue_dt and exp_dt:
            if exp_dt < issue_dt:
                self.add_flag("DL_EXPIRED_BEFORE_ISSUE", "License expiry date is before the issue date.", "High", 50)
            else:
                validity_years = (exp_dt - issue_dt).days / 365.25
                if validity_years > 10.0:
                    self.add_flag("DL_EXCESSIVE_VALIDITY", f"License validity period of {validity_years:.1f} years exceeds the standard US maximum (8 years).", "Medium", 20)

        if dob_dt and exp_dt:
            if exp_dt < dob_dt:
                self.add_flag("DL_EXPIRED_BEFORE_DOB", "License expiry date is before the Date of Birth.", "High", 50)

        # 3. Font Alignment checks
        if font_info:
            char_misalignment = font_info.get("character_misalignment", 0)
            if char_misalignment > 5:
                self.add_flag("DL_TEXT_MISALIGNMENT", "Detected horizontal alignment deviations in key fields.", "Medium", 20)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
