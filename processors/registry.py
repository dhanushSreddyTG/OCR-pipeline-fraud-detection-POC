import re
from typing import Dict, Any, Optional
from .base import BaseDocumentProcessor
from .aadhaar import AadhaarProcessor
from .pan import PanProcessor
from .dl import DrivingLicenseProcessor
from .passport import PassportProcessor
from .vtu import VTUProcessor
from .gst import GSTProcessor
from .mca import MCAProcessor
from .anu_ap import ANUProvisionalProcessor
from .assam_dibrugarh import AssamDibrugarhProcessor
from .california_dl import CaliforniaDLProcessor
from .florida_dl import FloridaDLProcessor
from .suny_transcript import SUNYTranscriptProcessor
from .us_bank_statement import USBankStatementProcessor

class DocumentProcessorRegistry:
    _processors: Dict[str, BaseDocumentProcessor] = {}

    @classmethod
    def register(cls, doc_type: str, processor: BaseDocumentProcessor):
        cls._processors[doc_type.upper()] = processor

    @classmethod
    def get_processor(cls, doc_type: str) -> BaseDocumentProcessor:
        return cls._processors.get(doc_type.upper())

    @classmethod
    def extract_document(cls, raw_text: str, lines: list, doc_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Routes to the correct processor using the provided doc_type, or classifies dynamically if None.
        """
        if not doc_type or doc_type == "UNKNOWN":
            text_compact = re.sub(r'[^a-z0-9<]', '', raw_text.lower())
            
            if "california" in text_compact:
                doc_type = "US_DL_CA"
            elif "florida" in text_compact or "getawaylane" in text_compact or re.search(r"\d{3}-\d{3}-\d{2}-\d{3}-\d", raw_text):
                doc_type = "US_DL_FL"
            elif any(k in text_compact for k in ["farmingdale", "stateuniversityofnewyork", "suny"]):
                doc_type = "SUNY_TRANSCRIPT"
            elif any(k in text_compact for k in ["allycom", "allybank", "moneymarketsavings", "combinedcustomerstatement"]):
                doc_type = "US_BANK_STATEMENT"
            elif any(k in text_compact for k in ["driving", "license", "licence", "licenc", "dlno"]):
                doc_type = "DL"
            elif "income" in text_compact or "pan" in text_compact:
                doc_type = "PAN"
            elif any(k in text_compact for k in ["passport", "p<ind", "republicofindia", "paseport"]) or re.search(r"\b[A-Z][0-9]{7}\b", raw_text) or (
                "<<" in raw_text and any(k in text_compact for k in ["ind", "republic"])
            ):
                doc_type = "PASSPORT"
            elif "aadhaar" in text_compact or "uniqueiden" in text_compact or (
                re.search(r"\d{4}\s?\d{4}\s?\d{4}", raw_text) and
                any(k in text_compact for k in ["govt", "india", "uidai", "male", "female", "dob", "birth", "yob"])
            ):
                doc_type = "AADHAAR"
            elif "gst" in text_compact and ("reg06" in text_compact or "registrationcertificate" in text_compact or "gstin" in text_compact):
                doc_type = "GST"
            elif "incorporation" in text_compact or "hereby certify that" in text_compact or "mca.gov.in" in text_compact:
                doc_type = "INCORPORATION"
            elif "acharyanagarjuna" in text_compact or "provisionalcertificate" in text_compact:
                doc_type = "ANDHRA_PRADESH"
            elif "dibrugarh" in text_compact and ("semestergradereport" in text_compact or "assam" in text_compact or "sgpa" in text_compact):
                doc_type = "ASSAM_DIBRUGARH"
            else:
                doc_type = "UNKNOWN"

        processor = cls.get_processor(doc_type)
        if processor:
            return processor.parse(raw_text, lines)
        return {"document_type": "Unknown"}

# Register default processors
DocumentProcessorRegistry.register("AADHAAR", AadhaarProcessor())
DocumentProcessorRegistry.register("PAN", PanProcessor())
DocumentProcessorRegistry.register("DL", DrivingLicenseProcessor())
DocumentProcessorRegistry.register("DL_KA", DrivingLicenseProcessor())
DocumentProcessorRegistry.register("DL_MH", DrivingLicenseProcessor())
DocumentProcessorRegistry.register("PASSPORT", PassportProcessor())
DocumentProcessorRegistry.register("VTU", VTUProcessor())
DocumentProcessorRegistry.register("MARKSHEET", VTUProcessor())
DocumentProcessorRegistry.register("GST", GSTProcessor())
DocumentProcessorRegistry.register("INCORPORATION", MCAProcessor())
DocumentProcessorRegistry.register("ANDHRA_PRADESH", ANUProvisionalProcessor())
DocumentProcessorRegistry.register("ASSAM_DIBRUGARH", AssamDibrugarhProcessor())
DocumentProcessorRegistry.register("US_DL_CA", CaliforniaDLProcessor())
DocumentProcessorRegistry.register("US_DL_FL", FloridaDLProcessor())
DocumentProcessorRegistry.register("SUNY_TRANSCRIPT", SUNYTranscriptProcessor())
DocumentProcessorRegistry.register("US_BANK_STATEMENT", USBankStatementProcessor())
