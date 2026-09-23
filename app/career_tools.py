"""Actionable career guidance and external data tools for Pivot Career Copilot.

Includes:
1. calculate_tiered_targeting - Deterministic weighted gap arithmetic for career tiers.
2. analyze_ats_readiness - Keyword coverage and formatting compliance checks.
3. fetch_github_profile_and_repos - Live GitHub repository and language extraction.
4. fetch_company_job_postings - Live Greenhouse and Lever job board query.
5. filter_market_reality - Recent hiring velocity and market reality filter.
6. compile_master_plan - Assembles Firestore state into a complete structured plan.md.
7. upload_tailored_resume_to_gcs - Uploads tailored resume drafts to Cloud Storage.
"""

import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types
from google.genai.types import GenerateContentConfig, Modality
from .firestore_tools import PROJECT_ID, get_db

GCS_BUCKET_NAME = "pivot-career-copilot-files"


def calculate_tiered_targeting(
    verified_skills: List[str],
    target_domain: str = "ai_engineering",
) -> Dict[str, Any]:
    """Calculates Safe, Moderate, and Ambitious career tiers using deterministic weighted gap arithmetic.

    Args:
        verified_skills: List of verified candidate skills (e.g. ['python', 'sql', 'docker', 'apis']).
        target_domain: Target career domain ('ai_engineering', 'data_engineering', 'cloud_backend').

    Returns:
        Structured breakdown with Safe, Moderate, and Ambitious roles, readiness percentages,
        identified gaps, and realistic timeline in weeks.
    """
    normalized_skills = {s.strip().lower().replace(" ", "_") for s in verified_skills}

    domain_archetypes = {
        "ai_engineering": {
            "safe": {
                "role": "Python Backend Engineer (AI Services)",
                "required": ["python", "apis", "rest", "git", "sql", "docker", "fastapi"],
                "base_timeline_weeks": 3,
            },
            "moderate": {
                "role": "Applied AI / RAG Engineer",
                "required": ["python", "pytorch", "rag", "embeddings", "vector_databases", "gemini", "adk"],
                "base_timeline_weeks": 8,
            },
            "ambitious": {
                "role": "Lead AI Systems Architect",
                "required": ["agent_orchestration", "a2a", "evaluations", "distributed_inference", "fine_tuning", "security"],
                "base_timeline_weeks": 16,
            },
        },
        "data_engineering": {
            "safe": {
                "role": "Data Analyst / Analytics Engineer",
                "required": ["sql", "python", "data_modeling", "git", "dashboards"],
                "base_timeline_weeks": 2,
            },
            "moderate": {
                "role": "Big Data Pipeline Engineer",
                "required": ["spark", "bigquery", "airflow", "kafka", "dbt", "python"],
                "base_timeline_weeks": 8,
            },
            "ambitious": {
                "role": "Principal Data Platform Architect",
                "required": ["lakehouse", "realtime_streaming", "data_governance", "distributed_systems"],
                "base_timeline_weeks": 18,
            },
        },
    }

    archetype = domain_archetypes.get(target_domain, domain_archetypes["ai_engineering"])
    results = {"target_domain": target_domain, "evaluated_skills": list(normalized_skills)}

    for tier_key in ["safe", "moderate", "ambitious"]:
        tier_cfg = archetype[tier_key]
        reqs = tier_cfg["required"]
        matched = [r for r in reqs if any(r in s or s in r for s in normalized_skills)]
        missing = [r for r in reqs if r not in matched]

        match_ratio = len(matched) / len(reqs) if reqs else 1.0

        if tier_key == "safe":
            readiness_pct = int(60 + (match_ratio * 38))
            weeks = max(1, int(tier_cfg["base_timeline_weeks"] * (1.1 - match_ratio)))
        elif tier_key == "moderate":
            readiness_pct = int(40 + (match_ratio * 45))
            weeks = max(4, int(tier_cfg["base_timeline_weeks"] * (1.3 - match_ratio)))
        else:
            readiness_pct = int(25 + (match_ratio * 45))
            weeks = max(8, int(tier_cfg["base_timeline_weeks"] * (1.5 - match_ratio)))

        readiness_pct = min(98, max(15, readiness_pct))

        results[tier_key] = {
            "role": tier_cfg["role"],
            "readiness": f"{readiness_pct}%",
            "readiness_score": readiness_pct,
            "matched_skills": matched,
            "gap_skills": missing if missing else ["None - requirements fully met"],
            "timeline_weeks": weeks,
        }

    return results


