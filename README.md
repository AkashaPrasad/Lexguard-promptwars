# LexGuard — AI Contract Risk Analyzer

> **Hackathon submission: Promptwars 2024**  
> Multi-agent Gemini AI pipeline for automated contract risk analysis

---

## Problem Statement

Individuals and small businesses sign contracts without legal counsel. A single unfavorable clause — a worldwide non-compete, a perpetual IP assignment, an automatic renewal trap — can cost tens of thousands in legal fees or lock someone into an exploitative agreement for years. Legal review costs $300–$800/hour and is inaccessible to most.

**LexGuard** makes contract risk analysis instant, accessible, and free using Google's Gemini AI.

---

## Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | https://lexguard-frontend-914779957093.asia-south1.run.app |
| **Backend API** | https://lexguard-backend-914779957093.asia-south1.run.app |
| **API Docs** | https://lexguard-backend-914779957093.asia-south1.run.app/docs |
| **Health Check** | https://lexguard-backend-914779957093.asia-south1.run.app/health |
| **Instant Demo** | https://lexguard-backend-914779957093.asia-south1.run.app/demo |

### Quick Test (no file upload needed)
```bash
# Instant demo analysis
curl https://lexguard-backend-914779957093.asia-south1.run.app/demo | python3 -m json.tool

# Health check with GCP services status
curl https://lexguard-backend-914779957093.asia-south1.run.app/health

# Analyze a contract (POST with file)
curl -X POST https://lexguard-backend-914779957093.asia-south1.run.app/analyze \
  -F "file=@your_contract.pdf"
```

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LexGuard System                              │
│                                                                       │
│  ┌─────────────┐         ┌──────────────────────────────────────┐   │
│  │   React 18  │  HTTPS  │          FastAPI Backend               │   │
│  │  TypeScript │────────▶│                                        │   │
│  │  Tailwind   │         │  ┌──────────┐    ┌────────────────┐   │   │
│  │  Vite       │         │  │  Clause  │    │   Risk Agent   │   │   │
│  └─────────────┘         │  │  Agent   │───▶│  (2-pass adv.) │   │   │
│         │                │  └──────────┘    └────────────────┘   │   │
│         │                │       │                  │              │   │
│         ▼                │       ▼                  ▼              │   │
│  ┌─────────────┐         │  ┌──────────┐    ┌────────────────┐   │   │
│  │  Cloud Run  │         │  │  Gemini  │    │  Gemini Flash  │   │   │
│  │  (Frontend) │         │  │  Flash   │    │  (adversarial) │   │   │
│  └─────────────┘         │  └──────────┘    └────────────────┘   │   │
│                           └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Stack:**
- **Backend:** Python 3.11, FastAPI, Pydantic v2, PyMuPDF, python-docx, ReportLab
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, Vitest
- **AI:** Google Gemini 2.5 Flash (multi-agent pipeline)
- **Infrastructure:** GCP Cloud Run, Artifact Registry, Cloud Build, Cloud Logging

---

## AI / ML Approach: Multi-Agent Pipeline

LexGuard implements a **5-stage multi-agent pipeline** powered entirely by Gemini 2.5 Flash:

### Agent 1 — Document Parser
Extracts raw text from PDF, DOCX, DOC, PNG, and JPG contracts using PyMuPDF (PDFs), python-docx (Word documents), and OCR fallback (images).

### Agent 2 — Clause Extractor (ClauseAgent)
Uses the **CUAD benchmark taxonomy** (41 clause types, from academic research on contract understanding) to identify and extract all relevant clauses from the contract text via a structured Gemini prompt. Returns each clause with type, verbatim text, and confidence score.

```
CUAD Clause Types: Non-Compete, IP Ownership Assignment, Governing Law,
Confidentiality, Termination for Convenience, Limitation of Liability,
Indemnification, Liquidated Damages, ... (41 total)
```

### Agent 3 — Pass 1 Risk Scorer (RiskAgent — Flash)
For each extracted clause, Gemini scores:
- **risk_score** (1–10)
- **risk_category** (Financial, Privacy, IP/Ownership, Employment, Operational, Compliance, Termination)
- **explanation** (plain-English risk description)
- **negotiation_tip** (specific, actionable negotiation advice)

