from pydantic import Field, validator
from typing import Optional
import re
from .base import BaseDocumentSchema

class CaliforniaDLSchema(BaseDocumentSchema):
    document_type: str = "California Driver License"
    dl_number: str = Field(..., description="California Driver License Number")
    class_type: Optional[str] = Field(None, description="License Class (e.g. C)")
    expiry_date: Optional[str] = Field(None, description="Expiration date (MM/DD/YYYY)")
    last_name: Optional[str] = Field(None, description="Last Name")
    first_name: Optional[str] = Field(None, description="First Name")
    address: Optional[str] = Field(None, description="Full Address")
    dob: Optional[str] = Field(None, description="Date of Birth (MM/DD/YYYY)")
    sex: Optional[str] = Field(None, description="Gender/Sex (M/F)")
    hair: Optional[str] = Field(None, description="Hair color (e.g. BRN, BLN)")
    eyes: Optional[str] = Field(None, description="Eye color (e.g. BRN, BLU)")
    height: Optional[str] = Field(None, description="Height (e.g. 5'-05\")")
    weight: Optional[str] = Field(None, description="Weight (e.g. 125 lb)")
    issue_date: Optional[str] = Field(None, description="Issue date (MM/DD/YYYY)")

    @validator('dl_number')
    def validate_dl_number(cls, v):
        # California DL: starts with a letter followed by 7 digits, or raw 7-8 digits
        cleaned = re.sub(r"[^A-Z0-9]", "", v.upper())
        if not re.match(r"^[A-Z0-9]\d{6,8}$", cleaned):
            raise ValueError("Invalid California DL number format")
        return cleaned
