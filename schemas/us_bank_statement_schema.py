from pydantic import BaseModel, Field
from typing import Optional, List
from .base import BaseDocumentSchema

class TransactionSchema(BaseModel):
    date: Optional[str] = Field(None, description="Transaction Date")
    description: Optional[str] = Field(None, description="Transaction Description")
    credits: Optional[float] = Field(0.0, description="Amount Credited")
    debits: Optional[float] = Field(0.0, description="Amount Debited")
    balance: Optional[float] = Field(None, description="Account Balance")

class USBankStatementSchema(BaseDocumentSchema):
    document_type: str = "US Bank Statement"
    bank_name: Optional[str] = Field(None, description="Bank Name (e.g. Ally Bank)")
    customer_name: Optional[str] = Field(None, description="Customer Name")
    statement_date: Optional[str] = Field(None, description="Statement Date")
    account_number: Optional[str] = Field(None, description="Account Number")
    open_date: Optional[str] = Field(None, description="Account Open Date")
    product: Optional[str] = Field(None, description="Product Name (e.g. Money Market Savings Account)")
    beginning_balance: Optional[float] = Field(None, description="Beginning Balance")
    ending_balance: Optional[float] = Field(None, description="Ending Balance")
    total_deposits: Optional[float] = Field(None, description="Total Deposits and Credits")
    total_withdrawals: Optional[float] = Field(None, description="Total Withdrawals and Debits")
    interest_paid_ytd: Optional[float] = Field(None, description="Interest Paid Year to Date")
    interest_paid_period: Optional[float] = Field(None, description="Interest Paid This Period")
    average_daily_balance: Optional[float] = Field(None, description="Average Daily Balance")
    transactions: List[TransactionSchema] = Field(default_factory=list, description="List of transactions")
