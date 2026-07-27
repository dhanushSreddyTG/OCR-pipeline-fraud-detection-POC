import re
from typing import Dict, Any
from .base import BaseDocumentProcessor
import logging

logger = logging.getLogger(__name__)

class ANUProvisionalProcessor(BaseDocumentProcessor):
    """
    Processor for Acharya Nagarjuna University (Andhra Pradesh) Provisional Certificates.
    """

    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        """
        Parses OCR text deterministically for ANU Provisional Certificates.
        """
        data = {
            "document_type": "Provisional Certificate",
            "state": "Andhra Pradesh",
            "university_name": "Acharya Nagarjuna University",
            "certificate_number": "",
            "registration_number": "",
            "student_name": "",
            "father_name": "",
            "degree": "",
            "branch": "",
            "result_class": "",
            "examination_month": "",
            "examination_year": "",
            "cgpa": "",
            "medium_of_instruction": "",
            "college_name": "",
            "certificate_issue_place": "",
            "certificate_issue_date": ""
        }

        # Normalize text to reduce OCR variability while preserving casing for extraction
        norm_text = re.sub(r'[\r\n]+', ' \n ', text)
        norm_text = re.sub(r'\s+', ' ', norm_text)

        # Certificate Number
        cert_match = re.search(r'\b([A-Z]\s*\d{6,8})\b', norm_text)
        if cert_match:
            data["certificate_number"] = cert_match.group(1).replace(" ", "")

        # Registration Number
        reg_match = re.search(r'(?:Regd|Reg|Registration)\.?\s*No\b[^A-Z0-9]*([A-Z0-9]{8,15})', norm_text, re.IGNORECASE)
        if reg_match:
            data["registration_number"] = reg_match.group(1).strip()

        # Student Name
        name_match = re.search(r'(?:Sri/Kumari/Smt|Sri / Kumari / Smt|Sri|Kumari|Smt)\.?\s+([A-Z\s]+?)(?=\s+S/o|\s+D/o|has\s|is\s|passed|\n|$)', norm_text, re.IGNORECASE)
        if name_match:
            data["student_name"] = name_match.group(1).strip()

        # Father Name
        father_match = re.search(r'(?:S/o|D/o)\s+(?:-|:)?\s*([A-Z\s]+?)(?=\s+has\s+passed|\s+passed|\n|$)', norm_text, re.IGNORECASE)
        if father_match:
            data["father_name"] = father_match.group(1).strip()

        # Degree
        deg_match = re.search(r'Degree of\s+([A-Za-z\s]+?)(?=\s+in\s|\s+Branch|\s+and\s+has|\n|$)', norm_text, re.IGNORECASE)
        if deg_match:
            data["degree"] = deg_match.group(1).strip().title()

        # Branch
        # Often structured as: "...Degree of Bachelor of Technology in ELECTRICAL & ELECTRONICS ENGINEERING" or standalone
        branch_match = re.search(r'(?:Degree of.*?in|Branch\s*:?)\s+([A-Z&\s]+?)(?=\s+and\s+has|\s+passed|\n|$)', norm_text)
        if branch_match:
            # Title case it but keep AND/& correctly cased
            branch_val = branch_match.group(1).strip().title()
            data["branch"] = branch_val

        # Examination Date (Month & Year)
        exam_match = re.search(r'held\s+in\s+([A-Za-z]+)\s+(\d{4})', norm_text, re.IGNORECASE)
        if exam_match:
            data["examination_month"] = exam_match.group(1).strip().title()
            data["examination_year"] = exam_match.group(2).strip()

        # Result Class
        class_match = re.search(r'in\s+([A-Z\s]+?)\s+CLASS', norm_text, re.IGNORECASE)
        if class_match:
            data["result_class"] = class_match.group(1).strip().upper()

        # CGPA
        cgpa_match = re.search(r'CGPA\s*[:\.]?\s*(\d{1,2}\.\d{1,2})', norm_text, re.IGNORECASE)
        if cgpa_match:
            data["cgpa"] = cgpa_match.group(1).strip()

        # Medium of Instruction
        medium_match = re.search(r'Medium of Instruction(?: and Examination)? is\s+([A-Za-z]+)', norm_text, re.IGNORECASE)
        if medium_match:
            data["medium_of_instruction"] = medium_match.group(1).strip().title()

        # College Name
        college_match = re.search(r'Course is pursued at\s+([A-Za-z0-9\s,\(\)]+?)(?=\s+Medium|\s+Nagarjuna|\s+Date|\n|$)', norm_text, re.IGNORECASE)
        if college_match:
            # Clean up potential trailing artifacts
            raw_college = college_match.group(1).strip()
            # Stop if we hit a known footer line accidentally
            for stop_word in ["Medium", "Nagarjuna", "Date", "Controller", "Vice"]:
                if stop_word.lower() in raw_college.lower():
                    raw_college = re.split(rf'(?i)\b{stop_word}\b', raw_college)[0].strip()
            data["college_name"] = raw_college

        # Issue Place
        place_match = re.search(r'(Nagarjuna\s*Nagar)', norm_text, re.IGNORECASE)
        if place_match:
            data["certificate_issue_place"] = "Nagarjuna Nagar"
            
        # Issue Date
        date_match = re.search(r'Date\s*[:\.]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', norm_text, re.IGNORECASE)
        if date_match:
            data["certificate_issue_date"] = date_match.group(1).strip()

        return data
