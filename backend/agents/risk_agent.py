"""Two-pass adversarial risk scoring agent."""
import asyncio
import json
import logging
from typing import List, Tuple

from models.contract import (
    ContractMetadata,
    ExtractedClause,
    RiskCategory,
    RiskSeverity,
    ScoredClause,
)
from utils.gemini_client import call_gemini
from config import (
    GEMINI_MODEL_FLASH,
    GEMINI_MODEL_PRO,
    RISK_CRITICAL_MIN,
    RISK_HIGH_MIN,
    RISK_MEDIUM_MIN,
)

logger = logging.getLogger(__name__)


def _build_pass1_prompt(clause: ExtractedClause) -> str:
    return f"""You are a contract risk analyst. Analyze this clause and return a JSON object.

Clause Type: {clause.clause_type}
Clause Text: {clause.extracted_text[:600]}

Return ONLY this exact JSON structure (no markdown, no explanation):
{{
  "risk_score": <integer 1-10, where 10 = most dangerous>,
  "risk_category": "<one of: Financial, Privacy, IP/Ownership, Employment, Operational, Compliance, Termination>",
  "explanation": "<plain English explanation of why this clause is risky, referencing specific language>",
  "negotiation_tip": "<specific, actionable negotiation recommendation for reducing this risk>"
}}"""


def _build_pass2_prompt(clause: ExtractedClause) -> str:
    return f"""You are an adversarial lawyer protecting a client from unfavorable contract terms.

Clause Type: {clause.clause_type}
Clause Text: {clause.extracted_text[:600]}

Return ONLY this exact JSON structure (no markdown, no explanation):
{{
  "adversarial_analysis": "<how the counterparty could exploit this clause against your client — be specific>",
  "worst_case": "<the worst realistic legal or business outcome if enforced as written>"
}}"""


def _build_metadata_prompt(contract_text: str) -> str:
    return f"""Extract metadata from this contract. Return ONLY this JSON structure:
{{
  "contract_type": "<NDA/Employment/SaaS/Vendor/Partnership/Service/Other>",
  "parties": ["<party 1 full name>", "<party 2 full name>"],
  "effective_date": "<ISO date string or null>",
  "governing_law": "<jurisdiction/state/country or null>",
  "contract_duration": "<duration description or null>"
}}

Contract (first 3000 chars):
{contract_text[:3000]}"""


class RiskAgent:
    """Scores contract clause risk using two-pass adversarial reasoning."""

    def _get_severity(self, score: int) -> RiskSeverity:
        """Map numeric risk score to severity level."""
        if score >= RISK_CRITICAL_MIN:
            return RiskSeverity.CRITICAL
        if score >= RISK_HIGH_MIN:
            return RiskSeverity.HIGH
        if score >= RISK_MEDIUM_MIN:
            return RiskSeverity.MEDIUM
        return RiskSeverity.LOW

    def compute_overall_score(self, clauses: List[ScoredClause]) -> int:
        """Compute overall contract risk score 0-100 using weighted severity."""
        if not clauses:
            return 0
        weights = {
            RiskSeverity.CRITICAL: 3.0,
            RiskSeverity.HIGH: 2.0,
            RiskSeverity.MEDIUM: 1.0,
            RiskSeverity.LOW: 0.5,
        }
        total_weight = sum(weights[c.severity] for c in clauses)
        weighted_sum = sum(c.risk_score * weights[c.severity] for c in clauses)
        if total_weight == 0:
            return 0
        raw = (weighted_sum / (total_weight * 10)) * 100
        return min(100, max(0, int(raw)))

    async def score_single(self, clause: ExtractedClause) -> ScoredClause:
        """Score a single clause using two-pass adversarial reasoning.

        Pass 1 (Flash): risk score, category, explanation, negotiation tip.
        Pass 2 (Flash): adversarial leverage and worst-case analysis.

        Passes run sequentially to avoid bursting 2N simultaneous calls
        when scoring N clauses concurrently — semaphore in gemini_client
        handles overall concurrency.

        Raises:
            RuntimeError: If Gemini API calls fail after all retries.
        """
        raw1 = await call_gemini(_build_pass1_prompt(clause), model_name=GEMINI_MODEL_FLASH)
        raw2 = await call_gemini(_build_pass2_prompt(clause), model_name=GEMINI_MODEL_PRO)

        pass1 = json.loads(raw1)
        pass2 = json.loads(raw2)

        risk_score = max(1, min(10, int(pass1.get("risk_score", 5))))

        try:
            risk_category = RiskCategory(pass1.get("risk_category", "Operational"))
        except ValueError:
            risk_category = RiskCategory.OPERATIONAL

        return ScoredClause(
            clause_type=clause.clause_type,
            extracted_text=clause.extracted_text,
            confidence=clause.confidence,
            risk_score=risk_score,
            severity=self._get_severity(risk_score),
            risk_category=risk_category,
            explanation=str(pass1.get("explanation", "")),
            negotiation_tip=str(pass1.get("negotiation_tip", "")),
            adversarial_analysis=str(pass2.get("adversarial_analysis", "")),
            worst_case_scenario=str(pass2.get("worst_case", "")),
        )

    async def _score_with_fallback(self, clause: ExtractedClause) -> ScoredClause:
        """Score a clause with one retry before returning MEDIUM fallback."""
        for attempt in range(2):
            try:
                return await self.score_single(clause)
            except Exception as e:
                if attempt == 0:
                    logger.warning(
                        "Clause scoring attempt 1 failed for '%s', retrying in 3s: %s",
                        clause.clause_type, e,
                    )
                    await asyncio.sleep(3)
                else:
                    logger.error(
                        "Clause scoring failed for '%s' after 2 attempts: %s",
                        clause.clause_type, e, exc_info=True,
                    )
        return ScoredClause(
                clause_type=clause.clause_type,
                extracted_text=clause.extracted_text,
                confidence=clause.confidence,
                risk_score=5,
                severity=RiskSeverity.MEDIUM,
                risk_category=RiskCategory.OPERATIONAL,
                explanation="Analysis unavailable due to processing error.",
                negotiation_tip="Review with qualified legal counsel.",
                adversarial_analysis="",
                worst_case_scenario="",
            )

    async def score_all(
        self, clauses: List[ExtractedClause], contract_text: str
    ) -> Tuple[List[ScoredClause], ContractMetadata]:
        """Score all clauses and extract metadata.

        Clause scoring runs in parallel; metadata extraction runs sequentially after.

        Args:
            clauses: Extracted clauses to score.
            contract_text: Full contract text for metadata extraction.

        Returns:
            Tuple of (scored clauses, contract metadata).
        """
        scoring_tasks = [self._score_with_fallback(c) for c in clauses]
        scored_clauses: List[ScoredClause] = list(await asyncio.gather(*scoring_tasks))

        try:
            raw_meta = await call_gemini(
                _build_metadata_prompt(contract_text), model_name=GEMINI_MODEL_FLASH
            )
            metadata_dict = json.loads(raw_meta)
        except Exception as e:
            logger.error("Metadata extraction failed: %s", e)
            metadata_dict = {}

        metadata = ContractMetadata(
            contract_type=metadata_dict.get("contract_type", "Unknown"),
            parties=metadata_dict.get("parties", []),
            effective_date=metadata_dict.get("effective_date"),
            governing_law=metadata_dict.get("governing_law"),
            contract_duration=metadata_dict.get("contract_duration"),
        )
        return scored_clauses, metadata
