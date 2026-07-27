import re
import logging
from typing import Dict, Any, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def parse_flux_markdown(markdown_text: str, doc_type: str) -> Dict[str, Any]:
    """
    Parses OCRFlux markdown/HTML output into target JSON schema.
    Specifically optimized for Marksheet/VTU documents.
    """
    result = {
        "document_type": "MARKSHEET" if "MARKSHEET" in doc_type.upper() or "VTU" in doc_type.upper() else doc_type,
        "raw_markdown": markdown_text,
    }

    # Extract metadata fields using regex heuristics
    text_upper = markdown_text.upper()

    # 1. University seat number (USN) or roll number
    usn_match = re.search(r'\b[1-4][A-Z]{2}\d{2}[A-Z]{2}\d{3}\b', text_upper)
    if usn_match:
        result["university_seat_number"] = usn_match.group(0)
    else:
        # Fallback USN/ID number searches
        usn_patterns = [
            r'USN\s*[:\-\s]\s*([A-Z0-9]+)',
            r'ROLL\s*NO\s*[:\-\s]\s*([A-Z0-9]+)',
            r'SEAT\s*NO\s*[:\-\s]\s*([A-Z0-9]+)'
        ]
        for pattern in usn_patterns:
            match = re.search(pattern, text_upper)
            if match:
                result["university_seat_number"] = match.group(1).strip()
                break

    # 2. Semester
    sem_match = re.search(r'(?:SEMESTER|SEM)\s*[:\-\s]\s*([0-9IVX]+)', text_upper)
    if sem_match:
        result["semester"] = sem_match.group(1).strip()
    else:
        # Check ordinal semesters
        for ord_sem in ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH"]:
            if ord_sem in text_upper:
                result["semester"] = ord_sem
                break

    # 3. University Name
    uni_patterns = [
        r'([A-Z\s]+UNIVERSITY[A-Z\s]*)',
        r'(VISVESVARAYA\s+TECHNOLOGICAL\s+UNIVERSITY[A-Z\s]*)',
        r'(VTU[A-Z\s]*)'
    ]
    for pattern in uni_patterns:
        match = re.search(pattern, text_upper)
        if match:
            # Clean and clean trailing spaces/newlines
            uni_name = match.group(1).strip().replace("\n", " ")
            uni_name = re.sub(r'\s+', ' ', uni_name)
            result["university_name"] = uni_name
            break
    
    if "university_name" not in result:
        if "VISVESVARAYA" in text_upper:
            result["university_name"] = "VISVESVARAYA TECHNOLOGICAL UNIVERSITY"

    # 4. College Name
    college_match = re.search(r'COLLEGE\s*[:\-\s]\s*([A-Z\s\n,]+)', text_upper)
    if college_match:
        col_name = college_match.group(1).strip().split("\n")[0]
        result["college_name"] = re.sub(r'\s+', ' ', col_name)
    else:
        # Search for common institute keyword patterns
        inst_match = re.search(r'([A-Z\s]+INSTITUTE\s+OF\s+[A-Z\s]+)', text_upper)
        if inst_match:
            result["college_name"] = re.sub(r'\s+', ' ', inst_match.group(1).strip())

    # 5. Extract tables & subjects
    subjects = []
    try:
        soup = BeautifulSoup(markdown_text, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Identify columns based on header row keywords
            headers = []
            header_row = rows[0]
            for td in header_row.find_all(['td', 'th']):
                headers.append(td.get_text(strip=True).upper())
                
            # If the table has exactly 2 columns, it is likely metadata (USN, Student Name, etc.)
            if len(headers) == 2:
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) == 2:
                        key_clean = re.sub(r'[^A-Z0-9\s]', '', cells[0].upper()).strip()
                        if "STUDENT NAME" in key_clean or "STUDENTNAME" in key_clean or key_clean == "NAME":
                            val_clean = re.sub(r"^[^A-Za-z0-9\s]+", "", cells[1]).strip()
                            result["student_name"] = val_clean.title()
                            result["name"] = val_clean.title()
                        elif "UNIVERSITY SEAT NUMBER" in key_clean or "SEAT NUMBER" in key_clean or key_clean == "USN" or key_clean == "ROLL NO" or key_clean == "ROLL NUMBER":
                            val_clean = re.sub(r"^[^A-Za-z0-9]+", "", cells[1]).strip()
                            result["university_seat_number"] = val_clean.upper()
                continue
                
            # Skip tables that do not look like marksheet/subject lists (e.g. metadata/too few columns)
            if len(headers) < 3:
                continue
            
            col_indices = {
                "code": -1,
                "name": -1,
                "internal": -1,
                "external": -1,
                "total": -1,
                "result": -1,
                "grade": -1,
                "credits": -1
            }
            
            # Simple keyword matching for column mapping
            for idx, h in enumerate(headers):
                if any(x in h for x in ["CODE", "SUBCODE", "SUB_CODE", "SUBJECTCODE"]):
                    col_indices["code"] = idx
                elif any(x in h for x in ["SUBJECT", "NAME", "TITLE", "SUB_NAME", "SUBNAME"]):
                    col_indices["name"] = idx
                elif any(x in h for x in ["INTERNAL", "INT", "IA"]):
                    col_indices["internal"] = idx
                elif any(x in h for x in ["EXTERNAL", "EXT", "SEE"]):
                    col_indices["external"] = idx
                elif any(x in h for x in ["TOTAL", "TOT"]):
                    col_indices["total"] = idx
                elif any(x in h for x in ["RESULT", "RES", "PASS", "FAIL"]):
                    col_indices["result"] = idx
                elif any(x in h for x in ["GRADE", "GR"]):
                    col_indices["grade"] = idx
                elif any(x in h for x in ["CREDIT", "CR"]):
                    col_indices["credits"] = idx

            # Fallback index mapping if standard headers are not detected
            if col_indices["code"] == -1 and col_indices["name"] == -1:
                # Guess typical column positions: Code is Col 0, Name is Col 1
                col_indices["code"] = 0
                col_indices["name"] = 1
            
            # Process content rows
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                if len(cells) < 2:
                    continue
                
                # Check if it looks like a subject row (e.g. valid code or name present)
                code_val = cells[col_indices["code"]] if 0 <= col_indices["code"] < len(cells) else ""
                name_val = cells[col_indices["name"]] if 0 <= col_indices["name"] < len(cells) else ""
                
                # Skip header repetitions or empty separator rows
                if not code_val and not name_val:
                    continue
                if code_val.upper() in ("SUBJECT CODE", "SUB CODE", "CODE"):
                    continue
                
                # Check for alphanumeric subject code pattern or non-trivial name length
                is_valid_subject = False
                if code_val and re.search(r'\d', code_val): # Contains numbers (like 18CS51)
                    is_valid_subject = True
                elif len(name_val) > 4 and not re.search(r'(?:TOTAL|GRAND|RESULT)', name_val.upper()):
                    is_valid_subject = True
                    
                if is_valid_subject:
                    subject_obj = {
                        "subject_code": code_val,
                        "subject_name": name_val,
                        "internal_marks": cells[col_indices["internal"]] if 0 <= col_indices["internal"] < len(cells) else None,
                        "external_marks": cells[col_indices["external"]] if 0 <= col_indices["external"] < len(cells) else None,
                        "total": cells[col_indices["total"]] if 0 <= col_indices["total"] < len(cells) else None,
                        "result": cells[col_indices["result"]] if 0 <= col_indices["result"] < len(cells) else None,
                        "grade": cells[col_indices["grade"]] if 0 <= col_indices["grade"] < len(cells) else None,
                        "credits": cells[col_indices["credits"]] if 0 <= col_indices["credits"] < len(cells) else None
                    }
                    subjects.append(subject_obj)
        
    except Exception as e:
        logger.error(f"Error parsing tables from markdown: {e}")

    if subjects:
        result["subjects"] = subjects
        
    return result
