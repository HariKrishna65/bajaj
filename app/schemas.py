from pydantic import BaseModel
from typing import List


class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float


class PageLineItems(BaseModel):
    page_no: str
    page_type: str
    bill_items: List[BillItem]


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
