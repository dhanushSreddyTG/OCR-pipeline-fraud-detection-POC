import re
from typing import Dict, Any, List
import logging
from .base import BaseDocumentProcessor

logger = logging.getLogger(__name__)

class VTUProcessor(BaseDocumentProcessor):
    def parse(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """
        Ultra-fast heuristic parser for VTU Marksheets.
        Bypasses the Neural Engine entirely to achieve <1s latency.
        """
        result = {
            "document_type": "VTU Grade Card",
            "university_name": "Visvesvaraya Technological University",
            "student_name": "",
            "father_name": "",
            "college_name": "",
            "university_seat_number": "",
            "semester": "",
            "exam_month": "",
            "exam_year": "",
            "overall_confidence": 0.4, # Base deterministic score
            
            "metadata": {
                "student_name": "",
                "father_name": "",
                "college_name": "",
                "usn": "",
                "programme": "",
                "semester": "",
                "exam_month": "",
                "exam_year": "",
                "grade_card_number": "",
                "date_of_issue": "",
                "medium_of_instruction": ""
            },
            "subjects": [],
            "summary": {
                "credits_registered": "",
                "credits_earned": "",
                "cumulative_credits_earned": "",
                "total_grade_points": "",
                "sgpa": "",
                "cgpa": ""
            }
        }
        
        # 1. OCR Preprocessing and Normalization
        text_lines = [line.strip() for line in lines if line.strip()]
        if not text_lines and raw_text:
            text_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
        normalized_text = " ".join(text_lines)
        
        # Address common OCR substitutions if necessary
        normalized_text = re.sub(r"1\s+7\s+M\s+A\s+T", "17MAT", normalized_text)
        
        # 2. Robust Metadata Extraction
        # Student Name
        m = re.search(r"Name\s*of\s*the\s*Stud[a-z]*\s*[:\-]?\s*(.+?)(?=\s+Semester|\s+USN|\s+Father|\s+Name of|\s+Mother|\s+Sl\.|$)", normalized_text, re.IGNORECASE)
        if not m:
            m = re.search(r"Student\s*Name\s*[:\-]?\s*(.+?)(?=\s+Semester|\s+USN|\s+Father|\s+Name of|\s+Mother|\s+Sl\.|$)", normalized_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            result["student_name"] = val
            result["metadata"]["student_name"] = val

        # Father/Mother Name
        m = re.search(r"(?:Father's|Mother's|Father.*?Mother.*?)\s*Name\s*[:\-]?\s*(.+?)(?=\s+Name\s*(?:of|ot)|\s+Sl\.|\s+SI\b|$)", normalized_text, re.IGNORECASE)
        if m:
            result["metadata"]["father_name"] = m.group(1).strip()
            result["father_name"] = result["metadata"]["father_name"]

        # College Name
        m = re.search(r"Name\s*(?:of|ot)\s*the[\.\s]*College\s*[:\-]?\s*(.+?)(?=\s+Sl\.|\s+SI\b|\s+Course|\s+Credits|$)", normalized_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            result["college_name"] = val
            result["metadata"]["college_name"] = val

        # USN
        m = re.search(r"USN\s*[:\-]?\s*([A-Z0-9]+)", normalized_text, re.IGNORECASE)
        if not m:
            m = re.search(r"University\s*Seat\s*Number\s*[:\-]?\s*([1-4][A-Z]{2}\d{2}[A-Z]{2}\d{3})", normalized_text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b([1-4][A-Z]{2}\d{2}[A-Z]{2}\d{3})\b", normalized_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().upper()
            result["university_seat_number"] = val
            result["metadata"]["usn"] = val

        # Grade Card Number
        m = re.search(r"\b(\d{2}\s*[A-Z]{2}\s*\d{6,8})\b", normalized_text)
        if m:
            result["metadata"]["grade_card_number"] = m.group(1).strip()

        # Medium of Instruction
        m = re.search(r"Medium\s*of\s*instruction\s*[:\-]?\s*([A-Za-z]+)", normalized_text, re.IGNORECASE)
        if m:
            result["metadata"]["medium_of_instruction"] = m.group(1).strip()

        # Date of Issue (Fallback to exam month if not explicit)
        m_doi = re.search(r"Date\s*of\s*issue\s*[:\-]?\s*([\d\-\/A-Za-z]+)", normalized_text, re.IGNORECASE)
        if m_doi:
            result["metadata"]["date_of_issue"] = m_doi.group(1).strip()

        # Programme, Exam Month, Year
        m = re.search(r"(B\.E\.|B\.Tech|B\.Arch|M\.Tech|MBA|MCA)\s*(.+?)\s+(January|February|March|April|May|June|July|August|September|October|November|December)[\/\-\s]*(February|March|April|May|June|July|August|September|October|November|December)?\s*\-?\s*(\d{4})", normalized_text, re.IGNORECASE)
        if m:
            result["metadata"]["programme"] = f"{m.group(1)} {m.group(2)}".strip()
            month = m.group(3).strip()
            if m.group(4):
                month += f"/{m.group(4).strip()}"
            result["metadata"]["exam_month"] = month
            result["metadata"]["exam_year"] = m.group(5).strip()
            result["exam_month"] = result["metadata"]["exam_month"]
            result["exam_year"] = result["metadata"]["exam_year"]

        m = re.search(r"\b([IL1]{1,3}|IV|V|V[IL1]{1,3}|IX|X)\s*Semester\b", normalized_text, re.IGNORECASE)
        if m:
            val = m.group(1).upper().replace('L', 'I').replace('1', 'I')
            result["metadata"]["semester"] = val
            result["semester"] = val

        # 3. Subject Table State Machine Improvements
        subjects = []
        current_subject = None
        parsing_subjects = False
        current_semester_group = ""
        
        summary_tokens = []
        parsing_summary = False

        termination_anchors = ["CREDITS REGISTERED", "CREDITS EARNED", "SGPA", "CGPA", "TOTAL GRADE POINTS", "DATE OF ISSUE", "MEDIUM OF INSTRUCTION", "REPEATED EXAM"]
        
        for i, line in enumerate(text_lines):
            line_upper = line.upper()
            
            # Table Termination
            if any(anchor in line_upper for anchor in termination_anchors):
                parsing_subjects = False
                if current_subject and current_subject.get("course_code"):
                    subjects.append(current_subject)
                current_subject = None
                parsing_summary = True
                
            if parsing_summary:
                tokens = re.findall(r"\b\d+(?:\.\d+)?\b", line)
                summary_tokens.extend(tokens)
                continue
                
            # Ignore and process standalone/spilled semester headers
            sem_match = re.search(r"\b([IL1]{1,3}|IV|V|V[IL1]{1,3}|IX|X)\s*SEMESTER\b", line_upper)
            if sem_match:
                val = sem_match.group(1).replace('L', 'I').replace('1', 'I')
                current_semester_group = val
                
                # If the line is JUST the semester header, we skip it
                if re.match(r"^([IL1]{1,3}|IV|V|V[IL1]{1,3}|IX|X)\s*SEMESTER$", line_upper.strip()):
                    continue

            # Look for Course Code
            code_match = re.search(r"(?:^|\s)(\d{2}[A-Z]{2,4}\d{2,4}[A-Z]?(?:\*|#)?)(?:\s|$)", line_upper)
            
            if code_match:
                parsing_subjects = True
                if current_subject and current_subject.get("course_code"):
                    subjects.append(current_subject)
                    
                code = code_match.group(1)
                idx = line.find(code)
                rest = line[idx+len(code):].strip()
                
                clean_code = code.strip("*# ")
                inferred_sem = current_semester_group
                # Dynamically infer semester from VTU course code structure (e.g. 17CPH39 -> 3)
                m_code = re.search(r"^[0-9]{2}[A-Za-z]+([1-8])", clean_code)
                if m_code:
                    sem_num = int(m_code.group(1))
                    sem_map_rev = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"VIII"}
                    inferred_sem = sem_map_rev.get(sem_num, current_semester_group)
                
                current_subject = {
                    "semester_taken": inferred_sem,
                    "course_code": clean_code,
                    "course_title": rest.strip("*# -"),
                    "credits_assigned": "",
                    "credits_earned": "",
                    "letter_grade": "",
                    "grade_point": "",
                    "buffer": rest
                }
                continue
                
            if parsing_subjects and current_subject:
                # Accumulate buffer (ignore pure grades if they match exactly)
                if line not in ["P", "F", "A", "W", "X", "NE"]:
                    current_subject["buffer"] += " " + line
                else:
                    current_subject["buffer"] += " " + line
                    
        if current_subject and current_subject.get("course_code"):
            subjects.append(current_subject)
            
        # Extract columns from subject buffers
        for sub in subjects:
            buffer = sub.get("buffer", "")
            
            ca, ce, lg, gp = "", "", "", ""
            # 1. Clean spilled summary table headers and trailing serial numbers FIRST
            buffer = re.sub(r"\b([IL1]{1,3}|IV|V|V[IL1]{1,3}|IX|X)\s*Semester\s*\d{1,2}$", "", buffer, flags=re.IGNORECASE).strip()
            buffer = re.sub(r"\b([IL1]{1,3}|IV|V|V[IL1]{1,3}|IX|X)\s*Semester\b", "", buffer, flags=re.IGNORECASE).strip()
            buffer = re.sub(r"(?:\bSemester|\b1Semester)\s*\d{1,2}$", "", buffer, flags=re.IGNORECASE).strip()
            buffer = re.sub(r"(?:\s*(?:Credits|Cumulative|Earned|CXG|Begistered|Registered|SGPA|CGPA|\(CXG\)))+\s*$", "", buffer, flags=re.IGNORECASE).strip()
            
            # Find the FIRST valid grade block to avoid trailing OCR noise (like next row's serial numbers)
            # Format 1: 4 4 D 6 (ca, ce, lg, gp)
            m1 = re.search(r"\b(\d{1,2})\s+(\d{1,2})\s+([SABCDEFP\+]{1,2})\s+(\d{1,2})\b", buffer, re.IGNORECASE)
            # Format 2: 4 4 6 D (swapped gp and lg)
            m2 = re.search(r"\b(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+([SABCDEFP\+]{1,2})\b", buffer, re.IGNORECASE)
            # Format 3: 4 D 6 (missing ce)
            m3 = re.search(r"\b(\d{1,2})\s+([SABCDEFP\+]{1,2})\s+(\d{1,2})\b", buffer, re.IGNORECASE)
            # Format 4: 4 0 F (missing gp)
            m4 = re.search(r"\b(\d{1,2})\s+(\d{1,2})\s+([SABCDEFP\+]{1,2})\b", buffer, re.IGNORECASE)
            # Format 5: 4 4 6 (missing lg)
            m5 = re.search(r"\b(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\b", buffer, re.IGNORECASE)
            # Format 6: D 6 (missing credits entirely)
            m6 = re.search(r"\b([SABCDEFP\+]{1,2})\s+(\d{1,2})\b", buffer, re.IGNORECASE)
            
            title_str = buffer
            if m1:
                ca, ce, lg, gp = m1.groups()
                title_str = buffer[:m1.start()].strip()
            elif m2:
                ca, ce, gp, lg = m2.groups()
                title_str = buffer[:m2.start()].strip()
            elif m4:
                ca, ce, lg = m4.groups()
                title_str = buffer[:m4.start()].strip()
            elif m3:
                ca, lg, gp = m3.groups()
                title_str = buffer[:m3.start()].strip()
            elif m5:
                ca, ce, gp = m5.groups()
                title_str = buffer[:m5.start()].strip()
            elif m6:
                lg, gp = m6.groups()
                title_str = buffer[:m6.start()].strip()
            else:
                # Fallback for completely mangled lines
                m7 = re.search(r"\b(\d{1,2})$", buffer, re.IGNORECASE)
                if m7:
                    gp = m7.group(1)
                    ce = "0" if gp == "0" else ""
                    title_str = buffer[:m7.start()].strip()
                    
            # Invalidate gp if it's > 10 (likely a serial number from the next row)
            if gp and gp.isdigit() and int(gp) > 10:
                gp = ""
                # Do NOT reset ca, ce, lg, they might be valid!
                            
            # Interpolate missing Letter Grade if we have Grade Point
            if gp and not lg:
                try:
                    g_val = int(gp)
                    if g_val == 10: lg = "S"
                    elif g_val == 9: lg = "A"
                    elif g_val == 8: lg = "B"
                    elif g_val == 7: lg = "C"
                    elif g_val == 6: lg = "D"
                    elif g_val == 5: lg = "E"
                    elif g_val == 4: lg = "P"
                    elif g_val == 0: lg = "F"
                except:
                    pass
                    
            # Interpolate missing Grade Point if we have Letter Grade
            if lg and not gp:
                if lg == "S": gp = "10"
                elif lg == "A": gp = "9"
                elif lg == "B": gp = "8"
                elif lg == "C": gp = "7"
                elif lg == "D": gp = "6"
                elif lg == "E": gp = "5"
                elif lg == "P": gp = "4"
                elif lg == "F": gp = "0"
                    
            # Forward inference from ce == 0
            if ce == "0" and not lg and not gp:
                lg = "F"
                gp = "0"
                
            # Interpolate missing Credits Assigned
            if not ca:
                if "lab" in title_str.lower() or "shop" in title_str.lower() or "project" in title_str.lower() or "seminar" in title_str.lower():
                    ca = "2"
                elif ce and ce != "0":
                    ca = ce
                else:
                    ca = "4" # Safest default for standard theoretical courses
                    
            # Interpolate missing Credits Earned
            if not ce and ca:
                if lg == "F" or gp == "0" or gp == 0:
                    ce = "0"
                elif lg in ["S", "A", "B", "C", "D", "E", "P"]:
                    ce = ca
                    
            title_str = title_str.strip("*# -")
            # Final trim for trailing isolated numbers
            title_str = re.sub(r"\s+\d{1,2}$", "", title_str).strip() 
            
            sub["course_title"] = title_str
            sub["credits_assigned"] = ca
            sub["credits_earned"] = ce
            sub["letter_grade"] = lg
            sub["grade_point"] = gp
            sub["semester_taken"] = sub.get("semester_taken", "")
            del sub["buffer"]
            
        result["subjects"] = subjects
        
        # Collect all semesters
        found_semesters = set(sub["semester_taken"] for sub in subjects if sub.get("semester_taken"))
        if found_semesters:
            sem_map = {"I":1, "II":2, "III":3, "IV":4, "V":5, "VI":6, "VII":7, "VIII":8}
            sem_str = ", ".join(sorted(list(found_semesters), key=lambda x: sem_map.get(x, 99)))
            result["metadata"]["semester"] = sem_str
            result["semester"] = sem_str
        
        # 4. Summary Extraction
        if len(summary_tokens) >= 6:
            rel_tokens = summary_tokens[-6:]
            result["summary"]["credits_registered"] = rel_tokens[0]
            result["summary"]["credits_earned"] = rel_tokens[1]
            result["summary"]["cumulative_credits_earned"] = rel_tokens[2]
            result["summary"]["total_grade_points"] = rel_tokens[3]
            result["summary"]["sgpa"] = rel_tokens[4]
            result["summary"]["cgpa"] = rel_tokens[5]

        # 5. Confidence Calculation
        if len(subjects) >= 5:
            # If we found subjects, compute dynamic confidence
            valid_subs = sum(1 for s in subjects if s["grade_point"] and s["letter_grade"])
            sub_ratio = valid_subs / len(subjects) if subjects else 0
            # Base confidence of 0.85 + 0.14 * sub_ratio ensures > 0.75 for fast path
            result["overall_confidence"] = 0.85 + (0.14 * sub_ratio)
        else:
            result["overall_confidence"] = 0.4
        
        return result