def analyze_ats_readiness(
    resume_text: str,
    target_role_requirements: str,
) -> Dict[str, Any]:
    """Performs deterministic keyword coverage, format, and ATS compliance analysis on a resume.

    Args:
        resume_text: Plain text or markdown of the candidate's resume.
        target_role_requirements: Job description requirements or keywords string.

    Returns:
        Objective ATS score, keyword coverage analysis, missing critical skills, and section checks.
    """
    stopwords = {
        "and", "the", "with", "for", "our", "you", "will", "are", "that", "this",
        "have", "from", "your", "work", "team", "years", "role", "must", "plus",
        "about", "their", "into", "been", "also", "using", "able", "skills",
    }

    # Extract target terms
    raw_req_terms = re.findall(r"[A-Za-z0-9_\+#\.\-]{2,}", target_role_requirements.lower())
    req_terms = [t for t in set(raw_req_terms) if t not in stopwords and len(t) > 2]

    resume_lower = resume_text.lower()
    matched_terms = [t for t in req_terms if t in resume_lower]
    missing_terms = [t for t in req_terms if t not in resume_lower]

    keyword_ratio = len(matched_terms) / len(req_terms) if req_terms else 1.0

    # Section structural checks
    sections_checked = {
        "contact_info": bool(re.search(r"@|\bphone\b|\blinkedin\b|\bgithub\b", resume_lower)),
        "experience": bool(re.search(r"\bexperience\b|\bemployment\b|\bwork history\b", resume_lower)),
        "education": bool(re.search(r"\beducation\b|\bdegree\b|\buniversity\b|\bcollege\b", resume_lower)),
        "skills": bool(re.search(r"\bskills\b|\btechnologies\b|\bproficiencies\b", resume_lower)),
    }
    sections_present_count = sum(1 for v in sections_checked.values() if v)
    structure_score = (sections_present_count / len(sections_checked)) * 100

    overall_ats_score = int((keyword_ratio * 70) + (structure_score * 0.3))
    overall_ats_score = min(100, max(10, overall_ats_score))

    return {
        "overall_ats_score": f"{overall_ats_score}%",
        "numeric_score": overall_ats_score,
        "keyword_coverage": f"{len(matched_terms)}/{len(req_terms)} ({int(keyword_ratio * 100)}%)",
        "matched_keywords": sorted(matched_terms)[:15],
        "missing_critical_keywords": sorted(missing_terms)[:15],
        "section_checks": sections_checked,
        "ats_status": "EXCELLENT" if overall_ats_score >= 80 else ("GOOD" if overall_ats_score >= 60 else "NEEDS_OPTIMIZATION"),
    }


