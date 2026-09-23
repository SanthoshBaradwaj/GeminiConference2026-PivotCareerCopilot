"""Seed script for Pivot Career Copilot Firestore collections.

Hardcodes the GCP project ID string per project guidelines to ensure
compatibility after deployment to Agent Platform.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-2479ded67a3b"


def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)

    # 1. Target Tiers (3-4 sample entries)
    target_tiers_samples = [
        {
            "user_id": "default_user",
            "safe": {
                "role": "Senior Python Backend Engineer",
                "readiness": "90%",
                "gap": "Minor: gRPC and OpenTelemetry telemetry standards",
                "timeline_weeks": 2,
            },
            "moderate": {
                "role": "AI Solutions Architect",
                "readiness": "72%",
                "gap": "Multi-agent evaluation and Vertex AI Agent Engine deployments",
                "timeline_weeks": 8,
            },
            "ambitious": {
                "role": "Principal AI Platform Lead",
                "readiness": "50%",
                "gap": "Enterprise security boundaries, Memory Bank systems, and A2A integration",
                "timeline_weeks": 16,
            },
        },
        {
            "user_id": "user_finance_to_ai",
            "safe": {
                "role": "Financial Quantitative Analyst / Analytics Engineer",
                "readiness": "85%",
                "gap": "Advanced Python data pipelines (dbt / BigQuery)",
                "timeline_weeks": 4,
            },
            "moderate": {
                "role": "Applied AI / ML Engineer (FinTech)",
                "readiness": "68%",
                "gap": "PyTorch fine-tuning and LLM evaluation frameworks",
                "timeline_weeks": 10,
            },
            "ambitious": {
                "role": "Research Engineer / AI Agent Architect",
                "readiness": "45%",
                "gap": "Autonomous agent orchestration and distributed inference",
                "timeline_weeks": 20,
            },
        },
        {
            "user_id": "user_swe_to_ml",
            "safe": {
                "role": "Full Stack Engineer (AI-Infused Products)",
                "readiness": "88%",
                "gap": "Gemini API tool calling and streaming interfaces",
                "timeline_weeks": 3,
            },
            "moderate": {
                "role": "Machine Learning Platform Engineer",
                "readiness": "65%",
                "gap": "Vector databases, RAG pipelines, and model serving infrastructure",
                "timeline_weeks": 12,
            },
            "ambitious": {
                "role": "Founding AI Engineer",
                "readiness": "42%",
                "gap": "End-to-end multi-agent orchestration, fine-tuning, and greenfield product vision",
                "timeline_weeks": 24,
            },
        },
        {
            "user_id": "user_data_to_agentic",
            "safe": {
                "role": "Senior Data Engineer (AI & Analytics)",
                "readiness": "92%",
                "gap": "Unstructured document parsing with Gemini multimodal",
                "timeline_weeks": 2,
            },
            "moderate": {
                "role": "RAG & Retrieval Systems Engineer",
                "readiness": "70%",
                "gap": "Hybrid search, semantic re-ranking, and chunking evaluations",
                "timeline_weeks": 9,
            },
            "ambitious": {
                "role": "Lead Cognitive Architect",
                "readiness": "48%",
                "gap": "Long-term stateful agent memory systems and cognitive loops",
                "timeline_weeks": 18,
            },
        },
    ]

    print(f"Seeding {len(target_tiers_samples)} target_tiers documents...")
    for entry in target_tiers_samples:
        doc_ref = db.collection("target_tiers").document(entry["user_id"])
        doc_ref.set(entry)
        print(f"  ✓ target_tiers/{entry['user_id']}")

    # 2. Shortlist samples
    shortlist_samples = [
        {
            "user_id": "default_user",
            "entries": [
                {
                    "company": "DeepMind Partner Labs",
                    "role": "AI Solutions Architect",
                    "source_posting_id": "gh_83921",
                },
                {
                    "company": "Anthropic Ecosystems",
                    "role": "Senior Agent Systems Engineer",
                    "source_posting_id": "lev_44910",
                },
                {
                    "company": "Vertex AI Solutions",
                    "role": "Principal AI Engineer",
                    "source_posting_id": "gh_10293",
                },
            ],
        },
        {
            "user_id": "user_finance_to_ai",
            "entries": [
                {
                    "company": "Two Sigma AI Labs",
                    "role": "Applied AI / ML Engineer (FinTech)",
                    "source_posting_id": "gh_77123",
                },
                {
                    "company": "Stripe",
                    "role": "Financial Quantitative Analyst",
                    "source_posting_id": "lev_99341",
                },
            ],
        },
    ]

    print(f"Seeding {len(shortlist_samples)} shortlist documents...")
    for entry in shortlist_samples:
        doc_ref = db.collection("shortlist").document(entry["user_id"])
        doc_ref.set(entry)
        print(f"  ✓ shortlist/{entry['user_id']}")

    # 3. Intake profile sample
    intake_sample = {
        "user_id": "default_user",
        "fields": [
            {
                "skill_id": "python_backend",
                "value": "7 years building FastAPI & microservices",
                "source": "resume.pdf",
                "snippet": "Led migration of core banking services to Python microservices",
            },
            {
                "skill_id": "cloud_gcp",
                "value": "GCP Cloud Architect certified",
                "source": "linkedin.md",
                "snippet": "Experienced with Cloud Run, Vertex AI, and Firestore",
            },
            {
                "skill_id": "genai_tools",
                "value": "Gemini API & ADK framework",
                "source": "github:cszhu/pivot-career-copilot",
                "snippet": "Implemented tool-use and A2A protocol for agents",
            },
        ],
    }
    db.collection("intake_profile").document("default_user").set(intake_sample)
    print("  ✓ intake_profile/default_user")

    print("\n✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed()
