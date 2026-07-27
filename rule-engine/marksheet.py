import re
from datetime import datetime
from base import BaseRule

class MarksheetRules(BaseRule):
    def __init__(self):
        super().__init__("Marksheet")
        self.verification_method = "Arithmetic Grade Audit"

    def parse_month_year(self, month_str: str, year_str: str) -> datetime:
        """Helper to create a date from exam month and year."""
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        m = months.get(month_str.lower().strip(), 1)
        try:
            y = int(year_str.strip())
            return datetime(y, m, 28) # End of month approx
        except ValueError:
            return None

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0
        
        # 0. Color Profile Validation
        self.evaluate_document_colors(file_path, self.doc_type)

        university = data.get("university_name", "").upper()
        
        # 1. Date Chronology Checks
        exam_month = data.get("examination_month") or data.get("exam_month")
        exam_year = data.get("examination_year") or data.get("exam_year")
        issue_date_str = data.get("certificate_issue_date") or data.get("date_of_issue")

        exam_dt = None
        if exam_month and exam_year:
            exam_dt = self.parse_month_year(exam_month, exam_year)

        issue_dt = self.parse_date(issue_date_str)
        if exam_dt and issue_dt:
            if issue_dt < exam_dt:
                self.add_flag("MARKSHEET_CHRONOLOGY_ERROR", f"Issue date '{issue_date_str}' is before examination date ({exam_month} {exam_year}).", "High", 45)

        # 2. Subject marks summation check (VTU and Dibrugarh)
        subjects = data.get("subjects", [])
        mismatched_subjects = 0
        
        for sub in subjects:
            int_m = sub.get("internal_marks")
            ext_m = sub.get("external_marks")
            tot_m = sub.get("total")
            
            if int_m and ext_m and tot_m:
                # Clean any spaces/alpha characters (e.g. absent/fail markers)
                int_clean = re.sub(r"[^\d]", "", str(int_m))
                ext_clean = re.sub(r"[^\d]", "", str(ext_m))
                tot_clean = re.sub(r"[^\d]", "", str(tot_m))
                
                if int_clean.isdigit() and ext_clean.isdigit() and tot_clean.isdigit():
                    val_int = int(int_clean)
                    val_ext = int(ext_clean)
                    val_tot = int(tot_clean)
                    if val_int + val_ext != val_tot:
                        # Allow 1-2 points margin for minor OCR/rounding errors, flag if mismatch is larger
                        if abs(val_int + val_ext - val_tot) > 2:
                            mismatched_subjects += 1
                            
        if mismatched_subjects > 0:
            self.add_flag("MARKS_SUM_MISMATCH", f"Detected marks summation discrepancies in {mismatched_subjects} subjects (Internal + External != Total).", "High", 40)

        # 3. SGPA / CGPA range checks
        cgpa_str = data.get("cgpa")
        sgpa_str = data.get("summary", {}).get("sgpa") or data.get("sgpa")
        
        for name, val in [("CGPA", cgpa_str), ("SGPA", sgpa_str)]:
            if val:
                val_clean = re.sub(r"[^\d\.]", "", str(val))
                try:
                    score = float(val_clean)
                    if score < 0.0 or score > 10.0:
                        self.add_flag("INVALID_GPA_VALUE", f"Extracted {name} value '{val}' is outside standard 0.0-10.0 scale.", "High", 45)
                except ValueError:
                    pass

        # 4. Font checking
        if font_info:
            font_size_anom = font_info.get("font_size_anomaly", False)
            if font_size_anom:
                self.add_flag("MARKSHEET_FONT_SIZE_ANOMALY", "Detected inconsistent font size changes inside the grades or marks columns.", "Medium", 30)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
