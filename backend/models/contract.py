"""Pydantic models for contract analysis data structures."""
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RiskSeverity(str, Enum):
    """Risk severity levels for contract clauses."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskCategory(str, Enum):
    """Categories of contract risk."""
    FINANCIAL = "Financial"
    PRIVACY = "Privacy"
    IP_OWNERSHIP = "IP/Ownership"
    EMPLOYMENT = "Employment"
    OPERATIONAL = "Operational"
    COMPLIANCE = "Compliance"
    TERMINATION = "Termination"


class ExtractedClause(BaseModel):
    """A clause extracted from a contract document."""
    clause_type: str
    extracted_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: int = Field(default=0, ge=0, le=10)


class ScoredClause(BaseModel):
    """A clause with full risk scoring and analysis."""
    clause_type: str
    extracted_text: str
    confidence: float
    risk_score: int = Field(ge=1, le=10)
    severity: RiskSeverity
    risk_category: RiskCategory
    explanation: str
    adversarial_analysis: str
    negotiation_tip: str
    worst_case_scenario: str


class ContractMetadata(BaseModel):
    """Metadata extracted from a contract document."""
    contract_type: str = "Unknown"
    parties: List[str] = []
    effective_date: Optional[str] = None
    governing_law: Optional[str] = None
    contract_duration: Optional[str] = None


class AnalysisResult(BaseModel):
    """Complete result of contract analysis."""
    analysis_id: str
    filename: str
    overall_risk_score: int = Field(ge=0, le=100)
    overall_severity: RiskSeverity
    clauses: List[ScoredClause]
    metadata: ContractMetadata
    highlighted_html: str = ""
    summary: str = ""
    indian_law_flags: List[str] = []
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    google_cloud_project: str = ""
    services: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: str
