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
