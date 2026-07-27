from enum import Enum
from typing import Optional, List, Dict, Any
import re
from pydantic import BaseModel, Field, validator

class DocumentType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    DRIVING_LICENSE = "driving_license"
    PASSPORT = "passport"
    VOTER_ID = "voter_id"
    GST_REGISTRATION = "gst_registration"
    UNKNOWN = "unknown"

class ProcessingPath(str, Enum):
    FAST = "fast_path"
    SLOW = "slow_path"
    NEURAL = "neural_path"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    M = "M"
    F = "F"
    OTHER = "other"
    UNKNOWN = "unknown"

class FraudFlags(BaseModel):
    mismatch_detected: bool = False
    invalid_pattern: bool = False
    low_quality_input: bool = False
    tampering_signs: bool = False
    details: List[str] = []

class FieldConfidence(BaseModel):
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)

class BaseDocument(BaseModel):
    document_type: DocumentType
    processing_path: Optional[ProcessingPath] = None
    overall_confidence: Optional[float] = None
    fraud_flags: Optional[FraudFlags] = None
    raw_text: Optional[str] = None
    face_image: Optional[str] = None # Legacy
    extracted_visual_artifacts: Optional[Dict[str, str]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="_metadata", serialization_alias="_metadata")

class UniversalSchema(BaseDocument):
    """Fallback schema for any document with arbitrary fields."""
    class Config:
        extra = "allow"

class AadhaarSchema(BaseDocument):
    aadhaar_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Gender = Gender.UNKNOWN
    address: Optional[str] = None
    is_front: bool = True

    @validator('aadhaar_number')
    def validate_aadhaar_number(cls, v):
        if v and not re.match(r"^\d{4}\s\d{4}\s\d{4}$", v):
             # Try cleaning it
             cleaned = re.sub(r"\s+", "", v)
             if len(cleaned) == 12:
                 return f"{cleaned[:4]} {cleaned[4:8]} {cleaned[8:]}"
             raise ValueError("Aadhaar must be 12 digits")
        return v

class PANSchema(BaseDocument):
    pan_number: Optional[str] = None
    name: Optional[str] = None
    father_name: Optional[str] = None
    dob: Optional[str] = None

    @validator('pan_number')
    def validate_pan_number(cls, v):
        if v and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", v):
            raise ValueError("Invalid PAN format")
        return v

class DLSchema(BaseDocument):
    dl_number: Optional[str] = None
    card_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    valid_till: Optional[str] = None
    address: Optional[Any] = None
    vehicle_classes: Optional[List[Dict[str, str]]] = None
    issuing_authority: Optional[str] = None
    father_name: Optional[str] = None

class PassportSchema(BaseDocument):
    name: Optional[str] = None
    passport_number: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    dob: Optional[str] = None
    doi: Optional[str] = None
    doe: Optional[str] = None
    gender: Gender = Gender.UNKNOWN
    nationality: Optional[str] = "INDIAN"
    expiry_date: Optional[str] = None
    mrz: Optional[Dict[str, str]] = None
    place_of_birth: Optional[str] = None
    place_of_issue: Optional[str] = None

class VoterIDSchema(BaseDocument):
    voter_id_number: Optional[str] = None
    name: Optional[str] = None
    father_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Gender = Gender.UNKNOWN
    is_front: bool = True

class GSTSchema(BaseDocument):
    gstin: Optional[str] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    additional_trade_names: Optional[str] = None
    constitution_of_business: Optional[str] = None
    principal_place_of_business: Optional[str] = None
    building_flat_number: Optional[str] = None
    street_road: Optional[str] = None
    locality: Optional[str] = None
    city_town: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    date_of_liability: Optional[str] = None
    period_of_validity: Optional[str] = None
    type_of_registration: Optional[str] = None
    approving_state: Optional[str] = None
    officer_name: Optional[str] = None
    officer_designation: Optional[str] = None
    jurisdictional_office: Optional[str] = None
    certificate_issue_date: Optional[str] = None

class UnifiedResponse(BaseModel):
    status: str = "success"
    document_type: DocumentType
    data: Dict[str, Any] # Will be one of the schemas above, cast to dict
    execution_time_ms: float
