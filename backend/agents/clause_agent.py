"""Agent for extracting contract clauses using the CUAD taxonomy."""
import json
import logging
from pathlib import Path
from typing import List

from models.contract import ExtractedClause
from utils.gemini_client import call_gemini
from config import GEMINI_MODEL_FLASH

logger = logging.getLogger(__name__)

_CUAD_DATA_PATH = Path(__file__).parent.parent / "data" / "cuad_clauses.json"


def get_cuad_clauses() -> list:
    """Load CUAD clause definitions, handling flat array or wrapped dict formats."""
    with open(_CUAD_DATA_PATH) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("clauses", [])
    return data


_CUAD_CLAUSES = get_cuad_clauses()


def _build_extraction_prompt(contract_text: str, clause_names: List[str]) -> str:
    clause_list = "\n".join(f"- {name}" for name in clause_names)
    return f"""You are a senior contract lawyer. Carefully read the contract and extract ALL relevant clauses.

Use ONLY these CUAD clause types (match as many as are present):
{clause_list}

Return a JSON array. Each item MUST have exactly these fields:
- "clause_type": the exact clause name from the list above
- "extracted_text": verbatim text from the contract (max 400 words per clause)
- "confidence": float 0.0–1.0 indicating confidence in the match

Be thorough — extract every clause type that appears in the contract.

CONTRACT TEXT:
{contract_text[:10000]}

Return ONLY a valid JSON array. No markdown, no explanations, just the array."""


def _parse_clause_item(item: dict) -> ExtractedClause | None:
    if not isinstance(item, dict):
        return None
    if "clause_type" not in item or "extracted_text" not in item:
        return None
    try:
        return ExtractedClause(
            clause_type=str(item["clause_type"]),
            extracted_text=str(item["extracted_text"]),
            confidence=float(item.get("confidence", 0.8)),
        )
    except Exception as e:
        logger.warning("Failed to parse clause item: %s", e)
        return None


class ClauseAgent:
    """Extracts contract clauses using the CUAD taxonomy."""

    def __init__(self) -> None:
        self.cuad_clauses = _CUAD_CLAUSES

    async def extract(self, contract_text: str) -> List[ExtractedClause]:
        """Extract clauses from contract text using Gemini.

        Args:
            contract_text: Raw text of the contract.

        Returns:
            List of ExtractedClause objects.

        Raises:
            RuntimeError: If Gemini API is unavailable or fails.
        """
        if not contract_text.strip():
            return []

        clause_names = [c["name"] for c in self.cuad_clauses]
        prompt = _build_extraction_prompt(contract_text, clause_names)

        raw = await call_gemini(prompt, model_name=GEMINI_MODEL_FLASH)
        result = json.loads(raw)

        if not isinstance(result, list):
            logger.warning("Clause extraction returned non-list type: %s", type(result))
            return []

        clauses = []
        for item in result:
            parsed = _parse_clause_item(item)
            if parsed is not None:
                clauses.append(parsed)

        logger.info("Extracted %d clauses from contract", len(clauses))
        return clauses
