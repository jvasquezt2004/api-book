from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SearchParams(BaseModel):
    """
    Parameters for searching books in the vectorstore
    """
    query: str
    dominant_sentiment: Optional[str] = None
    limit: int = 10
    offset: int = 0

class GetSummaryParams(BaseModel):
    title: str
    original_description: str
    

class UploadBookParams(BaseModel):
    content: str
    metadata: Dict[str, Any]

class SearchResult(BaseModel):
    """
    Format for individual search results
    """
    uuid: str
    content: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    """
    Response format for search endpoint
    """
    results: List[SearchResult]
    limit: int
    offset: int
    total: int

class ErrorResponse(BaseModel):
    """
    Response format for errors
    """
    error: str
    details: Optional[str] = None

class ClassifyBookParams(BaseModel):
    """
    Parameters for classifying a book's content to get category and sentiment
    """
    content: str  # El contenido es obligatorio
    category: Optional[str] = None  # Categoría opcional, se obtendrá automáticamente si es None
    dominant_sentiment: Optional[str] = None  # Sentimiento opcional, se obtendrá automáticamente si es None
