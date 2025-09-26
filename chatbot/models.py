# chatbot/models.py
from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class SourceInfo(BaseModel):
    chunk_id: int
    source: str
    content_preview: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[SourceInfo]] = []
