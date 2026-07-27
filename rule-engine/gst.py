import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class GstRules(BaseRule):
    def __init__(self):
        super().__init__("GST Registration")
        self.verification_method = "API Database Verification"

    # Indian GST State Code mapping
    STATE_CODES = {
        "01": "JAMMU AND KASHMIR", "02": "HIMACHAL PRADESH", "03": "PUNJAB", "04": "CHANDIGARH", "05": "UTTARAKHAND",
        "06": "HARYANA", "07": "DELHI", "08": "RAJASTHAN", "09": "UTTAR PRADESH", "10": "BIHAR", "11": "SIKKIM",
        "12": "ARUNACHAL PRADESH", "13": "NAGALAND", "14": "MANIPUR", "15": "MIZORAM", "16": "TRIPURA",
        "17": "MEGHALAYA", "18": "ASSAM", "19": "WEST BENGAL", "20": "JHARKHAND", "21": "ODISHA", "22": "CHHATTISGARH",
        "23": "MADHYA PRADESH", "24": "GUJARAT", "26": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "27": "MAHARASHTRA",
        "29": "KARNATAKA", "30": "GOA", "31": "LAKSHADWEEP", "32": "KERALA", "33": "TAMIL NADU", "34": "PUDUCHERRY",
        "35": "ANDAMAN AND NICOBAR ISLANDS", "36": "TELANGANA", "37": "ANDHRA PRADESH", "38": "LADAKH"
    }

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        gstin = data.get("gstin")
        if gstin:
            gstin = gstin.upper().strip()
            # 1. GSTIN format check
            if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gstin):
                self.add_flag("INVALID_GSTIN_FORMAT", f"GSTIN '{gstin}' is invalid or does not match the 15-character statutory format.", "High", 45)
            else:
                # 2. Extract and check embedded PAN
                embedded_pan = gstin[2:12]
                if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", embedded_pan):
                    self.add_flag("GSTIN_PAN_INVALID", f"Embedded PAN '{embedded_pan}' inside GSTIN has an invalid format.", "High", 45)
                
                # Check document PAN if present
                doc_pan = data.get("pan")
                if doc_pan:
                    doc_pan_clean = doc_pan.upper().strip()
                    if doc_pan_clean != embedded_pan:
                        self.add_flag("GSTIN_PAN_MISMATCH", f"Embedded PAN '{embedded_pan}' does not match document PAN '{doc_pan_clean}'.", "High", 50)

                # --- GST Registry API Authenticity Verification ---
                api_res = RegistryDatabaseClient.verify_gst(gstin)
                source = api_res.get("source", "GSTN Portal API")
                if not api_res.get("found"):
                    self.add_flag("REGISTRY_RECORD_NOT_FOUND", f"GSTIN '{gstin}' was not found in the {source} database. Unverified registry record.", "High", 100)
                else:
                    record = api_res["record"]
                    
                    status = record.get("status", "ACTIVE")
                    if status != "ACTIVE":
                        self.add_flag("REGISTRY_RECORD_INACTIVE", f"{source} reports status as '{status}'.", "High", 45)
                    
                    # Verify names (Trade name or Legal name)
                    extracted_name = data.get("legal_name") or data.get("trade_name") or data.get("name")
                    if extracted_name:
                        ext_words = set(re.sub(r"[^A-Z\s]", "", extracted_name.upper()).split())
                        act_words_legal = set(re.sub(r"[^A-Z\s]", "", record["legal_name"].upper()).split())
                        act_words_trade = set(re.sub(r"[^A-Z\s]", "", record["trade_name"].upper()).split())
                        
                        overlap_legal = {w for w in ext_words.intersection(act_words_legal) if len(w) > 1}
                        overlap_trade = {w for w in ext_words.intersection(act_words_trade) if len(w) > 1}
                        
                        if not overlap_legal and not overlap_trade:
                            self.add_flag("REGISTRY_NAME_MISMATCH", f"Extracted name '{extracted_name}' does not match {source} records (Legal: '{record['legal_name']}', Trade: '{record['trade_name']}').", "High", 45)

                # 3. State code verification
                state_code = gstin[0:2]
                expected_state = self.STATE_CODES.get(state_code)
                if expected_state:
                    # Check if expected state is mentioned in text
                    text_upper = full_text.upper()
                    if expected_state not in text_upper:
                        # Sometimes short state names or abbreviations are used, check common abbreviations
                        abbreviations = {
                            "KARNATAKA": ["KA", "BANGALORE", "BENGALURU"],
                            "MAHARASHTRA": ["MH", "MUMBAI", "PUNE"],
                            "DELHI": ["DL", "NEW DELHI"],
                            "TAMIL NADU": ["TN", "CHENNAI"],
                            "TELANGANA": ["TS", "TG", "HYDERABAD"],
                            "ANDHRA PRADESH": ["AP", "VIJAYAWADA", "VISAKHAPATNAM"]
                        }
                        matched_abbrev = False
                        for abbrev in abbreviations.get(expected_state, []):
                            if abbrev in text_upper:
                                matched_abbrev = True
                                break
                        if not matched_abbrev:
                            self.add_flag("GSTIN_STATE_MISMATCH", f"GSTIN state code '{state_code}' indicates '{expected_state}', which does not match address/jurisdiction state in document.", "Medium", 30)

        else:
            self.add_flag("MISSING_GSTIN", "No GSTIN number detected.", "High", 40)

        # 4. Date check
        liability_str = data.get("date_of_liability")
        reg_date_str = data.get("certificate_issue_date") or data.get("period_of_validity")
        
        # Check registration / liability chronology
        liability_dt = self.parse_date(liability_str)
        reg_dt = self.parse_date(reg_date_str)
        if liability_dt and reg_dt:
            if reg_dt < liability_dt:
                self.add_flag("GST_CHRONOLOGY_ERROR", f"Certificate issue date '{reg_date_str}' is before date of liability '{liability_str}'.", "Medium", 25)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
