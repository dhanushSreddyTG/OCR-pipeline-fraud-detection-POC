from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class FloridaDLSchema(BaseDocumentSchema):
    document_type: str = "Florida Driver License"
    dl_number: str = Field(..., description="Florida Driver License Number (e.g. S514-172-80-844-0)")
    class_type: Optional[str] = Field(None, description="License Class (e.g. E)")
    last_name: Optional[str] = Field(None, description="Last Name")
    first_name: Optional[str] = Field(None, description="First/Middle Name")
    address: Optional[str] = Field(None, description="Full Address")
    dob: Optional[str] = Field(None, description="Date of Birth (MM-DD-YYYY or MM/DD/YYYY)")
    sex: Optional[str] = Field(None, description="Gender/Sex (M/F)")
    height: Optional[str] = Field(None, description="Height (e.g. 5-08)")
    organ_donor: Optional[bool] = Field(None, description="Organ donor status")

    @validator('dl_number')
    def validate_dl_number(cls, v):
        # Florida DL: typically 1 letter followed by 12 digits, often formatted as X000-000-00-000-0
        cleaned = re.sub(r"[^A-Z0-9]", "", v.upper())
        if len(cleaned) != 13:
            raise ValueError("Florida DL number must be 1 letter and 12 digits")
        return v
