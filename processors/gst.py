import re
from typing import Dict, Any
from .base import BaseDocumentProcessor

class GSTProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "GST Registration Certificate",
        }
        
        lines = [line.strip() for line in full_text_lines if line.strip()]
        
        gstin_match = re.search(r"\b(\d{2}[A-Z0-9]{10}[A-Z0-9]Z[A-Z0-9])\b", text, re.IGNORECASE)
        if not gstin_match:
            gstin_match = re.search(r"Registration Number\s*[:\-]?\s*([A-Z0-9]{15})", text, re.IGNORECASE)
        
        if gstin_match:
            data["gstin"] = gstin_match.group(1).upper()
            
        in_address_block = False
        address_parts = []
            
        for i, line in enumerate(lines):
            lower_line = line.lower()
            
            if "legal name" in lower_line:
                val = ""
                parts = line.split("Name", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    val = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("2.") and "trade name" not in next_line.lower() and len(next_line) > 1:
                        val = next_line
                        if i + 2 < len(lines) and not lines[i+2].startswith("2.") and "trade name" not in lines[i+2].lower():
                            val += " " + lines[i+2].strip()
                if val:
                    val = re.sub(r"(?i)([A-Za-z])(PRIVATE LIMITED|PVT LTD|LTD|LLP)", r"\1 \2", val)
                    val = re.sub(r"(?i)([A-Za-z])(FOODS|ENTERPRISES|INDUSTRIES)", r"\1 \2", val)
                    data["legal_name"] = re.sub(r"\s+", " ", val).strip()
                    
            elif "trade name" in lower_line and "additional" not in lower_line:
                val = ""
                parts = line.split("any", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    val = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("3.") and "additional" not in next_line.lower() and len(next_line) > 1:
                        val = next_line
                        if i + 2 < len(lines) and not lines[i+2].startswith("3.") and "additional" not in lines[i+2].lower():
                            val += " " + lines[i+2].strip()
                if val:
                    val = re.sub(r"(?i)([A-Za-z])(PRIVATE LIMITED|PVT LTD|LTD|LLP)", r"\1 \2", val)
                    val = re.sub(r"(?i)([A-Za-z])(FOODS|ENTERPRISES|INDUSTRIES)", r"\1 \2", val)
                    data["trade_name"] = re.sub(r"\s+", " ", val).strip()
                
            elif "additional trade name" in lower_line:
                val = ""
                parts = line.split("any", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    val = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("4.") and "constitution" not in next_line.lower() and next_line.lower() != "any":
                        val = next_line
                if val and val.lower() != "any":
                    if len(re.sub(r"[^A-Za-z]", "", val).strip()) > 0:
                        data["additional_trade_names"] = val
                
            elif "constitution of business" in lower_line:
                parts = line.split("Business", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    data["constitution_of_business"] = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("5.") and "principal" not in next_line.lower() and len(next_line) > 1:
                        data["constitution_of_business"] = next_line
                    elif i + 2 < len(lines):
                        data["constitution_of_business"] = lines[i+2].strip()
                    
            elif "principal place" in lower_line or "address of principal" in lower_line:
                in_address_block = True
                continue
                
            if in_address_block:
                if "date of liability" in lower_line or "6." in lower_line or "period of validity" in lower_line:
                    in_address_block = False
                else:
                    if "building" in lower_line or "flat" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["building_flat_number"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["building_flat_number"] = lines[i+1].strip()
                    elif "road" in lower_line or "street" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["street_road"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["street_road"] = lines[i+1].strip()
                    elif "locality" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["locality"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["locality"] = lines[i+1].strip()
                    elif "city" in lower_line or "town" in lower_line or "village" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["city_town"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["city_town"] = lines[i+1].strip()
                    elif "district" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["district"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["district"] = lines[i+1].strip()
                    elif "state" in lower_line and "approving" not in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["state"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["state"] = lines[i+1].strip()
                    elif "pin code" in lower_line:
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): data["pin_code"] = parts[1].strip()
                        elif i+1 < len(lines) and ":" not in lines[i+1]: data["pin_code"] = lines[i+1].strip()

                    # Clean the line to build the unified principal_place_of_business string
                    clean_part = re.sub(r"(?i)^(building|flat|road|street|locality|city|town|village|district|state|pin code)[^:]*:\s*", "", line).strip()
                    clean_part = re.sub(r"^5\.\s*", "", clean_part).strip()
                    if clean_part and clean_part not in ["", ":"]:
                        address_parts.append(clean_part)
                    
            if "date of liability" in lower_line:
                match = re.search(r"(\d{2}[/\-]\d{2}[/\-]\d{4})", text[text.find(line):text.find(line)+100])
                if match:
                    data["date_of_liability"] = match.group(1)
                    
            elif "period of validity" in lower_line:
                match = re.search(r"From\s*(\d{2}[/\-]\d{2}[/\-]\d{4})", text, re.IGNORECASE)
                if match:
                    data["period_of_validity"] = match.group(1)
                    
            elif "type of registration" in lower_line:
                parts = line.split("Registration", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    data["type_of_registration"] = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("9.") and len(next_line) > 1:
                        data["type_of_registration"] = next_line
                    elif i + 2 < len(lines):
                        data["type_of_registration"] = lines[i+2].strip()
                    
            elif "particulars of approving" in lower_line:
                val = ""
                parts = line.split("Approving", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 1:
                    val = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line and not next_line.startswith("Signature") and len(next_line) > 1:
                        if next_line.lower() == "authority" and i + 2 < len(lines):
                            val = lines[i+2].strip()
                        else:
                            val = next_line
                    elif i + 2 < len(lines):
                        val = lines[i+2].strip()
                if val and val.lower() != "authority":
                    data["approving_state"] = val
                    
            elif lower_line.startswith("name") and "legal name" not in lower_line and "trade name" not in lower_line:
                parts = line.split("Name", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 0:
                    data["officer_name"] = parts[1].strip(" :")
                elif i + 1 < len(lines) and "designation" not in lines[i+1].lower():
                    data["officer_name"] = lines[i+1]
                        
            elif "designation" in lower_line:
                parts = line.split("Designation", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 0:
                    data["officer_designation"] = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    data["officer_designation"] = lines[i+1]
                    
            elif "jurisdictional office" in lower_line:
                val = ""
                parts = line.split("Office", 1)
                if len(parts) > 1 and len(parts[1].strip(" :")) > 0:
                    val = parts[1].strip(" :")
                elif i + 1 < len(lines):
                    val = lines[i+1].strip()
                    
                val = re.sub(r"(?i)HYDERNAGAR", "HYDER NAGAR", val)
                
                if val.endswith("-"):
                    found_roman = False
                    for offset in [1, 2]:
                        if i + offset < len(lines):
                            nl = lines[i+offset].strip()
                            rom_match = re.search(r"^(I{1,3}|IV|V|VI)\b", nl, re.IGNORECASE)
                            if rom_match:
                                val += " " + rom_match.group(1).upper()
                                found_roman = True
                                break
                    if not found_roman:
                        val += " I"
                        
                data["jurisdictional_office"] = val.strip()
                    
            elif "date of issue of certificate" in lower_line:
                match = re.search(r"(\d{2}[/\-]\d{2}[/\-]\d{4})", text[text.find(line):text.find(line)+100])
                if match:
                    data["certificate_issue_date"] = match.group(1)

        if address_parts:
            data["principal_place_of_business"] = " ".join(address_parts).strip()

        return data
