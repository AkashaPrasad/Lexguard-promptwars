"""Tests for the LexGuard FastAPI endpoints."""
import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from main import app
from models.contract import (
    AnalysisResult,
    ContractMetadata,
    RiskCategory,
    RiskSeverity,
    ScoredClause,
)


@pytest.fixture
def sample_scored_clause() -> ScoredClause:
    """Return a sample ScoredClause for mocking."""
    return ScoredClause(
        clause_type="Governing Law",
        extracted_text="This agreement is governed by California law.",
        confidence=0.95,
        risk_score=5,
        severity=RiskSeverity.MEDIUM,
        risk_category=RiskCategory.COMPLIANCE,
        explanation="Standard governing law clause.",
        adversarial_analysis="Jurisdiction may be unfavorable.",
        negotiation_tip="Negotiate for home jurisdiction.",
        worst_case_scenario="Foreign jurisdiction litigation.",
    )


@pytest.fixture
def sample_analysis_result(sample_scored_clause: ScoredClause) -> AnalysisResult:
    """Return a sample AnalysisResult for mocking."""
    return AnalysisResult(
        analysis_id="test-id-123",
        filename="test_contract.pdf",
        overall_risk_score=45,
        overall_severity=RiskSeverity.HIGH,
        clauses=[sample_scored_clause],
        metadata=ContractMetadata(
            contract_type="NDA",
            parties=["Company A", "Company B"],
            governing_law="California",
        ),
        summary="Overall risk score: 45/100. Test summary.",
        created_at="2024-01-01T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_health_check() -> None:
    """GET /health should return 200 with healthy status and services dict."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "services" in data
    assert isinstance(data["services"], dict)


@pytest.mark.asyncio
async def test_demo_endpoint() -> None:
    """GET /demo should return 200 with a complete AnalysisResult."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/demo")

    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "overall_risk_score" in data
    assert "clauses" in data
    assert len(data["clauses"]) > 0
    assert "metadata" in data
    assert "summary" in data
    # Verify first clause has all required fields
    clause = data["clauses"][0]
    assert "clause_type" in clause
    assert "risk_score" in clause
    assert "severity" in clause
    assert "explanation" in clause


@pytest.mark.asyncio
async def test_analyze_contract_success(
    sample_analysis_result: AnalysisResult,
) -> None:
    """POST /analyze should return 200 with AnalysisResult on valid PDF."""
    pdf_bytes = b"%PDF-1.4 fake pdf content for testing"

    with (
        patch("main.magic.from_buffer", return_value="application/pdf"),
        patch("main.parse_document", new_callable=AsyncMock) as mock_parse,
        patch("main.clause_agent.extract", new_callable=AsyncMock) as mock_extract,
        patch("main.risk_agent.score_all", new_callable=AsyncMock) as mock_score,
        patch("main.risk_agent.compute_overall_score", return_value=45),
    ):
        mock_parse.return_value = "This is contract text with governing law clause."
        mock_extract.return_value = []
        mock_score.return_value = (
            sample_analysis_result.clauses,
            sample_analysis_result.metadata,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("test_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "overall_risk_score" in data
    assert "clauses" in data


@pytest.mark.asyncio
async def test_analyze_rejects_invalid_mime() -> None:
    """POST /analyze should return 422 for disallowed file types."""
    with patch("main.magic.from_buffer", return_value="application/zip"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("evil.zip", io.BytesIO(b"PK fake zip"), "application/zip")},
            )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_rejects_oversized_file() -> None:
    """POST /analyze should return 413 for files exceeding size limit."""
    big_file = b"x" * (11 * 1024 * 1024)  # 11MB

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/analyze",
            files={"file": ("big.pdf", io.BytesIO(big_file), "application/pdf")},
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_analyze_rejects_empty_text() -> None:
    """POST /analyze should return 422 if no text can be extracted."""
    with (
        patch("main.magic.from_buffer", return_value="application/pdf"),
        patch("main.parse_document", new_callable=AsyncMock, return_value=""),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("empty.pdf", io.BytesIO(b"%PDF empty"), "application/pdf")},
            )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_analysis_not_found() -> None:
    """GET /analysis/{id} should return 404 for unknown IDs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/analysis/nonexistent-id-12345")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_pdf_report_not_found() -> None:
    """GET /report/{id} should return 404 for unknown analysis IDs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/report/nonexistent-id-99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rate_limiting() -> None:
    """POST /analyze should return 429 after exceeding rate limit."""
    from main import _rate_limit_store
    import time

    user_id = "rate-limit-test-user"
    now = time.time()
    _rate_limit_store[user_id] = [now] * 10  # Fill up the limit

    with patch("main.magic.from_buffer", return_value="application/pdf"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("test.pdf", io.BytesIO(b"pdf"), "application/pdf")},
                headers={"x-user-id": user_id},
            )

    assert response.status_code == 429
