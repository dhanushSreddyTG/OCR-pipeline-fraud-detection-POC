import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

class BaseRule:
    """
    Base class for all document integrity rules.
    Exposes common utilities for date parsing, rule flag creation, and font evaluation.
    """
    def __init__(self, doc_type: str):
        self.doc_type = doc_type
        self.flags = []
        self.points = 0
        self.verification_method = "Format Matching"

    def add_flag(self, rule_id: str, description: str, severity: str, points: int):
        self.flags.append({
            "rule_id": rule_id,
            "description": description,
            "severity": severity,
            "points": points
        })
        self.points += points

    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Attempts to parse a date string in various common formats (e.g. DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD).
        """
        if not date_str:
            return None
            
        clean_str = re.sub(r"\s+", " ", date_str).strip()
        
        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        def get_month_num(m_val):
            m_clean = m_val.lower()[:3].strip()
            if m_clean.isdigit():
                return int(m_clean)
            return months_map.get(m_clean, 1)

        patterns = [
            (r"^(\d{4})[-/]([A-Za-z0-9]+)[-/](\d{2})$", lambda m: datetime(int(m.group(1)), get_month_num(m.group(2)), int(m.group(3)))),
            (r"^(\d{1,2})[-/]([A-Za-z0-9]+)[-/](\d{4})$", lambda m: datetime(int(m.group(3)), get_month_num(m.group(2)), int(m.group(1)))),
            (r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", lambda m: datetime(int(m.group(3)), months_map.get(m.group(2).lower()[:3], 1), int(m.group(1))))
        ]
        
        for pat, converter in patterns:
            try:
                match = re.match(pat, clean_str)
                if match:
                    return converter(match)
            except Exception:
                pass
        return None

    def evaluate_document_colors(self, file_path: str, doc_name: str):
        if not file_path or not os.path.exists(file_path):
            return
            
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(file_path)
            if img is None:
                return
                
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            # Check if image is grayscale (mean saturation is extremely low)
            avg_sat = np.mean(s)
            if avg_sat < 12.0:
                self.add_flag(
                    rule_id="DOCUMENT_IS_GRAYSCALE",
                    description=f"The uploaded {doc_name} is grayscale or black-and-white. Genuine high-trust documents are expected to be in color to verify chromatic security features.",
                    severity="Medium",
                    points=15
                )
                return  # Skip color range checks if it is grayscale
                
            total_pixels = img.shape[0] * img.shape[1]
            
            if "Aadhaar" in doc_name:
                # Standard Aadhaar light teal/cyan background
                lower_teal = np.array([75, 15, 100])
                upper_teal = np.array([105, 200, 255])
                teal_mask = cv2.inRange(hsv, lower_teal, upper_teal)
                teal_pct = (cv2.countNonZero(teal_mask) / total_pixels) * 100.0
                
                # Standard Aadhaar red logo/stripe
                lower_red1 = np.array([0, 40, 80])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([170, 40, 80])
                upper_red2 = np.array([180, 255, 255])
                red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                red_pct = (cv2.countNonZero(red_mask) / total_pixels) * 100.0
                
                if teal_pct < 1.0:
                    self.add_flag(
                        rule_id="AADHAAR_INVALID_BACKGROUND_COLOR",
                        description=f"Aadhaar card lacks standard light teal/cyan background color (found {teal_pct:.2f}% of pixels in range).",
                        severity="High",
                        points=35
                    )
                if red_pct < 0.05:
                    self.add_flag(
                        rule_id="AADHAAR_INVALID_LOGO_COLOR",
                        description=f"Aadhaar card lacks standard red logo/emblem chromatic signature (found {red_pct:.2f}% of pixels in range).",
                        severity="High",
                        points=35
                    )
                    
            elif "PAN" in doc_name:
                # Standard PAN greenish-blue/teal background
                lower_teal = np.array([80, 20, 80])
                upper_teal = np.array([110, 220, 255])
                teal_mask = cv2.inRange(hsv, lower_teal, upper_teal)
                teal_pct = (cv2.countNonZero(teal_mask) / total_pixels) * 100.0
                
                if teal_pct < 1.5:
                    self.add_flag(
                        rule_id="PAN_INVALID_BACKGROUND_COLOR",
                        description=f"PAN card lacks standard blue/teal background color profile (found {teal_pct:.2f}% of pixels in range).",
                        severity="High",
                        points=35
                    )
                    
            elif "Passport" in doc_name:
                # Passport inside pages background: cream/gold or light cyan
                lower_cream = np.array([15, 10, 100])
                upper_cream = np.array([45, 150, 255])
                lower_cyan = np.array([80, 10, 100])
                upper_cyan = np.array([110, 150, 255])
                
                cream_mask = cv2.inRange(hsv, lower_cream, upper_cream)
                cyan_mask = cv2.inRange(hsv, lower_cyan, upper_cyan)
                bg_mask = cv2.bitwise_or(cream_mask, cyan_mask)
                bg_pct = (cv2.countNonZero(bg_mask) / total_pixels) * 100.0
                
                if bg_pct < 1.5:
                    self.add_flag(
                        rule_id="PASSPORT_INVALID_BACKGROUND_COLOR",
                        description=f"Passport pages lack standard security background cream/teal color profile (found {bg_pct:.2f}% of pixels in range).",
                        severity="High",
                        points=35
                    )
                    
            elif "GST" in doc_name:
                # GST header/emblem green band
                lower_green = np.array([35, 20, 50])
                upper_green = np.array([75, 250, 255])
                green_mask = cv2.inRange(hsv, lower_green, upper_green)
                green_pct = (cv2.countNonZero(green_mask) / total_pixels) * 100.0
                
                if green_pct < 0.08:
                    self.add_flag(
                        rule_id="GST_INVALID_HEADER_COLOR",
                        description=f"GST certificate lacks standard green border/emblem color profile (found {green_pct:.2f}% of pixels in range).",
                        severity="Medium",
                        points=25
                    )
                    
            elif "Driving" in doc_name or "DL" in doc_name:
                # DL header blue band
                lower_blue = np.array([100, 25, 80])
                upper_blue = np.array([130, 250, 255])
                blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
                blue_pct = (cv2.countNonZero(blue_mask) / total_pixels) * 100.0
                
                if blue_pct < 0.5:
                    self.add_flag(
                        rule_id="DL_INVALID_HEADER_COLOR",
                        description=f"Driving License lacks standard blue smartcard header color profile (found {blue_pct:.2f}% of pixels in range).",
                        severity="High",
                        points=30
                    )
                    
        except Exception:
            pass

    def evaluate(self, data: Dict[str, Any], full_text: str, lines: List[str], font_info: Dict[str, Any], file_path: str = None) -> Dict[str, Any]:
        """
        Subclasses implement custom checks and populate flags/points.
        """
        return {"flags": [], "points": 0}
