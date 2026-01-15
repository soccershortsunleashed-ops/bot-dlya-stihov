from pydantic import BaseModel
from typing import Any, Dict

class PaymentWebhook(BaseModel):
    event: str
    type: str
    object: Dict[str, Any]