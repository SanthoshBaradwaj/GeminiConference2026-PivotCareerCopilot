"""Firestore integration and function tools for Pivot Career Copilot.

Hardcodes the GCP project ID string to prevent Agent Platform
project number resolution errors after deployment.
"""

from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcode the GCP project ID as a string per project guidelines
PROJECT_ID = "qwiklabs-gcp-04-2479ded67a3b"

_db: Optional[firestore.Client] = None


def get_db() -> firestore.Client:
    """Returns an initialized Firestore Client for the hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def get_target_tiers(user_id: str = "default_user") -> Dict[str, Any]:
    """Retrieves target career tiers (Safe, Moderate, Ambitious) from Firestore.

    Args:
        user_id: The ID of the user whose target tiers to retrieve. Defaults to 'default_user'.

    Returns:
        A dictionary containing safe, moderate, and ambitious role recommendations,
        readiness percentages, identified gaps, and timelines in weeks.
    """
    db = get_db()
    doc = db.collection("target_tiers").document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return {
        "status": "not_found",
        "message": f"No target tiers found for user '{user_id}'.",
    }


def save_target_tiers(
    user_id: str,
    safe_role: str,
    safe_readiness: str,
    safe_gap: str,
    safe_timeline_weeks: int,
    moderate_role: str,
    moderate_readiness: str,
    moderate_gap: str,
    moderate_timeline_weeks: int,
    ambitious_role: str,
    ambitious_readiness: str,
    ambitious_gap: str,
    ambitious_timeline_weeks: int,
) -> str:
    """Saves or updates career targeting tiers in Firestore for a user.

    Args:
        user_id: The unique ID of the candidate.
        safe_role: Role name for the safe tier.
        safe_readiness: Readiness score/percentage (e.g. '85%').
        safe_gap: Specific gap or prep requirement.
        safe_timeline_weeks: Estimated preparation time in weeks.
        moderate_role: Role name for the moderate tier.
        moderate_readiness: Readiness score/percentage (e.g. '70%').
        moderate_gap: Specific gap or prep requirement.
        moderate_timeline_weeks: Estimated preparation time in weeks.
        ambitious_role: Role name for the ambitious tier.
        ambitious_readiness: Readiness score/percentage (e.g. '45%').
        ambitious_gap: Specific gap or prep requirement.
        ambitious_timeline_weeks: Estimated preparation time in weeks.

    Returns:
        Confirmation message indicating successful persistence.
    """
    db = get_db()
    data = {
        "user_id": user_id,
        "safe": {
            "role": safe_role,
            "readiness": safe_readiness,
            "gap": safe_gap,
            "timeline_weeks": safe_timeline_weeks,
        },
        "moderate": {
            "role": moderate_role,
            "readiness": moderate_readiness,
            "gap": moderate_gap,
            "timeline_weeks": moderate_timeline_weeks,
        },
        "ambitious": {
            "role": ambitious_role,
            "readiness": ambitious_readiness,
            "gap": ambitious_gap,
            "timeline_weeks": ambitious_timeline_weeks,
        },
    }
    db.collection("target_tiers").document(user_id).set(data)
    return f"Successfully saved target tiers for user '{user_id}' in Firestore."


def get_shortlist(user_id: str = "default_user") -> Dict[str, Any]:
    """Retrieves the shortlisted companies and roles from Firestore.

    Args:
        user_id: The ID of the user whose shortlist to retrieve. Defaults to 'default_user'.

    Returns:
        A dictionary containing the shortlisted companies, target roles, and source job posting IDs.
    """
    db = get_db()
    doc = db.collection("shortlist").document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return {
        "status": "not_found",
        "message": f"No shortlist found for user '{user_id}'.",
        "entries": [],
    }


def add_to_shortlist(
    user_id: str,
    company: str,
    role: str,
    source_posting_id: str = "",
) -> str:
    """Adds a new company and role to the candidate's shortlist in Firestore.

    Args:
        user_id: The unique ID of the candidate.
        company: The name of the target company.
        role: The specific job title or role.
        source_posting_id: Optional reference or job posting ID.

    Returns:
        Confirmation message of the addition.
    """
    db = get_db()
    doc_ref = db.collection("shortlist").document(user_id)
    doc = doc_ref.get()
    new_entry = {
        "company": company,
        "role": role,
        "source_posting_id": source_posting_id,
    }
    if doc.exists:
        entries = doc.to_dict().get("entries", [])
        entries.append(new_entry)
        doc_ref.update({"entries": entries})
    else:
        doc_ref.set({"user_id": user_id, "entries": [new_entry]})
    return f"Added {company} - {role} to shortlist for '{user_id}'."


def get_intake_profile(user_id: str = "default_user") -> Dict[str, Any]:
    """Retrieves verified skills and evidence citations from the candidate's intake profile in Firestore.

    Args:
        user_id: The ID of the user. Defaults to 'default_user'.

    Returns:
        A dictionary with the user's verified skills, source documents, and evidence snippets.
    """
    db = get_db()
    doc = db.collection("intake_profile").document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return {
        "status": "not_found",
        "message": f"No intake profile found for user '{user_id}'.",
        "fields": [],
    }


def add_intake_skill(
    user_id: str,
    skill_id: str,
    value: str,
    source: str,
    snippet: str,
) -> str:
    """Adds or updates a verified background claim or skill with evidence citation in Firestore.

    Args:
        user_id: The ID of the user.
        skill_id: Identifier for the skill or capability.
        value: Verified level, experience, or description.
        source: Source document or citation (e.g. 'resume.pdf', 'github:repo').
        snippet: Verifiable snippet or quote from the source.

    Returns:
        Confirmation message of the record saved.
    """
    db = get_db()
    doc_ref = db.collection("intake_profile").document(user_id)
    doc = doc_ref.get()
    field_entry = {
        "skill_id": skill_id,
        "value": value,
        "source": source,
        "snippet": snippet,
    }
    if doc.exists:
        fields = doc.to_dict().get("fields", [])
        # Update existing skill_id if present, else append
        fields = [f for f in fields if f.get("skill_id") != skill_id]
        fields.append(field_entry)
        doc_ref.update({"fields": fields})
    else:
        doc_ref.set({"user_id": user_id, "fields": [field_entry]})
    return f"Recorded skill '{skill_id}' for user '{user_id}' with evidence citation from '{source}'."
