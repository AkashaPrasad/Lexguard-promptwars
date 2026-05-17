"""LexGuard API - Contract Risk Analysis Service."""
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import magic
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agents.clause_agent import ClauseAgent
from agents.risk_agent import RiskAgent
from config import (
    ALLOWED_MIME_TYPES,
    APP_VERSION,
    CORS_ORIGINS,
    FIREBASE_PROJECT_ID,
    GEMINI_MODEL_FLASH,
    GCS_BUCKET_NAME,
    GOOGLE_CLOUD_PROJECT,
    MAX_FILE_SIZE_BYTES,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)
from models.contract import (
    AnalysisResult,
    ContractMetadata,
    HealthResponse,
    RiskCategory,
    RiskSeverity,
    ScoredClause,
)
from utils.document_parser import parse_document
from utils.gemini_client import GEMINI_AVAILABLE
from utils.report_generator import generate_pdf_report

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LexGuard API",
    version=APP_VERSION,
    description="AI-powered contract risk analysis using multi-agent Gemini pipeline",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_rate_limit_store: dict = {}
_analysis_store: dict = {}

clause_agent = ClauseAgent()
risk_agent = RiskAgent()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.on_event("startup")
async def startup_event() -> None:
    """Log service startup and validate GCP service connectivity."""
    logging.basicConfig(level=logging.INFO)
    logger.info("LexGuard API v%s starting up", APP_VERSION)
    logger.info("Gemini available: %s, model: %s", GEMINI_AVAILABLE, GEMINI_MODEL_FLASH)
    logger.info("GCS bucket: %s", GCS_BUCKET_NAME or "not configured")
    logger.info("Firebase project: %s", FIREBASE_PROJECT_ID or "not configured")
    logger.info("GCP project: %s", GOOGLE_CLOUD_PROJECT or "not configured")
    logger.info("CUAD clauses loaded: %d", len(clause_agent.cuad_clauses))


def check_rate_limit(user_id: str) -> None:
    """Enforce rate limit of RATE_LIMIT_REQUESTS per hour per user."""
    now = datetime.now(timezone.utc).timestamp()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    _rate_limit_store[user_id] = [
        t for t in _rate_limit_store[user_id] if t > window_start
    ]

    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per hour.",
        )

    _rate_limit_store[user_id].append(now)


def _get_overall_severity(score: int) -> RiskSeverity:
    if score >= 70:
        return RiskSeverity.CRITICAL
    if score >= 50:
        return RiskSeverity.HIGH
    if score >= 30:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _build_summary(clauses: list, overall_score: int) -> str:
    critical = [c for c in clauses if c.severity.value in ("CRITICAL", "HIGH")]
    critical.sort(key=lambda x: x.risk_score, reverse=True)
    top = critical[:3]
    if not top:
        return f"Contract has an overall risk score of {overall_score}/100 with no critical issues found."
    items = "; ".join(f"{c.clause_type} ({c.severity.value})" for c in top)
    return f"Overall risk score: {overall_score}/100. Top risks: {items}."


