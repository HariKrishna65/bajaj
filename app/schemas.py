from pydantic import BaseModel, HttpUrl, Field, field_validator

from typing import List, Literal


class RequestBody(BaseModel):
    document: HttpUrl


class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float


class PageLineItems(BaseModel):
    page_no: str
    page_type: str = Field(
        description="Must be exactly one of: Bill Detail, Final Bill, Pharmacy"
    )
    bill_items: List[BillItem]
    
    @field_validator('page_type')
    @classmethod
    def validate_page_type(cls, v):
        """Ensure page_type is exactly one of the allowed values"""
        valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]
        if v not in valid_types:
            # Try case-insensitive match
            v_lower = str(v).strip().lower()
            for valid_type in valid_types:
                if v_lower == valid_type.lower():
                    return valid_type
            # Default to "Bill Detail" if can't match
            return "Bill Detail"
        return v


class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int


class DataPayload(BaseModel):
    pagewise_line_items: List[PageLineItems]
    total_item_count: int


class SuccessResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsage
    data: DataPayload


class ErrorResponse(BaseModel):
    is_success: bool
    message: str
