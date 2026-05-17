"""Tests for the ClauseAgent clause extraction functionality."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from agents.clause_agent import ClauseAgent
from models.contract import ExtractedClause


@pytest.fixture
def agent() -> ClauseAgent:
    """Return a ClauseAgent instance for testing."""
    return ClauseAgent()


@pytest.fixture
def sample_contract_text() -> str:
    """Return a minimal NDA text for testing."""
    return """
    This Agreement shall be governed by the laws of California.
    The parties agree to keep all information confidential.
    Either party may terminate this agreement at any time without cause.
    All intellectual property created under this agreement shall be assigned to Company A.
    """


@pytest.mark.asyncio
async def test_extract_returns_list(agent: ClauseAgent, sample_contract_text: str) -> None:
    """ClauseAgent.extract should return a list."""
    mock_response = [
        {"clause_type": "Governing Law", "extracted_text": "governed by the laws of California", "confidence": 0.95},
        {"clause_type": "Termination for Convenience", "extracted_text": "terminate this agreement at any time", "confidence": 0.88},
    ]
    with patch("agents.clause_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = json.dumps(mock_response)
        result = await agent.extract(sample_contract_text)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(c, ExtractedClause) for c in result)


@pytest.mark.asyncio
async def test_extract_empty_text(agent: ClauseAgent) -> None:
    """ClauseAgent.extract should return empty list for empty input."""
    result = await agent.extract("")
    assert result == []


@pytest.mark.asyncio
async def test_extract_whitespace_text(agent: ClauseAgent) -> None:
    """ClauseAgent.extract should return empty list for whitespace-only input."""
    result = await agent.extract("   \n\t  ")
    assert result == []


@pytest.mark.asyncio
async def test_extract_handles_invalid_gemini_response(agent: ClauseAgent, sample_contract_text: str) -> None:
    """ClauseAgent.extract should handle non-list Gemini responses gracefully."""
    with patch("agents.clause_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = json.dumps({"error": "unexpected format"})
        result = await agent.extract(sample_contract_text)

    assert result == []


@pytest.mark.asyncio
async def test_extract_filters_invalid_items(agent: ClauseAgent, sample_contract_text: str) -> None:
    """ClauseAgent.extract should skip items missing required fields."""
    mock_response = [
        {"clause_type": "Governing Law", "extracted_text": "California law applies", "confidence": 0.9},
        {"invalid_key": "no clause_type here"},
        {"clause_type": "Non-Compete"},  # missing extracted_text
    ]
    with patch("agents.clause_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = json.dumps(mock_response)
        result = await agent.extract(sample_contract_text)

    assert len(result) == 1
    assert result[0].clause_type == "Governing Law"


@pytest.mark.asyncio
async def test_extract_confidence_bounds(agent: ClauseAgent, sample_contract_text: str) -> None:
    """ClauseAgent.extract should clamp confidence to valid range."""
    mock_response = [
        {"clause_type": "Governing Law", "extracted_text": "California", "confidence": 0.75},
    ]
    with patch("agents.clause_agent.call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = json.dumps(mock_response)
        result = await agent.extract(sample_contract_text)

    assert 0.0 <= result[0].confidence <= 1.0


def test_cuad_clauses_loaded(agent: ClauseAgent) -> None:
    """ClauseAgent should have all 41 CUAD clauses loaded."""
    assert len(agent.cuad_clauses) == 41


def test_cuad_clauses_have_required_fields(agent: ClauseAgent) -> None:
    """Each CUAD clause entry should have required fields."""
    required_fields = {"id", "name", "description", "risk_category", "base_risk_score"}
    for clause in agent.cuad_clauses:
        missing = required_fields - set(clause.keys())
        assert not missing, f"Clause '{clause.get('name')}' missing fields: {missing}"
