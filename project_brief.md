# Project Brief: Pivot Career Copilot

**App slug:** `pivot-career-copilot`
**Repo name (for Publish to GitHub):** `buildwithgemini-pivot-career-copilot`
**Status:** Replaces the lab's default `project_brief.md`. Written to be read by AGY at every later "look at my project_brief.md" checkpoint in the lab, not just at Design Your App.
**Where you are:** Base agent built and tested locally (Build Your First Agent complete). Everything below is what to hand AGY starting at Design Your App.

---

## 1. One-line concept

A conversational agent that takes a user from "here's my background" to "I got the job" — grounded in evidence the user actually provided, never in a guess or a plausible-sounding inference.

## 2. Problem & user

Career tools either trust a résumé's self-reported claims at face value, or they stop at a generic "here's a role that might fit" recommendation with no path to an actual offer. This agent does neither: it verifies what the user can actually back up, then carries them all the way through targeting, shortlisting, gap-closing, tailoring, and screening — as one continuous conversation with a durable memory of where they are.

**User:** someone actively changing careers or roles, who has a résumé, a GitHub profile, and/or a LinkedIn history, and wants a real plan — not a chatbot that answers questions about job-hunting in general.

## 3. Core user journey (as a conversation, not a multi-page app)

This is a chat-first ADK agent. The "screens" from earlier planning documents become **conversation phases**, and A2UI cards (§10) are what make each phase feel like more than plain text. Nothing here requires a custom multi-page frontend — the phasing lives in the agent's state machine, not in routing.

```
Upload/paste →  Verify  →  Target  →  Shortlist  →  Prepare  →  Apply  →  Track
(intake)         (interview)  (tiers)   (companies)  (gaps+study) (tailor+ATS) (plan.md)
```

The user can re-enter at any phase in later sessions — Memory Bank (§9) is what makes that not feel like starting over.

---

## 4. Data model (Firestore) — for the "Add Persistent Storage" step

Hand this to AGY directly; it's already domain-specific, so there's nothing to look up.

```
intake_profile      { user_id, fields: [ {skill_id, value, source, snippet} ] }
verified_signal     { user_id, skill_id, claimed_level, verified_level, evidence_ref }
target_profile      { user_id, interests, positioning, salary_input (optional) }
target_tiers        { user_id, safe, moderate, ambitious: {role, readiness, gap, timeline_weeks} }
shortlist           { user_id, entries: [ {company, role, source_posting_id} ] }
gap_lists           { user_id, role_id, strengthen: [], learn_new: [], soft_skills: [] }  # each item cited both sides
market_reality      { user_id, role_id, checked_at, postings: [], delta_note }
prep_docs           { user_id, role_id, content }
resume_versions     { user_id, role_id, base, tailored, ats_score, ai_detection_score, created_at }
plan                { user_id, compiled_at, sections: {} }  # the plan.md content, structured
```

Seed data: 3–4 sample `target_tiers` entries and one sample `shortlist` so the Playground has something to query before real intake happens.

**Hardcode the project ID** for the Firestore client and any seed script, per the lab's own warning — read it with `gcloud config get-value project`, never from `google.auth.default()` or `GOOGLE_CLOUD_PROJECT` (those return the project *number* on Agent Platform, which breaks Firestore silently after deploy).

## 5. Files/blobs (Cloud Storage)

One bucket, `pivot-career-copilot-files` (add a short random suffix if taken), for uploaded résumés and generated tailored drafts.

**Deviation from the lab's default pattern, deliberately:** do **not** set this bucket to public-read. The lab's own instructions default to public objects because they're written for generated product images; a résumé is PII. Keep the bucket private and serve files through signed URLs. Tell AGY this explicitly when creating the bucket — the copy-paste prompt in the lab asks for public permissions by default, and that's wrong here.

---

## 6. Agent & tool roster — for "Add Tools" and general agent design

ADK implementation column added so AGY knows what to actually scaffold, not just what the stage does.

