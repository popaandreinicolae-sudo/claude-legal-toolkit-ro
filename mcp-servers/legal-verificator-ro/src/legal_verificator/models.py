"""Pydantic models for Legal Verificator."""

from typing import Optional, List
from pydantic import BaseModel


class CCRSearchResult(BaseModel):
    found: bool
    title: str = ""
    url: str = ""
    printable_url: str = ""
    date: str = ""
    source: str = ""
    error: str = ""


class CCRDecisionText(BaseModel):
    text: str = ""
    source: str = ""
    total_chars: int = 0
    truncated: bool = False
    error: str = ""


class CCRVerification(BaseModel):
    verdict: str = "UNVERIFIABLE"  # CONFIRMED | INCORRECT | UNVERIFIABLE
    actual_subject: str = ""
    relevance_score: float = 0.0
    evidence: str = ""
    error: str = ""


class LegislationResult(BaseModel):
    found: bool
    title: str = ""
    status: str = ""  # in_vigoare | abrogat | modificat
    url: str = ""
    abrogated_by: Optional[str] = None
    error: str = ""


class ArticleText(BaseModel):
    text: str = ""
    source: str = ""
    last_modified: Optional[str] = None
    error: str = ""


class SearchResultItem(BaseModel):
    title: str
    snippet: str = ""
    url: str = ""
    category: str = ""


class Lege5SearchResult(BaseModel):
    results: List[SearchResultItem] = []
    total: int = 0
    error: str = ""


class Lege5Document(BaseModel):
    text: str = ""
    title: str = ""
    metadata: dict = {}
    error: str = ""


class BatchVerifyItem(BaseModel):
    key: str
    verdict: str
    actual_subject: str


class BatchVerifyResult(BaseModel):
    results: List[BatchVerifyItem] = []
    summary: dict = {}
    error: str = ""
