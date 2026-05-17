"""Firestore client for storing and retrieving analysis results."""
import uuid
from typing import Optional

from config import FIREBASE_PROJECT_ID


def store_analysis(analysis_dict: dict) -> str:
    """Store analysis result in Firestore and return document ID.

    Args:
        analysis_dict: Serialized AnalysisResult as a dictionary.

    Returns:
        Firestore document ID (or a UUID fallback on failure).
    """
    try:
        from google.cloud import firestore

        db = firestore.Client(project=FIREBASE_PROJECT_ID)
        doc_id = str(uuid.uuid4())
        db.collection("analyses").document(doc_id).set(analysis_dict)
        return doc_id
    except Exception:
        return str(uuid.uuid4())


def get_analysis(doc_id: str) -> Optional[dict]:
    """Retrieve analysis from Firestore by document ID.

    Args:
        doc_id: The Firestore document ID to fetch.

    Returns:
        Analysis dictionary if found, None otherwise.
    """
    try:
        from google.cloud import firestore

        db = firestore.Client(project=FIREBASE_PROJECT_ID)
        doc = db.collection("analyses").document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None
