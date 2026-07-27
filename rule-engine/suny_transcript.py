import re
from datetime import datetime
from base import BaseRule

class SUNYTranscriptRules(BaseRule):
    def __init__(self):
        super().__init__("SUNY Transcript")
        self.verification_method = "Format Matching"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0

        doc_type = data.get("document_type", "SUNY Academic Transcript")
        self.evaluate_document_colors(file_path, doc_type)

        # 1. GPA Range Validation
        gpa = data.get("ending_gpa")
        if gpa is not None:
            try:
                gpa_val = float(gpa)
                if gpa_val < 0.0 or gpa_val > 4.0:
                    self.add_flag("TRANSCRIPT_INVALID_GPA", f"Cumulative GPA '{gpa_val}' is out of bounds (expected 0.0 to 4.0).", "High", 50)
            except ValueError:
                self.add_flag("TRANSCRIPT_UNPARSABLE_GPA", f"GPA '{gpa}' is in an invalid format.", "Medium", 15)
        else:
            self.add_flag("MISSING_GPA", "No cumulative GPA detected on the transcript.", "Medium", 20)

        # 2. Student ID Validation
        student_id = data.get("student_id")
        if not student_id:
            self.add_flag("MISSING_STUDENT_ID", "Student ID is missing from the academic record.", "Medium", 15)

        # 3. Document Authenticity/Official Seal Checks
        text_upper = full_text.upper()
        if "OFFICIAL" not in text_upper and "TRANSCRIPT" not in text_upper:
            self.add_flag("UNOFFICIAL_DOCUMENT", "Academic transcript lacks standard 'OFFICIAL' stamp or headers.", "Medium", 20)

        # 4. Award Date Chronology Validation
        date_awarded = data.get("date_awarded")
        if date_awarded:
            # Parse award date
            dt = self.parse_date(date_awarded)
            if dt and dt > datetime.now():
                self.add_flag("DEGREE_FUTURE_AWARD", f"Degree award date '{date_awarded}' cannot be in the future.", "High", 45)

        # 5. Course list validation
        courses = data.get("courses", [])
        if not courses:
            self.add_flag("MISSING_COURSE_DETAILS", "No academic course list was detected on the transcript.", "Medium", 25)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
