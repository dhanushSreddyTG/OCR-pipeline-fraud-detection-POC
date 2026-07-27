import re
from datetime import datetime
from base import BaseRule
from registry_api_client import RegistryDatabaseClient

class McaRules(BaseRule):
    def __init__(self):
        super().__init__("Certificate of Incorporation")
        self.verification_method = "API Database Verification"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        cin = data.get("cin")
        if cin:
            cin = cin.upper().replace(" ", "").strip()
            # 1. Format check: 21 characters
            # e.g. U72900KA2021PTC145678
            if not re.match(r"^[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", cin):
                self.add_flag("INVALID_CIN_FORMAT", f"CIN '{cin}' does not conform to the 21-character corporate registration format.", "High", 45)
            else:
                # 2. Extract embedded attributes
                state_code = cin[6:8]
                inc_year_str = cin[8:12]
                comp_type = cin[12:15]

                # Check year match
                inc_date_str = data.get("incorporation_date") or data.get("issue_date")
                inc_dt = self.parse_date(inc_date_str)
                if inc_dt:
                    if str(inc_dt.year) != inc_year_str:
                        self.add_flag("CIN_YEAR_MISMATCH", f"Incorporation year in CIN ({inc_year_str}) does not match the certificate text date '{inc_date_str}' (year {inc_dt.year}).", "High", 50)
                else:
                    # Try keyword search in case parsing failed but the string contains a 4 digit year
                    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", str(inc_date_str))
                    if year_match and year_match.group(1) != inc_year_str:
                        self.add_flag("CIN_YEAR_MISMATCH", f"Incorporation year in CIN ({inc_year_str}) does not match certificate text year '{year_match.group(1)}'.", "High", 50)

                # --- MCA Registry API Authenticity Verification ---
                api_res = RegistryDatabaseClient.verify_mca(cin)
                source = api_res.get("source", "MCA Portal API")
                if not api_res.get("found"):
                    self.add_flag("REGISTRY_RECORD_NOT_FOUND", f"CIN '{cin}' was not found in the {source} database. Unverified registry record.", "High", 100)
                else:
                    record = api_res["record"]
                    
                    status = record.get("status", "ACTIVE")
                    if status != "ACTIVE":
                        self.add_flag("REGISTRY_RECORD_INACTIVE", f"{source} reports company status as '{status}'.", "High", 45)
                    
                    # Verify company name
                    comp_name = data.get("company_name") or data.get("name")
                    if comp_name:
                        ext_words = set(re.sub(r"[^A-Z\s]", "", comp_name.upper()).split())
                        act_words = set(re.sub(r"[^A-Z\s]", "", record["company_name"].upper()).split())
                        overlap = {w for w in ext_words.intersection(act_words) if len(w) > 1}
                        if not overlap:
                            self.add_flag("REGISTRY_NAME_MISMATCH", f"Extracted company name '{comp_name}' does not match {source} record '{record['company_name']}'.", "High", 45)
                    
                    # Verify Incorporation Date
                    if inc_dt:
                        act_inc_dt = self.parse_date(record["incorporation_date"])
                        if act_inc_dt and inc_dt.date() != act_inc_dt.date():
                            self.add_flag("REGISTRY_DOB_MISMATCH", f"Extracted Incorporation Date '{inc_date_str}' does not match {source} record '{record['incorporation_date']}'.", "High", 45)

                # Check state code match
                text_upper = full_text.upper()
                # Simple check if state code is found in full text
                # We can map standard state codes to their full names
                states_map = {"KA": "KARNATAKA", "MH": "MAHARASHTRA", "DL": "DELHI", "TN": "TAMIL NADU", "TG": "TELANGANA", "AP": "ANDHRA PRADESH", "WB": "WEST BENGAL", "GJ": "GUJARAT", "HR": "HARYANA"}
                expected_state = states_map.get(state_code)
                if expected_state and expected_state not in text_upper and state_code not in text_upper:
                    self.add_flag("CIN_STATE_MISMATCH", f"CIN state code '{state_code}' ({expected_state}) was not found in the registrar/address text.", "Medium", 30)

        else:
            self.add_flag("MISSING_CIN", "No Corporate Identification Number (CIN) detected.", "High", 40)

        # 3. PAN check for company
        pan = data.get("pan")
        if pan:
            pan = pan.upper().strip()
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
                self.add_flag("INVALID_MCA_PAN", f"Company PAN '{pan}' format is invalid.", "High", 45)
            else:
                # 4th character must be 'C' for Company
                if pan[3] != "C":
                    self.add_flag("MCA_PAN_STATUS_INVALID", f"Company PAN status character '{pan[3]}' is invalid (expected 'C' for Company).", "High", 40)
                
                # 5th character matches first character of company name
                comp_name = data.get("company_name")
                if comp_name:
                    clean_name = re.sub(r"^(DS\s+|MINISTRY\s+OF\s+|CENTRAL\s+REGISTRATION\s+CENTRE\s+)", "", comp_name.upper()).strip()
                    if clean_name:
                        first_letter = clean_name[0]
                        if pan[4] != first_letter:
                            # Sometimes corporate names have special qualifiers, verify first character of first word
                            words = [w for w in clean_name.split() if w.strip()]
                            if words and pan[4] != words[0][0]:
                                self.add_flag("MCA_PAN_NAME_MISMATCH", f"PAN 5th character '{pan[4]}' does not match company name '{comp_name}' (expected first letter '{first_letter}').", "Medium", 25)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
