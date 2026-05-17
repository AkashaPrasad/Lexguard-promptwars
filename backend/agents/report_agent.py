"""Agent for generating natural language report summaries."""
from typing import List

from models.contract import AnalysisResult, ScoredClause, RiskSeverity
from utils.gemini_client import call_gemini
from config import GEMINI_MODEL_FLASH


def _build_summary_prompt(result: AnalysisResult) -> str:
    """Build the report summary prompt."""
    critical_clauses = [
        c for c in result.clauses if c.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
    ]
    clause_summaries = "\n".join(
        f"- {c.clause_type} (score {c.risk_score}/10): {c.explanation[:100]}"
        for c in critical_clauses[:5]
    )
    return f"""Generate an executive summary for a contract risk report. Return JSON:
{{
  "executive_summary": "<2-3 sentence plain English summary>",
  "key_recommendations": ["<rec 1>", "<rec 2>", "<rec 3>"],
  "negotiation_priority": "<which clause to negotiate first and why>"
}}

Contract: {result.filename}
Overall Risk Score: {result.overall_risk_score}/100
Severity: {result.overall_severity.value}
Top Issues:
{clause_summaries}"""


class ReportAgent:
    """Generates natural language summaries and recommendations."""

    async def generate_summary(self, result: AnalysisResult) -> dict:
        """Generate an AI-powered executive summary for the analysis.

        Args:
            result: The completed AnalysisResult to summarize.

        Returns:
            Dictionary with executive_summary, key_recommendations,
            and negotiation_priority fields.
        """
        prompt = _build_summary_prompt(result)
        response = await call_gemini(prompt, model_name=GEMINI_MODEL_FLASH)

        if not isinstance(response, dict):
            return {
                "executive_summary": result.summary,
                "key_recommendations": [],
                "negotiation_priority": "",
            }
        return response

    def build_plain_summary(self, result: AnalysisResult) -> str:
        """Build a simple text summary without AI call.

        Args:
            result: The completed AnalysisResult.

        Returns:
            Plain text summary string.
        """
        critical = [
            c for c in result.clauses
            if c.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
        ]
        critical.sort(key=lambda x: x.risk_score, reverse=True)
        top = critical[:3]

        if not top:
            return (
                f"Contract has an overall risk score of {result.overall_risk_score}/100 "
                f"with no critical issues found."
            )

        items = "; ".join(
            f"{c.clause_type} ({c.severity.value})" for c in top
        )
        return (
            f"Overall risk score: {result.overall_risk_score}/100. "
            f"Top risks: {items}."
        )
