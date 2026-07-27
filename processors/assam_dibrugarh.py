import re
from typing import Dict, Any, List
import logging
from .base import BaseDocumentProcessor

logger = logging.getLogger(__name__)

class AssamDibrugarhProcessor(BaseDocumentProcessor):
    """
    Processor for Assam Dibrugarh University Semester Grade Report.
    """

    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        result = {
            "document_type": "Semester Grade Report",
            "state": "Assam",
            "university_name": "Dibrugarh University",
            "student_name": "",
            "enrollment_number": "",
            "registration_number": "",
            "serial_number": "",
            "roll_number": "",
            "session": "",
            "exam_held_in": "",
            "semester": "",
            "programme": "",
            "college_institute": "",
            "abc_id": "",
            "father_name": "",
            "mother_name": "",
            "subjects": [],
            "summary": {
                "total_credit": "",
                "total_credit_point": "",
                "sgpa": "",
                "cgpa": "",
                "result_status": ""
            },
            "date_of_declaration": "",
            "generated_on": "",
            "overall_confidence": 0.4
        }

        norm_text = " \n ".join([line.strip() for line in full_text_lines if line.strip()])
        if not norm_text:
            norm_text = text

        # Helper to extract value using regex
        def extract(pattern, default=""):
            match = re.search(pattern, norm_text, re.IGNORECASE)
            return match.group(1).strip() if match else default

        # Basic Metadata
        result["student_name"] = extract(r"NAME\s*:\s*(.+?)(?:\n|SERIAL|ENROLMENT|REGISTRATION)")
        result["enrollment_number"] = extract(r"ENROLMENT NUMBER\s*:\s*([A-Z0-9]+)")
        result["registration_number"] = extract(r"REGISTRATION NUMBER\s*:\s*([A-Z0-9]+)")
        result["serial_number"] = extract(r"SERIAL NO\s*:\s*([A-Z0-9]+)")
        result["roll_number"] = extract(r"ROLL NUMBER\s*:\s*([A-Z0-9]+)")
        result["session"] = extract(r"SESSION\s*:\s*([\d-]+)")
        result["exam_held_in"] = extract(r"EXAM HELD IN\s*:\s*(.+?)(?:\n|SEMESTER|PROGRAMME)")
        result["semester"] = extract(r"SEMESTER\s*:\s*([IVX]+|[1-8]|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT)")
        result["programme"] = extract(r"PROGRAMME\s*:\s*(.+?)(?:\n|COLLEGE)")
        result["college_institute"] = extract(r"COLLEGE/INSTITUTE\s*:\s*(.+?)(?:\n|ABC-ID)")
        result["abc_id"] = extract(r"ABC-ID\s*:\s*([A-Z0-9-]+)")
        result["father_name"] = extract(r"FATHER'S NAME\s*:\s*(.+?)(?:\n|PROGRAMME|MOTHER'S)")
        result["mother_name"] = extract(r"MOTHER'S NAME\s*:\s*(.+?)(?:\n|PROGRAMME|EXAM)")

        # Date of Declaration and Generated On
        result["date_of_declaration"] = extract(r"Date of Declaration of Result\s*:\s*([\d/]+)")
        result["generated_on"] = extract(r"Generated on\s*:?\s*([\d/]+)")

        # Extract Subjects Table
        subjects = []
        parsing_table = False
        for line in full_text_lines:
            line = line.strip()
            
            # Start of table detection
            if "COURSE CODE" in line.upper() and "COURSE TITLE" in line.upper():
                parsing_table = True
                continue
            
            # End of table detection
            if parsing_table and ("TOTAL CREDIT" in line.upper() or "SGPA" in line.upper() or "Note:" in line):
                parsing_table = False
                continue
                
            if parsing_table:
                # Expected format: Sl No, Course Code, Course Title, Credit, Letter Grade, Grade Point, Credit Point
                # e.g., "1 VAC2 HEALTH AND WELLNESS 2.00 A 8.00 16.00"
                match = re.match(r"^(\d+)\s+([A-Z0-9]+)\s+(.+?)\s+(\d+\.\d{2})\s+([A-Z\+]+|F)\s+(\d+\.\d{2})\s+(\d+\.\d{2})$", line, re.IGNORECASE)
                if match:
                    subjects.append({
                        "sl_no": match.group(1),
                        "course_code": match.group(2),
                        "course_title": match.group(3).strip(),
                        "credit": match.group(4),
                        "letter_grade": match.group(5),
                        "grade_point": match.group(6),
                        "credit_point": match.group(7)
                    })
                else:
                    # Fallback for OCR noise where spacing might be slightly off
                    tokens = line.split()
                    if len(tokens) >= 7 and tokens[0].isdigit() and re.match(r"^\d+\.\d{2}$", tokens[-1]):
                        # Try to construct from tokens
                        try:
                            sl_no = tokens[0]
                            code = tokens[1]
                            credit_pt = tokens[-1]
                            grade_pt = tokens[-2]
                            lg = tokens[-3]
                            credit = tokens[-4]
                            title = " ".join(tokens[2:-4])
                            subjects.append({
                                "sl_no": sl_no,
                                "course_code": code,
                                "course_title": title,
                                "credit": credit,
                                "letter_grade": lg,
                                "grade_point": grade_pt,
                                "credit_point": credit_pt
                            })
                        except Exception as e:
                            logger.debug(f"Assam Processor failed to parse row tokens: {line}")
        
        result["subjects"] = subjects

        # Extract Summary Line (Total Credit, Total Credit Point, SGPA, CGPA, Result)
        # Summary block usually looks like:
        # TOTAL CREDIT TOTAL CREDIT POINT SGPA CGPA RESULT
        # 22.00 89.00 0.00 0.00 FAIL
        summary_found = False
        for i, line in enumerate(full_text_lines):
            if "TOTAL CREDIT" in line.upper() and "SGPA" in line.upper() and "CGPA" in line.upper():
                # The next non-empty line usually contains the values
                for j in range(i+1, min(i+5, len(full_text_lines))):
                    val_line = full_text_lines[j].strip()
                    val_match = re.match(r"(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+([A-Z]+)", val_line, re.IGNORECASE)
                    if val_match:
                        result["summary"]["total_credit"] = val_match.group(1)
                        result["summary"]["total_credit_point"] = val_match.group(2)
                        result["summary"]["sgpa"] = val_match.group(3)
                        result["summary"]["cgpa"] = val_match.group(4)
                        result["summary"]["result_status"] = val_match.group(5).upper()
                        summary_found = True
                        break
            if summary_found:
                break
                
        # Fallback if summary format is slightly different
        if not summary_found:
            tc_match = re.search(r"TOTAL CREDIT\s*\n\s*(\d+\.\d{2})", norm_text, re.IGNORECASE)
            if tc_match: result["summary"]["total_credit"] = tc_match.group(1)
            
            tcp_match = re.search(r"TOTAL CREDIT POINT\s*\n\s*(\d+\.\d{2})", norm_text, re.IGNORECASE)
            if tcp_match: result["summary"]["total_credit_point"] = tcp_match.group(1)
            
            sgpa_match = re.search(r"SGPA\s*\n\s*(\d+\.\d{2})", norm_text, re.IGNORECASE)
            if sgpa_match: result["summary"]["sgpa"] = sgpa_match.group(1)
            
            cgpa_match = re.search(r"CGPA\s*\n\s*(\d+\.\d{2})", norm_text, re.IGNORECASE)
            if cgpa_match: result["summary"]["cgpa"] = cgpa_match.group(1)
            
            res_match = re.search(r"RESULT\s*\n\s*([A-Z]+)", norm_text, re.IGNORECASE)
            if res_match: result["summary"]["result_status"] = res_match.group(1)

        # Confidence Calculation
        if len(subjects) >= 1:
            valid_subs = sum(1 for s in subjects if s["grade_point"] and s["letter_grade"])
            sub_ratio = valid_subs / len(subjects) if subjects else 0
            result["overall_confidence"] = 0.85 + (0.14 * sub_ratio)
        else:
            result["overall_confidence"] = 0.4

        return result