def _make_demo_result() -> AnalysisResult:
    """Return a rich hardcoded demo result showcasing full analysis capabilities."""
    clauses = [
        ScoredClause(
            clause_type="Non-Compete",
            extracted_text=(
                "Employee agrees not to engage in any business activities competitive with "
                "Company's business anywhere in the world for a period of five (5) years "
                "following termination, regardless of the reason for termination."
            ),
            confidence=0.97,
            risk_score=9,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.EMPLOYMENT,
            explanation=(
                "A 5-year worldwide non-compete is extremely broad. Courts in many jurisdictions "
                "deem such clauses unenforceable, but defending against enforcement costs money "
                "and time. The geographic scope ('anywhere in the world') and duration (5 years) "
                "are both well beyond industry norms of 1-2 years within a defined region."
            ),
            negotiation_tip=(
                "Push for a 12-month restriction limited to direct competitors within your "
                "primary work region. Insist on a defined list of specific competitor companies "
                "rather than a broad industry exclusion."
            ),
            adversarial_analysis=(
                "The company can use this clause to seek an injunction immediately upon your "
                "departure, freezing your ability to work in your field while litigation proceeds. "
                "Even if the clause is ultimately unenforceable, the legal costs and career "
                "disruption are a powerful deterrent."
            ),
            worst_case_scenario=(
                "You leave the company and join a startup in the same sector. The company obtains "
                "a temporary restraining order, you lose the new job while the case drags on for "
                "18 months, and you pay $50,000+ in legal fees even if you ultimately win."
            ),
        ),
        ScoredClause(
            clause_type="IP Ownership Assignment",
            extracted_text=(
                "Employee hereby irrevocably assigns to Company all right, title, and interest "
                "in any and all inventions, discoveries, improvements, and works of authorship "
                "conceived, developed, or reduced to practice during the term of employment or "
                "within two (2) years thereafter, whether or not related to Employee's duties."
            ),
            confidence=0.95,
            risk_score=8,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.IP_OWNERSHIP,
            explanation=(
                "This clause captures ALL intellectual property created within 2 years after "
                "employment ends, even work completely unrelated to the job. Side projects, "
                "personal apps, and independent inventions created on your own time with "
                "personal resources could be claimed by the company."
            ),
            negotiation_tip=(
                "Negotiate a carve-out for personal projects developed entirely on personal time "
                "with personal resources and unrelated to company business. Request a written "
                "schedule of pre-existing IP to exclude from the assignment."
            ),
            adversarial_analysis=(
                "If you build a successful startup after leaving, the company can claim ownership "
                "of all the technology if it was conceived during the 2-year window. "
                "The 'related to duties' language is absent — any IP can be claimed."
            ),
            worst_case_scenario=(
                "You launch a successful SaaS product 18 months after leaving. The company sues "
                "for ownership of all IP, demands transfer of the product, and seeks damages "
                "for profits earned during the dispute period."
            ),
        ),
        ScoredClause(
            clause_type="Confidentiality",
            extracted_text=(
                "Employee agrees to maintain in strict confidence all Confidential Information "
                "of Company in perpetuity. Confidential Information means any information, "
                "technical data, trade secrets or know-how, including but not limited to "
                "research, product plans, products, services, customers, markets, software, "
                "developments, inventions, processes, formulas, and business plans."
            ),
            confidence=0.93,
            risk_score=7,
            severity=RiskSeverity.HIGH,
            risk_category=RiskCategory.PRIVACY,
            explanation=(
                "The perpetual duration ('in perpetuity') is unusually aggressive. The definition "
                "of Confidential Information is extremely broad and could cover general industry "
                "knowledge. This could prevent you from discussing your experience in job interviews "
                "or using skills developed during employment."
            ),
            negotiation_tip=(
                "Negotiate a 3-5 year confidentiality period for general confidential information "
                "(trade secrets can remain perpetual). Request a narrow, specific definition of "
                "what constitutes Confidential Information."
            ),
            adversarial_analysis=(
                "The broad definition means future employers could be contacted and accused of "
                "receiving stolen trade secrets if you discuss your work experience. "
                "This creates a chilling effect on your employability."
            ),
            worst_case_scenario=(
                "You mention a high-level technical approach in a job interview. The company "
                "sends a cease-and-desist to your prospective employer, who withdraws the offer "
                "to avoid litigation exposure."
            ),
        ),
        ScoredClause(
            clause_type="Termination for Convenience",
            extracted_text=(
                "Company may terminate this Agreement at any time, with or without cause, "
                "upon fourteen (14) days written notice. Employee shall have no right to any "
                "compensation or benefits beyond the notice period."
            ),
            confidence=0.91,
            risk_score=6,
            severity=RiskSeverity.HIGH,
            risk_category=RiskCategory.EMPLOYMENT,
            explanation=(
                "14 days notice is extremely short for termination without cause. Industry "
                "standard for experienced professionals is 1-3 months. After any severance, "
                "all benefits and compensation stop immediately with no additional obligations "
                "on the company."
            ),
            negotiation_tip=(
                "Negotiate for 30-90 days notice or equivalent severance pay. Include continuation "
                "of health benefits through the notice period. Consider requesting a severance "
                "formula based on years of service (e.g., 2 weeks per year)."
            ),
            adversarial_analysis=(
                "The company can terminate on 14 days notice at any time — including immediately "
                "before a stock vesting cliff — leaving you with minimal financial protection "
                "during your job search."
            ),
            worst_case_scenario=(
                "You are terminated 5 days before a major stock vesting event with only 14 days "
                "notice and two weeks' pay, losing hundreds of thousands in unvested equity."
            ),
        ),
        ScoredClause(
            clause_type="Governing Law",
            extracted_text=(
                "This Agreement shall be governed by and construed in accordance with the laws "
                "of the State of Delaware, without regard to its conflict of law provisions. "
                "Any disputes shall be resolved exclusively in the courts of New Castle County, Delaware."
            ),
            confidence=0.98,
            risk_score=4,
            severity=RiskSeverity.MEDIUM,
            risk_category=RiskCategory.COMPLIANCE,
            explanation=(
                "Delaware governing law is standard for corporate agreements but may be "
                "inconvenient if you are based elsewhere. Exclusive jurisdiction in Delaware "
                "courts means you would need to litigate in Delaware even if you live in "
                "another state or country."
            ),
            negotiation_tip=(
                "If you are not based in Delaware, request that disputes be resolved in your "
                "home state or via remote arbitration. Alternatively, negotiate for venue to "
                "follow the defendant's location."
            ),
            adversarial_analysis=(
                "If you need to enforce your rights, you must file in Delaware courts, "
                "incurring travel costs and potentially needing to hire Delaware-licensed counsel "
                "in addition to your local attorney."
            ),
            worst_case_scenario=(
                "You file a wage claim from California. You must retain Delaware counsel and "
                "travel repeatedly to Wilmington, making small claims economically unviable."
            ),
        ),
    ]

    overall_score = risk_agent.compute_overall_score(clauses)
    return AnalysisResult(
        analysis_id="demo-" + str(uuid.uuid4())[:8],
        filename="sample_nda_demo.pdf",
        overall_risk_score=overall_score,
        overall_severity=_get_overall_severity(overall_score),
        clauses=clauses,
        metadata=ContractMetadata(
            contract_type="Employment Agreement",
            parties=["Acme Corporation", "John Doe"],
            effective_date="2024-01-15",
            governing_law="Delaware",
            contract_duration="At-will (no fixed term)",
        ),
        summary=_build_summary(clauses, overall_score),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status including GCP service availability."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        google_cloud_project=GOOGLE_CLOUD_PROJECT or "not-set",
        services={
            "gemini": "configured" if GEMINI_AVAILABLE else "not_configured",
            "gcs": "configured" if GCS_BUCKET_NAME else "not_configured",
            "firebase": "configured" if FIREBASE_PROJECT_ID else "not_configured",
            "model": GEMINI_MODEL_FLASH,
        },
    )