### Agent 4 — Pass 2 Adversarial Lawyer (RiskAgent — Flash)
A second Gemini call with an adversarial prompt ("you are an adversarial lawyer") performs:
- **adversarial_analysis** — how the counterparty could exploit the clause
- **worst_case_scenario** — worst realistic outcome if enforced as written

### Agent 5 — Metadata Extractor
Extracts contract-level metadata: type, parties, effective date, governing law, duration.

**Parallel execution:** All clause scoring tasks run concurrently via `asyncio.gather()`, minimizing total latency.

**Weighted risk scoring:** Overall score (0–100) uses severity-weighted averaging:
- CRITICAL clauses: weight 3.0
- HIGH clauses: weight 2.0
- MEDIUM clauses: weight 1.0
- LOW clauses: weight 0.5

---

## API Documentation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health + GCP services status |
| `GET` | `/demo` | Instant demo analysis (no upload required) |
| `POST` | `/analyze` | Analyze a contract file |
| `GET` | `/analysis/{id}` | Retrieve stored analysis |
| `GET` | `/report/{id}` | Download PDF risk report |
| `GET` | `/docs` | Swagger UI |

### POST /analyze

**Request:** `multipart/form-data`
- `file`: Contract file (PDF, DOCX, DOC, PNG, JPG; max 10MB)
- `x-user-id` header: Optional user ID for rate limiting (10 req/hour)

**Response:** `AnalysisResult`
```json
{
  "analysis_id": "uuid-string",
  "filename": "contract.pdf",
  "overall_risk_score": 78,
  "overall_severity": "CRITICAL",
  "summary": "Overall risk score: 78/100. Top risks: Non-Compete (CRITICAL); IP Ownership (CRITICAL).",
  "clauses": [
    {
      "clause_type": "Non-Compete",
      "extracted_text": "Party B shall not compete worldwide for 5 years...",
      "confidence": 0.97,
      "risk_score": 9,
      "severity": "CRITICAL",
      "risk_category": "Employment",
      "explanation": "5-year worldwide non-compete is extremely broad...",
      "negotiation_tip": "Push for 12-month restriction limited to direct competitors...",
      "adversarial_analysis": "Company can seek injunction immediately upon departure...",
      "worst_case_scenario": "You lose new job while litigation drags on 18 months..."
    }
  ],
  "metadata": {
    "contract_type": "Employment Agreement",
    "parties": ["Acme Corp", "John Doe"],
    "effective_date": "2024-01-15",
    "governing_law": "Delaware",
    "contract_duration": "At-will"
  },
  "created_at": "2024-01-15T10:00:00+00:00"
}
```

### GET /health
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:00:00.000Z",
  "google_cloud_project": "poetic-primer-496606-g4",
  "services": {
    "gemini": "configured",
    "gcs": "configured",
    "firebase": "configured",
    "model": "gemini-2.5-flash"
  }
}
```

---

## GCP Services Used

| Service | Purpose |
|---------|---------|
| **Gemini 2.5 Flash** (`generativelanguage.googleapis.com`) | Multi-agent AI pipeline: clause extraction, risk scoring, adversarial analysis, metadata extraction |
| **Cloud Run** | Serverless deployment for both frontend and backend containers |
| **Artifact Registry** | Docker image storage (`asia-south1-docker.pkg.dev`) |
| **Cloud Build** | CI/CD pipeline (`cloudbuild.yaml`) |
| **Cloud Logging** | Structured application logs (startup, analysis events, errors) |
| **Cloud Storage (GCS)** | Contract file storage (`lexguard-documents` bucket) |
| **Firebase** | Authentication infrastructure (optional auth on `/analyze`) |

---

## Evaluation Criteria Mapping

| Criterion | Implementation |
|-----------|---------------|
| **AI Integration** | 5-agent Gemini 2.5 Flash pipeline; parallel scoring via `asyncio.gather()`; SHA-256 response caching; 3-attempt retry with exponential backoff |
| **Technical Depth** | CUAD 41-clause taxonomy (academic benchmark); two-pass adversarial reasoning; PyMuPDF + python-docx parsing; weighted severity scoring algorithm |
| **GCP Integration** | Cloud Run, Artifact Registry, Cloud Build, Cloud Logging, GCS, Firebase Auth, Gemini API |
| **Code Quality** | Pydantic v2 strict typing; pytest-asyncio (28 tests); Vitest (11 tests); Ruff linting; fully typed Python |
| **UX / Accessibility** | WCAG 2.1 AA: ARIA labels, color+icon severity indicators, keyboard navigation, React.memo, Suspense lazy loading |
| **Problem-Solution Fit** | Real pain point: inaccessible legal review ($300-800/hr); instant analysis; actionable output; PDF report download |
| **Demo Readiness** | `/demo` endpoint for instant judge testing (no upload); live deployment; Swagger UI at `/docs` |

---

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Gemini API key from https://aistudio.google.com/app/apikey

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set your API key
cp .env.example .env   # or create .env manually:
echo "GEMINI_API_KEY=your_key_here" > .env
echo "GEMINI_MODEL=gemini-2.5-flash" >> .env

uvicorn main:app --reload --port 8000
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
# App available at http://localhost:5173
```

