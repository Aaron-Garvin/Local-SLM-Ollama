
from pydantic import BaseModel, Field
from typing import Optional

class PersonExtraction(BaseModel):
    name: Optional[str] = Field(description="Full name of the person")
    age: Optional[int] = Field(description="Age in years, None if not mentioned")
    role: Optional[str] = Field(description="Job title or profession")
    location: Optional[str] = Field(description="City or region")
    confidence: Optional[float] = Field(description="0.0-1.0 confidence score for extraction")