def fetch_github_profile_and_repos(username: str) -> Dict[str, Any]:
    """Fetches public repositories, top languages, and commit metadata for a GitHub user.

    Uses the public, unauthenticated GitHub REST API to verify coding claims with real evidence.

    Args:
        username: GitHub handle (e.g. 'torvalds' or 'google').

    Returns:
        User profile stats, list of recent repositories with languages, stars, and topics.
    """
    clean_username = username.strip().lstrip("@")
    url = f"https://api.github.com/users/{clean_username}/repos?sort=updated&per_page=8"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PivotCareerCopilot-Agent/1.0", "Accept": "application/vnd.github.v3+json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        repos = []
        languages_detected = {}
        for r in data:
            lang = r.get("language")
            if lang:
                languages_detected[lang] = languages_detected.get(lang, 0) + 1
            repos.append({
                "name": r.get("name"),
                "description": r.get("description") or "No description",
                "language": lang,
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "updated_at": r.get("updated_at"),
                "html_url": r.get("html_url"),
            })

        return {
            "status": "success",
            "username": clean_username,
            "total_fetched": len(repos),
            "primary_languages": sorted(languages_detected.keys(), key=lambda l: languages_detected[l], reverse=True),
            "recent_repositories": repos,
        }
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": f"GitHub API error: {e.reason}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_company_job_postings(
    company_slug: str,
    board_type: str = "greenhouse",
) -> Dict[str, Any]:
    """Fetches live job postings from a company's public Greenhouse or Lever job board.

    Args:
        company_slug: The company ID or slug (e.g. 'anthropic', 'cloudflare', 'stripe', 'figma').
        board_type: 'greenhouse' or 'lever'. Defaults to 'greenhouse'.

    Returns:
        List of active job titles, departments, locations, and direct application links.
    """
    clean_slug = company_slug.strip().lower()
    if board_type.lower() == "lever":
        url = f"https://api.lever.co/v0/postings/{clean_slug}?mode=json"
    else:
        url = f"https://boards-api.greenhouse.io/v1/boards/{clean_slug}/jobs"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PivotCareerCopilot-Agent/1.0", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        jobs = []
        if board_type.lower() == "lever":
            for item in data[:20]:
                jobs.append({
                    "id": item.get("id"),
                    "title": item.get("text"),
                    "department": (item.get("categories") or {}).get("department", "General"),
                    "location": (item.get("categories") or {}).get("location", "Remote"),
                    "url": item.get("hostedUrl"),
                    "updated_at": item.get("createdAt"),
                })
        else:
            raw_jobs = data.get("jobs", [])
            for item in raw_jobs[:20]:
                departments = [d.get("name") for d in item.get("departments", [])]
                jobs.append({
                    "id": str(item.get("id")),
                    "title": item.get("title"),
                    "department": ", ".join(departments) if departments else "General",
                    "location": (item.get("location") or {}).get("name", "Not specified"),
                    "url": item.get("absolute_url"),
                    "updated_at": item.get("updated_at"),
                })

        return {
            "status": "success",
            "company": clean_slug,
            "board_type": board_type,
            "total_open_roles": len(jobs),
            "jobs": jobs,
        }
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": f"Job board request returned: {e.reason}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def filter_market_reality(
    company_slug: str,
    role_keyword: str = "",
    days: int = 30,
    board_type: str = "greenhouse",
) -> Dict[str, Any]:
    """Filters company job postings to check recent hiring velocity and verify active market demand.

    Args:
        company_slug: The company slug (e.g. 'cloudflare', 'stripe', 'anthropic').
        role_keyword: Optional keyword to filter roles (e.g. 'engineer', 'ai', 'manager').
        days: Only consider postings updated or created within this number of days. Defaults to 30.
        board_type: 'greenhouse' or 'lever'.

    Returns:
        Market reality check with active role counts, matching postings, and status.
    """
    board_data = fetch_company_job_postings(company_slug=company_slug, board_type=board_type)
    if board_data.get("status") != "success":
        return board_data

    jobs = board_data.get("jobs", [])
    keyword = role_keyword.strip().lower()

    filtered_jobs = []
    cutoff_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

    for job in jobs:
        title = job.get("title", "").lower()
        dept = job.get("department", "").lower()

        if keyword and (keyword not in title and keyword not in dept):
            continue

        raw_date = job.get("updated_at")
        is_recent = True
        if raw_date:
            try:
                # Handle ISO formatted strings
                clean_date = raw_date.replace("Z", "+00:00")
                parsed_dt = datetime.datetime.fromisoformat(clean_date)
                if parsed_dt < cutoff_dt:
                    is_recent = False
            except Exception:
                is_recent = True

        if is_recent:
            filtered_jobs.append(job)

    market_status = "ACTIVE_HIRING" if len(filtered_jobs) >= 2 else ("MODERATE_ACTIVITY" if len(filtered_jobs) == 1 else "NO_RECENT_POSTINGS")

    return {
        "status": "success",
        "company": company_slug,
        "role_keyword": role_keyword,
        "window_days": days,
        "market_status": market_status,
        "recent_matching_count": len(filtered_jobs),
        "recent_roles": filtered_jobs,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def compile_master_plan(user_id: str = "default_user") -> Dict[str, Any]:
    """Assembles all Firestore state (intake, target tiers, shortlist) into a cohesive, structured plan.md.

    Args:
        user_id: The ID of the candidate. Defaults to 'default_user'.

    Returns:
        Summary of the compiled plan and full structured markdown content.
    """
    db = get_db()
    tiers_doc = db.collection("target_tiers").document(user_id).get()
    shortlist_doc = db.collection("shortlist").document(user_id).get()
    intake_doc = db.collection("intake_profile").document(user_id).get()

    tiers = tiers_doc.to_dict() if tiers_doc.exists else {}
    shortlist = shortlist_doc.to_dict() if shortlist_doc.exists else {}
    intake = intake_doc.to_dict() if intake_doc.exists else {}

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_lines = [
        f"# 🎯 Pivot Career Action Plan: {user_id}",
        f"*Compiled at: {now_iso}*",
        "",
        "---",
        "",
        "## 1. Verified Evidence & Background Signal",
    ]

    fields = intake.get("fields", [])
    if fields:
        for f in fields:
            md_lines.append(f"- **{f.get('skill_id', 'Skill')}**: {f.get('value')}")
            md_lines.append(f"  - *Evidence Citation*: `{f.get('source')}` — \"{f.get('snippet', '')}\"")
    else:
        md_lines.append("*No intake profile items verified yet.*")

    md_lines.extend([
        "",
        "## 2. Target Career Tiers & Readiness Scoring",
    ])

    for tier_name in ["safe", "moderate", "ambitious"]:
        t = tiers.get(tier_name, {})
        if t:
            icon = "🟢" if tier_name == "safe" else ("🟡" if tier_name == "moderate" else "🔴")
            md_lines.append(f"### {icon} {tier_name.capitalize()} Tier: {t.get('role', 'TBD')}")
            md_lines.append(f"- **Readiness**: {t.get('readiness', 'N/A')}")
            md_lines.append(f"- **Estimated Timeline**: {t.get('timeline_weeks', 'N/A')} weeks")
            md_lines.append(f"- **Identified Gap / Focus Area**: {t.get('gap', 'None')}")
            md_lines.append("")

    md_lines.extend([
        "## 3. Shortlisted Target Companies & Roles",
    ])

    entries = shortlist.get("entries", [])
    if entries:
        for idx, item in enumerate(entries, 1):
            posting_ref = f" (Posting ID: `{item.get('source_posting_id')}`)" if item.get("source_posting_id") else ""
            md_lines.append(f"{idx}. **{item.get('company')}** — {item.get('role')}{posting_ref}")
    else:
        md_lines.append("*No companies shortlisted yet.*")

    md_lines.extend([
        "",
        "## 4. Next Milestones & Gap-Closing Roadmap",
        "1. Complete prioritized study roadmap for Moderate tier gaps.",
        "2. Run live ATS keyword checks on tailored resume against shortlist job postings.",
        "3. Monitor 7-day Market Reality signals before submitting applications.",
    ])

    full_markdown = "\n".join(md_lines)

    # Persist the plan in Firestore
    plan_record = {
        "user_id": user_id,
        "compiled_at": now_iso,
        "content": full_markdown,
    }
    db.collection("plan").document(user_id).set(plan_record)

    return {
        "status": "success",
        "user_id": user_id,
        "compiled_at": now_iso,
        "summary": f"Compiled plan with {len(fields)} verified skills, 3 career tiers, and {len(entries)} shortlisted positions.",
        "plan_markdown": full_markdown,
    }


def upload_tailored_resume_to_gcs(
    user_id: str,
    role_id: str,
    resume_markdown: str,
) -> Dict[str, Any]:
    """Uploads a tailored resume draft to Cloud Storage and generates its public URL.

    Args:
        user_id: The candidate ID.
        role_id: Target role identifier (e.g. 'ai_solutions_architect').
        resume_markdown: Full text or markdown content of the tailored resume.

    Returns:
        Upload status, Cloud Storage path, GCS URI, and public accessible URL.
    """
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        blob_path = f"resumes/{user_id}/{role_id}.md"
        blob = bucket.blob(blob_path)

        blob.upload_from_string(
            resume_markdown,
            content_type="text/markdown",
        )

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"
        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_path}"

        return {
            "status": "success",
            "bucket": GCS_BUCKET_NAME,
            "blob_path": blob_path,
            "gcs_uri": gcs_uri,
            "public_url": public_url,
            "bytes_uploaded": len(resume_markdown.encode("utf-8")),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_job_board_api(
    keyword: str = "",
    remote_only: bool = False,
    limit: int = 5,
) -> Dict[str, Any]:
    """Queries the Arbeitnow job board aggregator API from the public-apis directory.

    Searches real, live tech job listings across Europe and Remote, with role,
    remote filters, and tag matching. Reads optional API key from ARBEITNOW_API_KEY env var.

    Args:
        keyword: Search query for title, company, or skills (e.g. 'python', 'ai', 'engineer').
        remote_only: If True, only returns roles flagged as remote.
        limit: Maximum number of jobs to return (default 5, max 10).

    Returns:
        Structured dictionary with matched jobs, companies, locations, and application links.
    """
    import os
    api_key = os.environ.get("ARBEITNOW_API_KEY")
    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {"User-Agent": "PivotCareerCopilot/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw_jobs = data.get("data", [])
        kw = keyword.strip().lower()

        matched = []
        for j in raw_jobs:
            if remote_only and not j.get("remote", False):
                continue

            title = j.get("title", "").lower()
            company = j.get("company_name", "").lower()
            tags = [t.lower() for t in j.get("tags", [])]

            if kw:
                if kw not in title and kw not in company and not any(kw in t for t in tags):
                    continue

            matched.append({
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("location", "Remote/Not specified"),
                "remote": j.get("remote", False),
                "tags": j.get("tags", [])[:5],
                "url": j.get("url"),
                "created_at": j.get("created_at"),
            })

            if len(matched) >= min(limit, 10):
                break

        return {
            "status": "success",
            "source": "Arbeitnow (public-apis directory)",
            "query": keyword,
            "remote_only": remote_only,
            "total_found": len(matched),
            "jobs": matched,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed querying Arbeitnow API: {e}"}


async def generate_career_visual_asset(
    item_name: str,
    asset_type: str = "career_badge",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates an image for a career domain item using gemini-3.1-flash-lite-image in the global region.

    Saves the image via tool_context.save_artifact for the Playground's Artifacts panel,
    and uploads the image bytes directly to the public Cloud Storage bucket, returning its public HTTPS URL.
    Hardcodes the bucket name and GCP project as strings without saving locally.

    Args:
        item_name: Target career role or milestone (e.g. 'AI Solutions Architect', 'Cloud Platform Lead').
        asset_type: Type of visual ('career_badge', 'roadmap_card', 'milestone_certificate', 'avatar'). Defaults to 'career_badge'.
        tool_context: ADK ToolContext injected by the framework for saving artifacts.

    Returns:
        Structured response with the public Cloud Storage HTTPS URL, GCS URI, and artifact details.
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_name.lower())
    timestamp = int(datetime.datetime.now().timestamp())
    artifact_filename = f"{safe_name}_{asset_type}_{timestamp}.png"

    prompt = (
        f"A clean, modern, high-quality minimalist vector design of a {asset_type.replace('_', ' ')} "
        f"for the role '{item_name}'. Professional aesthetic, vibrant gradient colors, clean emblem badge icon, "
        f"vector illustration style, solid clean background."
    )

    try:
        # Initialize Google GenAI client in the global region
        genai_client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-04-2479ded67a3b",  # Hardcoded project ID string
            location="global",  # Global region
        )

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=GenerateContentConfig(response_modalities=[Modality.IMAGE]),
        )

        image_bytes = None
        mime_type = "image/png"
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"
                    break
            if image_bytes:
                break

        if not image_bytes:
            return {
                "status": "error",
                "message": "Model response did not contain image bytes.",
            }

        # (1) Save with tool_context.save_artifact for the Playground Artifacts panel
        saved_in_artifacts = False
        if tool_context is not None and hasattr(tool_context, "save_artifact"):
            part_artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            try:
                await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=part_artifact,
                )
                saved_in_artifacts = True
            except TypeError:
                try:
                    await tool_context.save_artifact(
                        filename=artifact_filename,
                        data=image_bytes,
                        mime_type=mime_type,
                    )
                    saved_in_artifacts = True
                except Exception:
                    pass
            except Exception:
                pass

        # (2) Upload same image bytes to the public Cloud Storage bucket (hardcoded string)
        storage_client = storage.Client(project="qwiklabs-gcp-04-2479ded67a3b")
        bucket = storage_client.bucket("pivot-career-copilot-files")

        blob_path = f"visuals/{artifact_filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/pivot-career-copilot-files/{blob_path}"

        return {
            "status": "success",
            "item_name": item_name,
            "asset_type": asset_type,
            "artifact_filename": artifact_filename,
            "saved_in_playground_artifacts": saved_in_artifacts,
            "bucket": "pivot-career-copilot-files",
            "object_path": blob_path,
            "gcs_uri": f"gs://pivot-career-copilot-files/{blob_path}",
            "public_url": public_url,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed generating image: {e}"}



async def generate_career_video_asset(
    item_name: str,
    asset_type: str = "motion_badge",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates a short video for a career domain item using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the video via tool_context.save_artifact for the Playground's Artifacts panel,
    and uploads the video bytes directly to the public Cloud Storage bucket, returning its public HTTPS URL.
    Hardcodes the bucket name and GCP project as strings without writing to a local file.

    Args:
        item_name: Target career role or milestone (e.g. 'AI Solutions Architect', 'Cloud Platform Lead').
        asset_type: Type of motion asset ('motion_badge', 'transition_teaser', 'milestone_celebration'). Defaults to 'motion_badge'.
        tool_context: ADK ToolContext injected by the framework for saving artifacts.

    Returns:
        Structured response with the public Cloud Storage HTTPS URL, GCS URI, and artifact details.
    """
    import base64
    import google.auth
    import google.auth.transport.requests
    import requests

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_name.lower())
    timestamp = int(datetime.datetime.now().timestamp())
    artifact_filename = f"{safe_name}_{asset_type}_{timestamp}.mp4"

    prompt = (
        f"A 4-second cinematic motion graphics video of a glowing modern 3D tech badge "
        f"rotating smoothly for '{item_name}'. Professional aesthetic, vibrant neon accents, "
        f"clean typography, dark sleek background, smooth looping motion."
    )

    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        url = "https://aiplatform.googleapis.com/v1beta1/projects/qwiklabs-gcp-04-2479ded67a3b/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gemini-omni-flash-preview",
            "input": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
        }

        res = requests.post(url, headers=headers, json=payload, timeout=180)
        if res.status_code != 200:
            return {"status": "error", "message": f"Omni API returned status {res.status_code}: {res.text}"}

        data = res.json()
        video_bytes = None
        mime_type = "video/mp4"

        for step in data.get("steps", []):
            for c in step.get("content", []):
                if c.get("type") == "video" and "data" in c:
                    video_bytes = base64.b64decode(c["data"])
                    mime_type = c.get("mime_type") or "video/mp4"
                    break
            if video_bytes:
                break

        if not video_bytes:
            return {"status": "error", "message": "Model response did not contain video bytes."}

        # (1) Save with tool_context.save_artifact for Playground Artifacts panel
        saved_in_artifacts = False
        if tool_context is not None and hasattr(tool_context, "save_artifact"):
            try:
                part_artifact = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                await tool_context.save_artifact(filename=artifact_filename, artifact=part_artifact)
                saved_in_artifacts = True
            except TypeError:
                try:
                    await tool_context.save_artifact(filename=artifact_filename, data=video_bytes, mime_type=mime_type)
                    saved_in_artifacts = True
                except Exception:
                    pass
            except Exception:
                pass

        # (2) Upload same video bytes to the public Cloud Storage bucket (hardcoded string)
        storage_client = storage.Client(project="qwiklabs-gcp-04-2479ded67a3b")
        bucket = storage_client.bucket("pivot-career-copilot-files")

        blob_path = f"visuals/{artifact_filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/pivot-career-copilot-files/{blob_path}"

        return {
            "status": "success",
            "item_name": item_name,
            "asset_type": asset_type,
            "artifact_filename": artifact_filename,
            "saved_in_playground_artifacts": saved_in_artifacts,
            "bucket": "pivot-career-copilot-files",
            "object_path": blob_path,
            "gcs_uri": f"gs://pivot-career-copilot-files/{blob_path}",
            "public_url": public_url,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed generating video with Omni model: {e}"}
