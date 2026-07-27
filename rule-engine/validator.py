import os
import sys
import importlib.util
from typing import Dict, Any, List

class DocumentRuleValidator:
    """
    Coordinates and runs rule audits for the document under inspection.
    """
    @classmethod
    def get_rule_evaluator(cls, doc_type: str):
        """
        Dynamically loads the rule module from the rule-engine directory.
        This handles the hyphenated directory name robustly in Python.
        """
        doc_type_clean = doc_type.upper().strip()
        
        # Map registry/processor document types to rules modules
        module_mapping = {
            "AADHAAR": "aadhaar.py",
            "AADHAAR CARD": "aadhaar.py",
            
            "PAN": "pan.py",
            "PAN CARD": "pan.py",
            
            "DL": "dl.py",
            "DRIVING LICENSE": "dl.py",
            "DL_KA": "dl.py",
            "DL_MH": "dl.py",
            
            "PASSPORT": "passport.py",
            
            "VTU": "marksheet.py",
            "VTU GRADE CARD": "marksheet.py",
            "MARKSHEET": "marksheet.py",
            "ANDHRA_PRADESH": "marksheet.py",
            "PROVISIONAL CERTIFICATE": "marksheet.py",
            "ASSAM_DIBRUGARH": "marksheet.py",
            "SEMESTER GRADE REPORT": "marksheet.py",
            
            "GST": "gst.py",
            "GST REGISTRATION CERTIFICATE": "gst.py",
            
            "INCORPORATION": "mca.py",
            "CERTIFICATE OF INCORPORATION": "mca.py",
            
            "US_DL_CA": "us_dl.py",
            "CALIFORNIA DRIVER LICENSE": "us_dl.py",
            "US_DL_FL": "us_dl.py",
            "FLORIDA DRIVER LICENSE": "us_dl.py",
            
            "SUNY_TRANSCRIPT": "suny_transcript.py",
            "SUNY ACADEMIC TRANSCRIPT": "suny_transcript.py",
            
            "US_BANK_STATEMENT": "us_bank_statement.py",
            "US BANK STATEMENT": "us_bank_statement.py"
        }
        
        filename = module_mapping.get(doc_type_clean)
        if not filename:
            return None
            
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, filename)
        
        if not os.path.exists(file_path):
            return None
            
        # Spec-based dynamic loading to support 'rule-engine' hyphen in directory
        module_name = f"rule_engine_{filename.split('.')[0]}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Instantiate corresponding class
            class_mapping = {
                "aadhaar.py": "AadhaarRules",
                "pan.py": "PanRules",
                "passport.py": "PassportRules",
                "marksheet.py": "MarksheetRules",
                "dl.py": "DrivingLicenseRules",
                "gst.py": "GstRules",
                "mca.py": "McaRules",
                "us_dl.py": "USDrivingLicenseRules",
                "suny_transcript.py": "SUNYTranscriptRules",
                "us_bank_statement.py": "USBankStatementRules"
            }
            class_name = class_mapping.get(filename)
            if class_name and hasattr(module, class_name):
                return getattr(module, class_name)()
        except Exception as e:
            print(f"Error loading rule evaluator {class_name}: {e}", file=sys.stderr)
            
        return None

    @classmethod
    def validate(cls, doc_type: str, extracted_data: Dict[str, Any], full_text: str, lines: List[str], font_info: Dict[str, Any], file_path: str = None) -> Dict[str, Any]:
        evaluator = cls.get_rule_evaluator(doc_type)
        if evaluator:
            res = evaluator.evaluate(extracted_data, full_text, lines, font_info, file_path)
            res["verification_method"] = getattr(evaluator, "verification_method", "Format Matching")
            return res
        return {"flags": [], "points": 0, "verification_method": "None"}