### Run Tests
```bash
# Backend (28 tests)
cd backend && python3 -m pytest tests/ -v

# Frontend (11 tests)
cd frontend && npm run test
```

---

## Docker & Deployment

### Run Locally with Docker Compose
```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:8080
```

### Deploy to GCP Cloud Run
```bash
# Authenticate
gcloud auth configure-docker asia-south1-docker.pkg.dev

# Build backend (must use linux/amd64 for Cloud Run)
docker build --platform linux/amd64 \
  -t asia-south1-docker.pkg.dev/poetic-primer-496606-g4/lexguard/backend:v2 \
  ./backend
docker push asia-south1-docker.pkg.dev/poetic-primer-496606-g4/lexguard/backend:v2

# Deploy
gcloud run deploy lexguard-backend \
  --image asia-south1-docker.pkg.dev/poetic-primer-496606-g4/lexguard/backend:v2 \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=your_key,GEMINI_MODEL=gemini-2.5-flash"
```

---

## Repository Structure

```
Promptwars/
├── backend/
│   ├── agents/
│   │   ├── clause_agent.py      # CUAD clause extraction (Agent 2)
│   │   └── risk_agent.py        # Two-pass risk scoring (Agents 3 & 4)
│   ├── data/
│   │   ├── cuad_clauses.json    # 41 CUAD clause definitions
│   │   └── sample_nda.txt       # Sample NDA for testing
│   ├── models/
│   │   └── contract.py          # Pydantic v2 models
│   ├── tests/
│   │   ├── test_api.py          # FastAPI endpoint tests (11 tests)
│   │   ├── test_clause_agent.py # Clause extraction tests (8 tests)
│   │   └── test_risk_agent.py   # Risk scoring tests (9 tests)
│   ├── utils/
│   │   ├── document_parser.py   # Multi-format document parsing
│   │   ├── gemini_client.py     # Gemini API client (retry, cache, logging)
│   │   ├── logger.py            # Centralized logging
│   │   └── report_generator.py  # PDF report generation
│   ├── config.py                # Environment configuration
│   ├── main.py                  # FastAPI application
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts        # API client
│   │   ├── components/          # React components (ClauseCard, RiskDashboard, etc.)
│   │   ├── hooks/               # Custom React hooks
│   │   ├── types.ts             # TypeScript types
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
├── cloudbuild.yaml              # Cloud Build CI/CD
├── docker-compose.yml
└── README.md
```

---

## Test Coverage

**Backend — 28 tests (pytest + pytest-asyncio):**
- `test_api.py` — health check with services dict, demo endpoint, analyze success/failure, rate limiting, 404 handling
- `test_clause_agent.py` — extraction, CUAD loading (41 clauses), edge cases, field validation
- `test_risk_agent.py` — severity mapping, overall score computation, two-pass scoring, fallback behavior

**Frontend — 11 tests (Vitest + @testing-library/react):**
- Component rendering, accessibility ARIA checks, API integration, error state handling

---

## GitHub Repository

https://github.com/AkashaPrasad/Lexguard-promptwars

---

*Built for Promptwars 2024 — solo project*
