from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


SemanticFormat = Literal["rdfs", "skos"]


class SemanticModel(BaseModel):
    id: str
    name: str
    format: SemanticFormat
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    enabled: bool = True
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class SemanticModelCreate(BaseModel):
    name: str
    format: SemanticFormat
    content_text: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    enabled: Optional[bool] = True


class SemanticModelUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None


class SemanticModelPreview(BaseModel):
    id: str
    name: str
    format: SemanticFormat
    preview: str


