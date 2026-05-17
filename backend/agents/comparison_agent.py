"""Agent for comparing two contracts and identifying differences in risk."""
from typing import Dict, List, Tuple

from models.contract import AnalysisResult, ScoredClause, RiskSeverity
from utils.gemini_client import call_gemini
from config import GEMINI_MODEL_FLASH


def _find_clause_by_type(
    clauses: List[ScoredClause], clause_type: str
) -> ScoredClause | None:
    """Find a clause by its type in a list."""
    for clause in clauses:
        if clause.clause_type == clause_type:
            return clause
    return None


def _build_comparison_prompt(
    clause_type: str,
    text_a: str,
    text_b: str,
) -> str:
    """Build the clause comparison prompt."""
    return f"""Compare these two contract clauses of type '{clause_type}' and return JSON:
{{
  "risk_delta": <integer -10 to 10, positive means Contract B is riskier>,
  "key_differences": ["<difference 1>", "<difference 2>"],
  "recommendation": "<which version is better and why>"
}}

Contract A: {text_a[:400]}
Contract B: {text_b[:400]}"""


class ComparisonAgent:
    """Compares two AnalysisResult objects to identify risk differences."""

    async def compare(
        self, result_a: AnalysisResult, result_b: AnalysisResult
    ) -> Dict:
        """Compare two contract analyses and return differences.

        Args:
            result_a: First contract analysis result.
            result_b: Second contract analysis result.

        Returns:
            Dictionary with comparison results per clause type.
        """
        clause_types_a = {c.clause_type for c in result_a.clauses}
        clause_types_b = {c.clause_type for c in result_b.clauses}
        common_types = clause_types_a & clause_types_b

        comparisons = {}
        for clause_type in common_types:
            clause_a = _find_clause_by_type(result_a.clauses, clause_type)
            clause_b = _find_clause_by_type(result_b.clauses, clause_type)
            if clause_a and clause_b:
                comparison = await call_gemini(
                    _build_comparison_prompt(
                        clause_type,
                        clause_a.extracted_text,
                        clause_b.extracted_text,
                    ),
                    model_name=GEMINI_MODEL_FLASH,
                )
                comparisons[clause_type] = comparison

        return {
            "contract_a": result_a.filename,
            "contract_b": result_b.filename,
            "score_delta": result_b.overall_risk_score - result_a.overall_risk_score,
            "clauses_only_in_a": list(clause_types_a - clause_types_b),
            "clauses_only_in_b": list(clause_types_b - clause_types_a),
            "clause_comparisons": comparisons,
        }