| # | Name | What it does | ADK implementation |
|---|---|---|---|
| 1 | Intake & Grounding | Parses résumé, LinkedIn text/`linkedin.md`, GitHub public repos (API), private-repo text, collab write-up into `intake_profile`, every field source-tagged | Sub-agent |
| 2 | Adaptive Readiness Interviewer | Asks targeted questions about the highest-risk claims; writes `verified_signal` | Sub-agent |
| 3 | Interest & Positioning | Elicits interests, candidate directions, optional salary input | Sub-agent |
| 4 | Tiered Targeting | Safe/Moderate/Ambitious scoring + realistic timeline from weighted-gap arithmetic | **Function tool** — pure arithmetic, no judgment needed; a good candidate for the code-execution sandbox (§8) |
| 5 | Job Discovery | Calls `job_search`, scores postings against the verified vector | Sub-agent + function tool (`job_search`) |
| 6 | Shortlist | Narrows to 3–5 companies, multiple roles allowed per company | Sub-agent |
| 7 | Gap & Soft-Skill | Per shortlisted role: strengthen / learn new / soft skills, each cited both sides | Sub-agent |
| 8 | Market Reality | `job_search` filtered to last 7 days per shortlisted role | Function tool |
| 9 | Interview Prep | Study checklist per role, dependency-ordered | Sub-agent |
| 10 | Resume Tailor | Rewrites résumé language for a target posting — cannot exceed the verified vector | Sub-agent |
| 11 | ATS Readiness | Keyword coverage, structure, format checks | **Function tool** — deterministic, sandbox candidate |
| 12 | Anti-AI-Detection | Style-only revision pass, never touches content/claims | Sub-agent |
| 13 | Prep-Doc Synthesizer | Combines 7–12 into one document per role | Function tool |
| 14 | Master Plan Compiler | Assembles all Firestore state into `plan.md` | Function tool |

**When AGY asks "which 2–3 tools should I build first"**, point it at #4 (Tiered Targeting) and #11 (ATS Readiness) — both are pure functions, no external API, and prove the deterministic-scoring pattern before anything generative is layered on.

---

## 7. External free APIs — for "Call External APIs"

Already researched; hand this table to AGY instead of having it browse public-apis/APIsList from scratch.

| Need | API | Key required? |
|---|---|---|
| GitHub public repos | `api.github.com` (GitHub REST API) | No (60 req/hr unauthenticated; a personal access token raises this to 5,000/hr) |
| Job postings (Job Discovery, Market Reality) | Greenhouse and Lever public job-board JSON endpoints, per company | No — both include posting/update timestamps, which is what makes the "last 7 days" filter in #8 work |

**Explicit non-goals, do not build these even if AGY suggests them:**
- **No LinkedIn API of any kind.** No general free public API exists for arbitrary profile access; LinkedIn's official API is partner-gated, and scraping carries real ToS exposure. LinkedIn input is user-pasted text or a self-authored `linkedin.md` — a plain intake field, not an integration.
- **No salary-data API.** Salary is an optional field the user fills in during Stage 3 if they want to; it is never a blocking dependency and never fetched live.
- **No OAuth flow for private GitHub repos.** Private-repo work is user-described text, same as the collaboration write-up.

If AGY finds a genuinely useful *optional* API while browsing public-apis (e.g., something for company-info enrichment), that's fine as a stretch item (§15) — just not as a blocking dependency for the core pipeline.

---

## 8. Code execution / sandbox

Real, natural fit here — not forced. Use `AgentEngineSandboxCodeExecutor` for:
- Tiered Targeting's weighted-gap arithmetic (#4)
- ATS Readiness's keyword/structure scoring (#11)
- Any of the §12 validation metric computations that need to scan structured Firestore state rather than trust a single agent's self-report

This keeps the same "deterministic by choice" discipline from the original build: an agent asserts a number, the sandbox is where that number actually gets computed and can be checked.

---

## 9. Memory Bank — for "Add Memory"

Durable facts to configure for extraction, phrased the way the lab's own example phrases it ("Configure memory so that all user allergies are remembered"):

> Configure memory so that the user's location constraints, weekly hours available, sponsorship/visa status, and company preferences are remembered across sessions.

These are exactly the fields that should **not** need to be re-asked every time the user returns — that's the whole point of using Memory Bank instead of re-deriving them from scrolling back through a growing transcript (see §14 on why that distinction matters architecturally, not just for UX).

---

## 10. A2UI — for "Enrich Responses with A2UI"

Card/table types needed, mapped to the stage that produces them:

