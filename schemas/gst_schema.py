from pydantic import Field
from typing import Optional
from .base import BaseDocumentSchema

class GSTSchema(BaseDocumentSchema):
    document_type: str = "GST Registration Certificate"
    gstin: Optional[str] = Field(None, description="GST Registration Number")
    legal_name: Optional[str] = Field(None, description="Legal Name")
    trade_name: Optional[str] = Field(None, description="Trade Name")
    additional_trade_names: Optional[str] = Field(None, description="Additional Trade Names")
    constitution_of_business: Optional[str] = Field(None, description="Constitution of Business")
    principal_place_of_business: Optional[str] = Field(None, description="Address of Principal Place of Business")
    building_flat_number: Optional[str] = Field(None, description="Building / Flat Number")
    street_road: Optional[str] = Field(None, description="Street / Road")
    locality: Optional[str] = Field(None, description="Locality")
    city_town: Optional[str] = Field(None, description="City / Town")
    district: Optional[str] = Field(None, description="District")
    state: Optional[str] = Field(None, description="State")
    pin_code: Optional[str] = Field(None, description="PIN Code")
    date_of_liability: Optional[str] = Field(None, description="Date of Liability")
    period_of_validity: Optional[str] = Field(None, description="Period of Validity")
    type_of_registration: Optional[str] = Field(None, description="Type of Registration")
    approving_state: Optional[str] = Field(None, description="Particulars of Approving State")
    officer_name: Optional[str] = Field(None, description="Officer Name")
    officer_designation: Optional[str] = Field(None, description="Officer Designation")
    jurisdictional_office: Optional[str] = Field(None, description="Jurisdictional Office")
    certificate_issue_date: Optional[str] = Field(None, description="Date of issue of Certificate")