@app.get("/demo", response_model=AnalysisResult)
async def demo_analysis() -> AnalysisResult:
    """Instant demo analysis — no file upload required.

    Returns a pre-computed analysis of a sample employment contract
    to demonstrate the full LexGuard multi-agent pipeline output.
    """
    return _make_demo_result()


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_contract(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default="anonymous"),
) -> AnalysisResult:
    """Analyze a contract document for risks using the multi-agent pipeline.

    Args:
        file: The uploaded contract file (PDF, DOCX, DOC, PNG, JPG).
        x_user_id: Optional user identifier for rate limiting.

    Returns:
        AnalysisResult with scored clauses and overall risk assessment.
    """
    user_id = x_user_id or "anonymous"
    check_rate_limit(user_id)

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit.",
        )

    detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type '{detected_mime}'. Allowed: PDF, DOCX, DOC, PNG, JPG.",
        )

    contract_text = await parse_document(
        file_bytes, detected_mime, file.filename or "contract"
    )

    if not contract_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the document.",
        )

    logger.info("Analyzing contract: %s (%d chars)", file.filename, len(contract_text))

    extracted = await clause_agent.extract(contract_text)
    logger.info("Clause extraction complete: %d clauses found", len(extracted))

    scored_clauses, metadata = await risk_agent.score_all(extracted, contract_text)
    logger.info("Risk scoring complete: %d clauses scored", len(scored_clauses))

    overall_score = risk_agent.compute_overall_score(scored_clauses)
    overall_severity = _get_overall_severity(overall_score)
    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    result = AnalysisResult(
        analysis_id=analysis_id,
        filename=file.filename or "contract",
        overall_risk_score=overall_score,
        overall_severity=overall_severity,
        clauses=scored_clauses,
        metadata=metadata,
        created_at=created_at,
        summary=_build_summary(scored_clauses, overall_score),
    )

    _analysis_store[analysis_id] = result
    logger.info("Analysis complete: id=%s score=%d severity=%s", analysis_id, overall_score, overall_severity.value)
    return result


@app.get("/report/{analysis_id}")
async def get_pdf_report(analysis_id: str) -> StreamingResponse:
    """Generate and return a PDF report for a previously completed analysis."""
    result = _analysis_store.get(analysis_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Re-upload contract to generate report.",
        )

    pdf_bytes = generate_pdf_report(result)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="lexguard-report-{analysis_id[:8]}.pdf"'
        },
    )


@app.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str) -> AnalysisResult:
    """Retrieve a previously stored analysis by ID."""
    result = _analysis_store.get(analysis_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return result