| Stage | A2UI component |
|---|---|
| Tiered Targeting (#4) | A table: Safe / Moderate / Ambitious rows, columns for role, readiness %, gap, timeline |
| Shortlist (#6) | Cards, one per company, listing its roles |
| Gap & Soft-Skill (#7) | A table: three columns (strengthen / learn new / soft skills), cited |
| Market Reality (#8) | A card per role: "confirmed" or "what changed," dated |
| Resume Tailor + ATS + Anti-detection (#10–12) | A scorecard card: ATS score, AI-detection risk, both before/after |
| Master Plan (#14) | A summary card linking to the full `plan.md`, not the whole document inline |

Build with `A2uiSchemaManager` version 0.8 and the Basic Catalog, same as the lab's default `enable-a2ui` skill — nothing project-specific changes about the wiring itself, only which cards get built.

---

## 11. Frontend

Use the lab's `build-agent-frontend` skill for the base FastAPI proxy + chat UI; customize with:

**Rebrand:** title "Pivot Career Copilot," header same, accent color a confident teal/green (`#0F9D58`-family) rather than the default — evokes "verified/earned," not generic AI-blue.

**Three example prompts** (ready for the "Add a row of 3 clickable example prompts" step):
1. "I want to move from finance into AI — here's my résumé."
2. "What roles am I actually ready for right now?"
3. "Show me my current plan."

**plan.md rendering:** the frontend should render the Master Plan summary card (§10) with a link/expand to the full document — never paste the whole `plan.md` into the chat pane directly.

---

## 12. Validation & evaluation

The lab's evaluation tooling specifics should be looked up via the Developer Knowledge MCP rather than guessed — ask AGY to confirm the current `agents-cli`/ADK eval-set mechanism before building this out. The eval **cases** themselves are already defined, though — build eval scenarios that check:

| Check | Pass condition |
|---|---|
| Citation coverage | Every claim/conclusion in Stages 1, 2, 7, 9, 10 output carries a checkable evidence citation |
| Résumé fidelity | Zero instances of a Stage 10 tailored résumé asserting a skill/level beyond the verified vector — this is a hard invariant, not a soft preference |
| Tier spread | Safe→Ambitious readiness gap is meaningful (≥15–20 pts), not collapsed to near-zero |
| Market-hit rate | Shortlisted roles have ≥1 confirming posting within the last 7 days at Stage 8 |
| Context-rot check | Re-reading a downstream conclusion's cited evidence against current Firestore state finds no mismatch |

Wire these as literal test conversations/assertions once the eval mechanism is confirmed — don't skip straight to "looks fine in the Playground."

---

## 13. Deployment

**Redeploy checklist**, since this project touches every category the lab warns about:
- Pass any API-key env vars with `--update-env-vars` (none required for the core pipeline per §7 — GitHub and Greenhouse/Lever are key-free — but keep this in mind if a stretch API needs one).
- Grant the deployed agent's service account `roles/datastore.user` (Firestore) and `roles/storage.objectAdmin` on the `pivot-career-copilot-files` bucket (Cloud Storage) — the deployed agent runs as its own service account with no access by default, unlike the Playground which runs as you.
- If using code execution (§8), confirm the Agent Platform API is enabled before redeploying.
- Frontend deploys separately, to Cloud Run, pointed at `AGENT_ENGINE_RESOURCE_NAME` and `AGENT_DIRECTORY`; its own service account needs `roles/aiplatform.user`.

---

## 14. Grounded & anti-context-rot architecture (non-negotiable, applies to every stage above)

- **Structured Firestore state is the source of truth; conversation transcript is not.** Every stage writes into the typed collections in §4; downstream agents read those, never the accumulated chat history.
- **Every conclusion cites its evidence item, enforced at the write boundary** — a résumé line, a GitHub repo, an interview answer, a specific posting requirement — not just requested in a prompt.
- **Durable facts live in Memory Bank (§9), not in re-derived context.**

## 15. Non-goals

- No fixed MCQ question bank — readiness is established conversationally (agent #2).
- No LinkedIn API, no salary API, no GitHub OAuth for private repos (§7).
- No claim anywhere in the system that exceeds what the verified vector supports.
- No plausible-sounding placeholder content in `plan.md` — an unfilled section is marked pending, never invented.

## 16. Suggested build order for this lab session

Fourteen agents/tools is a full production system, not a one-sitting workshop build. Build in this order and stop wherever the session runs out of time — everything below it is documented, not blocking:

**Phase 1 (core loop, do this first):** #1 Intake → #4 Tiered Targeting (function tool) → one A2UI table for it → Firestore wired for `intake_profile` and `target_tiers`. This alone is a demoable "upload → verified read on where you stand" loop.

**Phase 2 (targeting → shortlist):** #2 Adaptive Interview → #5 Job Discovery (with the GitHub/Greenhouse APIs) → #6 Shortlist → its A2UI cards.

**Phase 3 (prep & apply):** #7 Gap & Soft-Skill → #9 Interview Prep → #10 Resume Tailor → #11 ATS Readiness → #12 Anti-AI-detection.

**Phase 4 (assembly & memory):** #8 Market Reality → #13 Prep-Doc Synthesizer → #14 Master Plan Compiler → Memory Bank (§9) → the frontend (§11).

## 17. Stretch goals menu (for the "Stretch Goals" step)

- **Omni video**: a short "here's your plan, narrated" clip generated from the compiled `plan.md` — genuinely useful here, unlike a forced product-photo use case.
- **Cloud Trace**: inspect the full multi-agent execution flow across all 14 stages — valuable specifically because this pipeline is long enough that tracing which sub-agent/tool actually produced a given citation matters.
- **Company-info enrichment API** (optional, from public-apis) — if a genuinely free, no-key candidate turns up, use it to enrich Shortlist cards with basic company context; not a blocking dependency.
- **Frontend polish** to match the teal/green "verified" branding throughout, including the plan.md summary card.
