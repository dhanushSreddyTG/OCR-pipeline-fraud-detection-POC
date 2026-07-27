import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class PassportRules(BaseRule):
    def __init__(self):
        super().__init__("Passport")
        self.verification_method = "API Database Verification"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        # 1. Format check
        passport_no = data.get("passport_number")
        if passport_no:
            passport_no = passport_no.upper().strip()
            # Standard Indian/ICAO passport format: 1 letter + 7 digits
            if not re.match(r"^[A-Z][0-9]{7}$", passport_no):
                # Sometime MRZ contains placeholder '<' or spaces
                if not re.match(r"^[A-Z0-9<]{8,9}$", passport_no):
                    self.add_flag("INVALID_PASSPORT_NUMBER", f"Passport number '{passport_no}' does not conform to standard format (1 letter + 7 digits).", "Medium", 20)
            
            # --- Passport Seva Registry API Authenticity Verification ---
            api_res = RegistryDatabaseClient.verify_passport(passport_no)
            source = api_res.get("source", "Passport Seva API")
            if not api_res.get("found"):
                self.add_flag("REGISTRY_RECORD_NOT_FOUND", f"Passport number '{passport_no}' was not found in the {source} database. Unverified registry record.", "High", 100)
            else:
                record = api_res["record"]
                
                status = record.get("status", "ACTIVE")
                if status != "ACTIVE":
                    self.add_flag("REGISTRY_RECORD_INACTIVE", f"{source} reports status as '{status}'.", "High", 45)
                
                # Verify name
                holder_name = data.get("name")
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
            self.add_flag("MISSING_PASSPORT_NUMBER", "No passport number found.", "High", 40)

        # 2. Date parsing
        dob_dt = self.parse_date(data.get("dob"))
        doi_dt = self.parse_date(data.get("doi"))
        doe_dt = self.parse_date(data.get("doe"))

        # Fact Check: Chronology
        if dob_dt and doi_dt:
            if doi_dt < dob_dt:
                self.add_flag("PASSPORT_CHRONOLOGY_ERROR", "Date of Issue cannot be before Date of Birth.", "High", 50)
            
            # Age at issuance
            age_at_issue = (doi_dt - dob_dt).days / 365.25
            
            if doi_dt and doe_dt:
                if doe_dt < doi_dt:
                    self.add_flag("PASSPORT_EXPIRED_BEFORE_ISSUE", "Date of Expiry is before Date of Issue.", "High", 50)
                
                # Check validity period (Adult = 10 years, Minor = 5 years)
                validity_days = (doe_dt - doi_dt).days
                validity_years = validity_days / 365.25
                
                expected_years = 10
                is_minor = age_at_issue < 18
                if is_minor:
                    expected_years = 5

                # Allow ±30 days deviation for parsing edge cases or issuance adjustments
                if abs(validity_years - expected_years) > 0.1:
                    # If it's a minor passport with 5 years but we expected 10 or vice-versa, or if it is completely irregular
                    # Let's check if it fits either 5 or 10 years
                    if abs(validity_years - 10) > 0.1 and abs(validity_years - 5) > 0.1:
                        self.add_flag("PASSPORT_VALIDITY_ANOMALY", f"Passport validity period of {validity_years:.2f} years is anomalous (expected {expected_years} years).", "High", 45)
                    elif is_minor and abs(validity_years - 10) < 0.1:
                        # Minor issued a 10 year passport - sometimes allowed if 15-18, but flag a note
                        pass

        # 3. MRZ (Machine Readable Zone) consistency checks
        # If both MRZ parsed fields and visual fields are present, check their coherence
        surname = data.get("surname")
        given_names = data.get("given_names")
        visual_name = data.get("name")
        gender = data.get("gender")

        # Let's try parsing MRZ block if not explicitly structured in data but lines contain MRZ
        mrz_lines = [l for l in lines if l.replace(" ", "").startswith("P<") or (len(l.replace(" ", "")) > 30 and ("<<" in l or re.match(r"^[A-Z0-9<]{30,}", l.replace(" ", ""))))]
        
        if len(mrz_lines) >= 2:
            m1 = mrz_lines[0].replace(" ", "").upper()
            m2 = mrz_lines[1].replace(" ", "").upper()
            
            # Extract passport number from MRZ Line 2 (first 9 chars usually)
            mrz_pass_no = m2[0:8] if len(m2) > 8 else ""
            if passport_no and mrz_pass_no:
                # Clean filler characters '<'
                clean_mrz_no = mrz_pass_no.replace("<", "")
                clean_vis_no = passport_no.replace("<", "")
                if clean_mrz_no not in clean_vis_no and clean_vis_no not in clean_mrz_no:
                    self.add_flag("PASSPORT_MRZ_NUMBER_MISMATCH", f"Passport number in visual field ({passport_no}) does not match MRZ ({clean_mrz_no}).", "High", 50)
            
            # Extract DOB from MRZ Line 2 (chars 13-18)
            if len(m2) >= 19:
                mrz_dob_raw = m2[13:19]
                if mrz_dob_raw.isdigit() and dob_dt:
                    mrz_yy = int(mrz_dob_raw[0:2])
                    mrz_mm = int(mrz_dob_raw[2:4])
                    mrz_dd = int(mrz_dob_raw[4:6])
                    
                    dob_yy = dob_dt.year % 100
                    if dob_yy != mrz_yy or dob_dt.month != mrz_mm or dob_dt.day != mrz_dd:
                        self.add_flag("PASSPORT_MRZ_DOB_MISMATCH", f"DOB in visual field ({data.get('dob')}) does not match MRZ DOB ({mrz_dd:02d}-{mrz_mm:02d}-{mrz_yy:02d}).", "High", 50)

            # Extract Gender from MRZ Line 2 (char 20)
            if len(m2) >= 21:
                mrz_sex = m2[20]
                if mrz_sex in ["M", "F"] and gender and gender != "Unknown":
                    # Map gender format
                    vis_sex = gender[0].upper()
                    if vis_sex != mrz_sex:
                        self.add_flag("PASSPORT_MRZ_GENDER_MISMATCH", f"Gender in visual field ({gender}) does not match MRZ ({mrz_sex}).", "High", 40)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
