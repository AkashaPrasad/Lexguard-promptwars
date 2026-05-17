"""Tests for the RiskAgent risk scoring functionality."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from agents.risk_agent import RiskAgent
from models.contract import ExtractedClause, RiskCategory, RiskSeverity, ScoredClause


@pytest.fixture
def agent() -> RiskAgent:
    """Return a RiskAgent instance for testing."""
    return RiskAgent()


@pytest.fixture
def sample_clause() -> ExtractedClause:
    """Return a sample ExtractedClause for testing."""
    return ExtractedClause(
        clause_type="Non-Compete",
        extracted_text="Party B shall not compete worldwide for 5 years.",
        confidence=0.9,
    )


@pytest.fixture
def sample_ip_clause() -> ExtractedClause:
    """Return a sample IP assignment clause."""
    return ExtractedClause(
        clause_type="IP Ownership Assignment",
        extracted_text="All IP created shall be irrevocably assigned to Party A.",
        confidence=0.85,
    )


def test_get_severity_critical(agent: RiskAgent) -> None:
    """Scores 8-10 should map to CRITICAL severity."""
    assert agent._get_severity(8) == RiskSeverity.CRITICAL
    assert agent._get_severity(10) == RiskSeverity.CRITICAL


def test_get_severity_high(agent: RiskAgent) -> None:
    """Scores 6-7 should map to HIGH severity."""
    assert agent._get_severity(6) == RiskSeverity.HIGH
    assert agent._get_severity(7) == RiskSeverity.HIGH


def test_get_severity_medium(agent: RiskAgent) -> None:
    """Scores 4-5 should map to MEDIUM severity."""
    assert agent._get_severity(4) == RiskSeverity.MEDIUM
    assert agent._get_severity(5) == RiskSeverity.MEDIUM


def test_get_severity_low(agent: RiskAgent) -> None:
    """Scores 1-3 should map to LOW severity."""
    assert agent._get_severity(1) == RiskSeverity.LOW
    assert agent._get_severity(3) == RiskSeverity.LOW


def test_compute_overall_score_empty(agent: RiskAgent) -> None:
    """Overall score for empty clause list should be 0."""
    assert agent.compute_overall_score([]) == 0


def test_compute_overall_score_single_critical(agent: RiskAgent) -> None:
    """Single CRITICAL clause with score 10 should yield high overall score."""
    clause = ScoredClause(
        clause_type="Non-Compete",
        extracted_text="text",
        confidence=0.9,
        risk_score=10,
        severity=RiskSeverity.CRITICAL,
        risk_category=RiskCategory.EMPLOYMENT,
        explanation="",
        adversarial_analysis="",
        negotiation_tip="",
        worst_case_scenario="",
    )
    score = agent.compute_overall_score([clause])
    assert score == 100


def test_compute_overall_score_all_low(agent: RiskAgent) -> None:
    """All LOW clauses with score 1 should yield a low overall score."""
    clauses = [
        ScoredClause(
            clause_type=f"Clause {i}",
            extracted_text="text",
            confidence=0.8,
            risk_score=1,
            severity=RiskSeverity.LOW,
            risk_category=RiskCategory.OPERATIONAL,
            explanation="",
            adversarial_analysis="",
            negotiation_tip="",
            worst_case_scenario="",
        )
        for i in range(5)
    ]
    score = agent.compute_overall_score(clauses)
    assert score <= 20


@pytest.mark.asyncio
async def test_score_single_success(agent: RiskAgent, sample_clause: ExtractedClause) -> None:
    """score_single should return a valid ScoredClause on success."""
    pass1 = {
        "risk_score": 9,
        "risk_category": "Employment",
        "explanation": "Very restrictive non-compete.",
        "negotiation_tip": "Narrow the geographic scope.",
    }
    pass2 = {
        "adversarial_analysis": "Prevents party from working in their industry.",
        "worst_case": "Party B cannot work anywhere for 5 years.",
    }
    with patch("agents.risk_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [json.dumps(pass1), json.dumps(pass2)]
        result = await agent.score_single(sample_clause)

    assert isinstance(result, ScoredClause)
    assert result.risk_score == 9
    assert result.severity == RiskSeverity.CRITICAL
    assert result.risk_category == RiskCategory.EMPLOYMENT


@pytest.mark.asyncio
async def test_score_single_clamps_risk_score(agent: RiskAgent, sample_clause: ExtractedClause) -> None:
    """score_single should clamp risk_score to 1-10 range."""
    pass1 = {"risk_score": 15, "risk_category": "Employment", "explanation": "x", "negotiation_tip": "y"}
    pass2 = {"adversarial_analysis": "", "worst_case": ""}
    with patch("agents.risk_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [json.dumps(pass1), json.dumps(pass2)]
        result = await agent.score_single(sample_clause)

    assert result.risk_score == 10


@pytest.mark.asyncio
async def test_score_all_returns_correct_count(agent: RiskAgent) -> None:
    """score_all should return one ScoredClause per input clause."""
    clauses = [
        ExtractedClause(clause_type="Governing Law", extracted_text="California", confidence=0.9),
        ExtractedClause(clause_type="Non-Compete", extracted_text="5 years worldwide", confidence=0.85),
    ]
    pass1 = {"risk_score": 5, "risk_category": "Compliance", "explanation": "ok", "negotiation_tip": "ok"}
    pass2 = {"adversarial_analysis": "", "worst_case": ""}
    meta = {
        "contract_type": "NDA",
        "parties": ["A", "B"],
        "effective_date": None,
        "governing_law": "California",
        "contract_duration": None,
    }

    with patch("agents.risk_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [
            json.dumps(pass1), json.dumps(pass2),
            json.dumps(pass1), json.dumps(pass2),
            json.dumps(meta),
        ]
        scored, metadata = await agent.score_all(clauses, "Contract text here.")

    assert len(scored) == 2
    assert metadata.contract_type == "NDA"


@pytest.mark.asyncio
async def test_score_with_fallback_on_error(agent: RiskAgent, sample_clause: ExtractedClause) -> None:
    """_score_with_fallback should return MEDIUM fallback on exception."""
    with patch("agents.risk_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = Exception("API error")
        result = await agent._score_with_fallback(sample_clause)

    assert result.severity == RiskSeverity.MEDIUM
    assert result.risk_score == 5
    assert result.clause_type == sample_clause.clause_type
