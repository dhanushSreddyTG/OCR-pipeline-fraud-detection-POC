import os
import io
import fitz  # PyMuPDF
import pytesseract
import sys
from PIL import Image

# --- Checksum Algorithms ---
def is_luhn_valid(num_str):
    if not num_str.isdigit() or len(num_str) < 13: return True # Ignore non-cc
    digits = [int(c) for c in num_str]
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9: digits[i] -= 9
    return sum(digits) % 10 == 0

def is_verhoeff_valid(num_str):
    if not num_str.isdigit() or len(num_str) != 12: return True
    d = [[0,1,2,3,4,5,6,7,8,9], [1,2,3,4,0,6,7,8,9,5], [2,3,4,0,1,7,8,9,5,6], [3,4,0,1,2,8,9,5,6,7], [4,0,1,2,3,9,5,6,7,8], [5,9,8,7,6,0,4,3,2,1], [6,5,9,8,7,1,0,4,3,2], [7,6,5,9,8,2,1,0,4,3], [8,7,6,5,9,3,2,1,0,4], [9,8,7,6,5,4,3,2,1,0]]
    p = [[0,1,2,3,4,5,6,7,8,9], [1,5,7,6,2,8,3,0,9,4], [5,8,0,3,7,9,6,1,4,2], [8,9,1,6,0,4,3,5,2,7], [9,4,5,3,1,2,6,8,7,0], [4,2,8,6,5,7,3,9,0,1], [2,7,9,3,8,0,6,4,1,5], [7,0,4,6,9,1,3,2,5,8], [0,1,2,3,4,5,6,7,8,9]]
    inv = [0,4,3,2,1,5,6,7,8,9]
    c = 0
    num_array = [int(n) for n in reversed(num_str)]
    try:
        for i, num in enumerate(num_array):
            c = d[c][p[i % 8][num]]
        return c == 0
    except IndexError:
        return True
# ---------------------------

class FontAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_ext = os.path.splitext(file_path)[1].lower()
        self.flags = []
        self.points = 0
        self.extracted_text = ""
        self.text_lines = []
        self.unaligned_count = 0
        self.font_size_anomaly = False
        self.multiple_fonts_detected = False

    def add_flag(self, rule_id, description, severity, points):
        self.flags.append({
            "rule_id": rule_id,
            "description": description,
            "severity": severity,
            "points": points
        })
        self.points += points

    def analyze(self):
        report = {"extracted": {}, "red_flags": [], "risk_score": 0, "risk_level": "Low", "font_info": {}}
        if self.file_ext == ".pdf":
            self.analyze_pdf_fonts()
        elif self.file_ext in [".docx", ".xlsx", ".pptx"]:
            self.analyze_office_text()
        elif self.file_ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff"]:
            self.analyze_image_fonts()
        
        report["red_flags"] = self.flags
        report["risk_score"] = min(100, self.points)
        if report["risk_score"] >= 45:
            report["risk_level"] = "High"
        elif report["risk_score"] >= 16:
            report["risk_level"] = "Medium"
        else:
            report["risk_level"] = "Low"
            
        report["font_info"] = {
            "character_misalignment": self.unaligned_count,
            "font_size_anomaly": self.font_size_anomaly,
            "multiple_fonts_detected": self.multiple_fonts_detected,
            "extracted_text": self.extracted_text,
            "text_lines": self.text_lines
        }
        return report

    def analyze_pdf_fonts(self):
        try:
            doc = fitz.open(self.file_path)
            font_sizes = []
            font_names = set()
            full_text_parts = []
            
            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                blocks = page.get_text("dict").get("blocks", [])
                
                # Extract clean text lines
                text_page = page.get_text("text")
                full_text_parts.append(text_page)
                for line in text_page.split("\n"):
                    if line.strip():
                        self.text_lines.append(line.strip())
                        
                for b in blocks:
                    if "lines" in b:
                        for l in b["lines"]:
                            for s in l["spans"]:
                                font_sizes.append(s["size"])
                                font_names.add(s["font"])
                                
            self.extracted_text = "\n".join(full_text_parts)

            # Scanned PDF check: if digital text is empty, fall back to page-rendering OCR
            if not self.extracted_text.strip():
                full_text_parts = []
                for page_num in range(min(5, len(doc))):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    text_page = pytesseract.image_to_string(img)
                    full_text_parts.append(text_page)
                    for line in text_page.split("\n"):
                        if line.strip():
                            self.text_lines.append(line.strip())
                self.extracted_text = "\n".join(full_text_parts)
            
            if len(font_names) > 5:
                self.multiple_fonts_detected = True
                self.add_flag("MULTIPLE_FONTS_DETECTED", f"Detected unusually high number of fonts: {len(font_names)}", "Medium", 20)
            
            if font_sizes:
                avg_size = sum(font_sizes) / len(font_sizes)
                outliers = [s for s in font_sizes if abs(s - avg_size) > 10.0]
                if outliers and len(outliers) < len(font_sizes) * 0.05:
                     self.font_size_anomaly = True
                     self.add_flag("FONT_SIZE_ANOMALY", "Detected irregular text sizes that could indicate tampering.", "Medium", 25)

            doc.close()
        except Exception as e:
            print(f"Error in PDF font analysis: {e}", file=sys.stderr)

    def analyze_office_text(self):
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(self.file_path) as z:
                # 1. DOCX Text Extraction
                if 'word/document.xml' in z.namelist():
                    xml_content = z.read('word/document.xml')
                    root = ET.fromstring(xml_content)
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    texts = []
                    for p in root.findall('.//w:p', ns):
                        p_text_parts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                        p_text = "".join(p_text_parts).strip()
                        if p_text:
                            texts.append(p_text)
                            self.text_lines.append(p_text)
                    self.extracted_text = "\n".join(texts)
                
                # 2. XLSX Text Extraction
                elif 'xl/sharedStrings.xml' in z.namelist():
                    xml_content = z.read('xl/sharedStrings.xml')
                    root = ET.fromstring(xml_content)
                    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    texts = [t.text for t in root.findall('.//ns:t', ns) if t.text]
                    self.extracted_text = "\n".join(texts)
                    self.text_lines = [t.strip() for t in texts if t.strip()]

                # 3. PPTX Text Extraction
                elif 'ppt/slides/slide1.xml' in z.namelist():
                    slide_texts = []
                    for name in sorted(z.namelist()):
                        if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                            xml_content = z.read(name)
                            root = ET.fromstring(xml_content)
                            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                            texts = [t.text for t in root.findall('.//a:t', ns) if t.text]
                            slide_texts.extend(texts)
                    self.extracted_text = "\n".join(slide_texts)
                    self.text_lines = [t.strip() for t in slide_texts if t.strip()]
        except Exception as e:
            print(f"Error in office document text analysis: {e}", file=sys.stderr)

    def analyze_image_fonts(self):
        try:
            import re
            img = Image.open(self.file_path)
            
            # --- Checksum Validation ---
            full_text = pytesseract.image_to_string(img)
            self.extracted_text = full_text
            self.text_lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            
            # Find contiguous digits
            numbers = re.findall(r'\d+', full_text.replace(" ", "").replace("-", ""))
            for num in numbers:
                if len(num) == 12 and not is_verhoeff_valid(num):
                    self.add_flag("CHECKSUM_FAILED_VERHOEFF", f"Aadhar-style 12-digit number failed Verhoeff checksum validation.", "High", 45)
                elif len(num) >= 15 and len(num) <= 19 and not is_luhn_valid(num):
                    self.add_flag("CHECKSUM_FAILED_LUHN", f"Credit card-style number failed Luhn checksum validation.", "High", 45)
            # ---------------------------

            boxes_str = pytesseract.image_to_boxes(img)
            
            # Parse boxes: char left bottom right top page
            # Note: pytesseract boxes have origin at BOTTOM-LEFT
            boxes = []
            for line in boxes_str.split('\n'):
                if line.strip():
                    parts = line.split(' ')
                    if len(parts) >= 6:
                        char = parts[0]
                        left = int(parts[1])
                        bottom = int(parts[2])
                        right = int(parts[3])
                        top = int(parts[4])
                        boxes.append({"char": char, "left": left, "bottom": bottom, "right": right, "top": top})
            
            # Group boxes by roughly same horizontal baseline (bottom coordinate)
            # Since origin is bottom-left, y is 'bottom'
            lines = []
            current_line = []
            
            # Sort by top/bottom first to group into lines roughly
            boxes.sort(key=lambda b: (b['bottom'], b['left']))
            
            for b in boxes:
                if not current_line:
                    current_line.append(b)
                else:
                    # If the bottom is within 15 pixels, consider it same line
                    avg_bottom = sum(cb['bottom'] for cb in current_line) / len(current_line)
                    if abs(b['bottom'] - avg_bottom) < 15:
                        current_line.append(b)
                    else:
                        lines.append(current_line)
                        current_line = [b]
            if current_line:
                lines.append(current_line)
            
            unaligned = 0
            for line in lines:
                if len(line) > 3:
                    # Sort left to right
                    line.sort(key=lambda b: b['left'])
                    
                    # Calculate median bottom and top for the line
                    bottoms = [b['bottom'] for b in line]
                    tops = [b['top'] for b in line]
                    median_bottom = sorted(bottoms)[len(bottoms)//2]
                    median_top = sorted(tops)[len(tops)//2]
                    
                    # Find characters that deviate significantly from median
                    for b in line:
                        if abs(b['bottom'] - median_bottom) > 4 or abs(b['top'] - median_top) > 4:
                            unaligned += 1
                            
            self.unaligned_count = unaligned
            if unaligned > 0:
                self.add_flag("CHARACTER_MISALIGNMENT", f"Detected {unaligned} individual characters with misaligned baselines or sizes.", "High", 35)

        except Exception as e:
            print(f"Error in Image font analysis: {e}", file=sys.stderr)
