import re
from abc import ABC, abstractmethod
from typing import Dict, Any

# GEOGRAPHIC STOP-WORDS to prevent address-as-name misclassification
GEO_MARKERS = {
    "MAHARASHTRA", "BENGALURU", "BANGALORE", "KARNATAKA", "MUMBAI", "DELHI", "INDIA",
    "TOWN", "VILLAGE", "DISTRICT", "DIST", "STREET", "ROAD", "COLONY", "MIRAJ", "SANGARA"
}

class BaseDocumentProcessor(ABC):
    """
    Abstract base class for all document processors.
    Enforces a standard interface for extracting metadata from OCR text.
    """

    @abstractmethod
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        """
        Parses OCR text and extracts key fields for a specific document type.
        """
        pass

    def is_likely_address(self, text: str) -> bool:
        text_upper = text.upper()
        return any(marker in text_upper for marker in GEO_MARKERS) or any(char.isdigit() for char in text)

    def extract_gender_normalized(self, text: str) -> str:
        text_upper = text.upper()
        # Look for standalone words to avoid sub-word matching (e.g., matching "mal" in "Vimal" or "Malini")
        if re.search(r"\b(FEMALE|FEMA1E|FEMAIE)\b", text_upper) or re.search(r"(?<!/)\bF\b(?!/)", text_upper):
            return "F"
        if re.search(r"\b(MALE|MAIE|MAL)\b", text_upper) or re.search(r"(?<!/)\bM\b(?!/)", text_upper):
            return "M"
        return "Unknown"
