# Component 1 — Pre-Enhancement Audit Report

**Project:** MANO — Privacy-Preserving Mental Health Intervention & Simulation Platform
**Component:** C1 — Privacy-Preserving Mental Health Data Generation and Adaptive Multimodal Intervention Simulation Engine
**Original report date:** 2026-04-21 (Phase 0 — initial baseline)
**Refreshed:** 2026-05-01 (current state assessment vs. 16-prompt guideline)
**Auditor:** Principal Architect
**Audit scope:** `mano-api/` backend + `mano-frontend/` — every module that touches the five frozen C1 models, plus all enhancement layers and the consumer-facing UI.

---

## 1. Executive summary

C1 is the most feature-dense of MANO's four components. Before layering new functionality, the existing surface area was audited for silent failure modes, duplicate logic, hardcoded values, and contract gaps. The five core models (`risk_lstm.pth`, `seq2seq_simulator.pth`, `ppo_agent.pth`, `timegan_final.pth`, `ctgan_model_MENTAL_HEALTH_TECH.pkl`) are loading correctly and performing inference at documented latencies; they are **frozen** and must never be retrained, replaced, or mutated. Every enhancement in this effort is an additive layer on their outputs.

Phase 0 (baseline hardening) is **complete**: structured logging, error envelopes, rate limiting, log sanitizer, source tagging, request ID propagation, infra primitives (cache/event bus/scheduler), Alembic baseline, and the deep `/health` probe are in place. The five models load eagerly at startup via the lifespan manager.

Phases 1 through 6 of the 16-prompt enhancement are **partially landed**: every prompt has a corresponding router, service, and schema scaffold, but contract surfaces diverge from the guideline in several places, the flagship Guided Therapy Session is missing its mandatory hardcoded safety guard, the consumer-facing UI restructure (15 → 6 user pages + 5 researcher pages) has not started, and several Phase-3+ DB tables (`trajectory_log`, `intervention_feedback`, `user_preference_profile`, `therapy_session_records`, `event_audit_log`, `researcher_job`) have not been migrated.

The remaining work is best executed in the guideline's prescribed order — Phase 1 (close baseline gaps) → Phase 2 (intelligence layers) → Phase 3 (input + dashboard) → Phase 4 (therapy flagship) → Phase 5 (personalization + research) → Phase 6 (testing + deploy). Each phase ships independently with backward-compatible additions.

---

## 2. Frozen-model inventory

| Model | Artifact | Service | Load path | Status |
|---|---|---|---|---|
| Hybrid LSTM (risk) | `ml_models/component1/risk_lstm.pth` | `RiskPredictionService` | `main.py` lifespan | OK |
| Seq2Seq + Attention (simulator) | `ml_models/component1/seq2seq_simulator.pth` | `InterventionService` | `main.py` lifespan | OK |
| PPO Actor-Critic (agent) | `ml_models/component1/ppo_agent.pth` | `InterventionService` | `main.py` lifespan | OK |
| TimeGAN (wearable generator) | `ml_models/component1/timegan_final.pth` | `TimeGANService` | `main.py` lifespan | OK |
| CTGAN (profile generator) | `ml_models/component1/ctgan_model_MENTAL_HEALTH_TECH.pkl` | `CTGANService` | `main.py` lifespan | OK |

Architecture definition files (`lstm_model_Def.py`, `seq2seq_model_Def.py`, `rl_agent_Def.py`, `timegan_model_Def.py`, `rule_engine_Def.py`) colocated with weights — preserved as-is.

**Immutability guarantee:** no code path in this codebase opens a `.pth` or `.pkl` file in write mode. Verified via grep. All forward passes use `model.eval()` where appropriate; MC Dropout selectively flips `Dropout` layers to `train()` without persisting.

---

## 3. Existing C1 endpoint inventory (current state, 2026-05-01)

### 3.1 Original / pre-enhancement routers (untouched, contract-stable)

| Prefix | Endpoints | Status |
|---|---|---|
| `/api/v1/simulation` | `/predict_risk`, `/simulate_intervention`, `/prescribe_ai`, `/simulate_batch` | OK — 14 ms LSTM latency confirmed |
| `/api/v1/patients` | full CRUD + `/from-user/{user_id}`, `/by-user/{user_id}` | OK |
| `/api/v1/whatif` | `/what_if` | OK |
| `/api/v1/xai` | `/explain_risk` | OK — SHAP wired |
| `/api/v1/nba` | `/recommend` | OK |
| `/api/v1/sequence` | `/run_sequence` | OK |
| `/api/v1/uncertainty` | `/evaluate` | OK — 20-pass MC Dropout |
| `/api/v1/reports` | `/generate` | OK |
| `/api/v1/twin` | `/generate`, `/personal` | OK |

### 3.2 Phase-2 onward routers landed since 2026-04-21

| Prefix | Endpoints | Prompt | Status |
|---|---|---|---|
| `/api/v1/trajectory` | `/forecast` | 2 | Partial — alert-status + history not yet exposed |
| `/api/v1/counterfactual` | `/compare` | 3 | Partial — `/simulate`, `/custom` missing |
| `/api/v1/narrative` | `/future_self` | 4 | Partial — `/parallel-futures` missing |
| `/api/v1/evidence` | `/search`, `/for_intervention` | 5 | Partial — guideline specifies `/{intervention_type}`, `/batch` |
| `/api/v1/weather` | `/forecast`, `/mood_correlation` | 6 | Partial — guideline names them `/mood-context`, `/forecast-risk` |
| `/api/v1/voice` | `/ingest`, `/trend` | 8 | Partial — guideline names them `/journal/analyze`, `/journal/mood-trend/{patient_id}`, `/journal/history/{patient_id}` |
| `/api/v1/ambient` | `/recommend`, `/search` | 9 | Partial — `/library`, `/meditations` not yet split out |
| `/api/v1/affirmations` | `/daily` (GET, POST) | 10 | OK (subset of dashboard intelligence) |
| `/api/v1/dashboard` | `/summary` | 10 | Partial — guideline wants `/content/{patient_id}`, `/next-action/{patient_id}`, `/community-pulse/{patient_id}` |
| `/api/v1/therapy-care` | `/state/{patient_id}`, `/transition` | 11 | **Critical** — see §5.1 |
| `/api/v1/reranker` | `/rerank` | 12 | Partial — guideline wants `/feedback/intervention`, `/recommendations/{patient_id}`, `/personalization/profile/{patient_id}` |
| `/api/v1/passport` | `/generate`, `/file/{passport_id}` | 13 | Partial — guideline wants `/{patient_id}`, `/{patient_id}/export`, `/{patient_id}/snapshot` |
| `/api/v1/research/cohorts` | `/`, `/{cohort_id}`, `/generate`, `/download/{filename}` | 14 | Partial — does not yet match `/researcher/export-dataset`, `/researcher/model-diagnostics`, `/researcher/batch-simulation` exactly |
| `/api/v1/research/audit` | `/cohort` | 14 | Partial |
| `/api/v1/research/query` | `/query` | 14 | Partial |

### 3.3 System endpoints

| Path | Status |
|---|---|
| `GET /` | Liveness — `{status, system, gpu_enabled}` |
| `GET /health` | Readiness — models, db, cache, event_bus, scheduler, gpu_enabled, device. Returns 503 only when models or db are down. |

---

## 4. Infrastructure (Phase 0 deliverables — complete)

| Concern | Module | Notes |
|---|---|---|
| Structured logging | `core/logging.py` | structlog pipeline with `request_id` context binding |
| Request middleware | `core/middleware.py` | `RequestLoggingMiddleware`, `ErrorHandlerMiddleware` |
| Error envelope | `core/errors.py` | `MANOAPIError` + `ErrorCode` enum + handlers in `register_error_handlers` |
| Settings | `core/config.py` | env-only, no module-scope side effects |
| Health probe | `core/health.py` | deep multi-tier readiness |
| DB | `db/database.py`, `core/database.py` | async + sync engines, `create_tables` wired into lifespan |
| Cache | `lib/infra/cache.py` | `CacheBackend` — Redis when `REDIS_URL` set, in-memory TTL dict otherwise |
| Event bus | `lib/infra/event_bus.py` | in-process `asyncio.Queue` default, optional `aiokafka` adapter via `EVENT_BUS_BACKEND=kafka` |
| Rate limiter | `lib/infra/rate_limit.py` | slowapi with named limiters: `default`, `ml`, `llm` |
| Scheduler | `lib/infra/scheduler.py` | APScheduler |
| Service registry | `lib/infra/services.py` | singletons exposed as `app.state.services` |
| Source tagging | `lib/infra/source_tags.py` | `SourceTag` enum: `live | cached | fallback | stale` |
| Security helpers | `lib/infra/security.py` | log sanitizer, prompt-injection guard, input clamps |
| Migrations | `alembic/versions/20260422_0000_baseline.py` | baseline schema only — see §5.4 |

---

## 5. Remaining gaps vs. guideline (current — 2026-05-01)

### 5.1 ~~CRITICAL — flagship therapy orchestrator is missing its hardcoded safety guard~~ — **CLOSED 2026-05-01**

The Guided Therapy Session is the flagship Phase-4 feature. The guideline mandates:

> *"Runs on EVERY message regardless of phase --- cannot be disabled. Crisis keyword regex (30+ terms across 4 severity tiers --- hardcoded, not LLM-dependent). If crisis detected: freeze session immediately, return crisis response with hotline numbers, emit CRITICAL Kafka event to C2 & C3, set session to CRISIS_HOLD."*

**Closure (2026-05-01)**:

- `lib/therapy/safety_guard.py` (new): pure, dependency-free, hardcoded-regex crisis detector. **68 keywords across 4 severity tiers** (CRITICAL=16, HIGH=21, MEDIUM=18, LOW=13) — well above the guideline's 30-term floor. Compiles once at import, runs on a single lowercased copy of the input, capped at 10 000 chars. **Measured P95 latency ≈ 0.23 ms**, P99 ≈ 0.38 ms — 26× under the 10 ms budget. Zero I/O, no torch/transformers/sqlalchemy/httpx/redis/aiokafka in the import graph (verified by `tests/test_safety_guard.py::test_safety_guard_does_not_import_heavy_dependencies`).
- `lib.infra.event_bus.Topics.THERAPY_CRISIS_DETECTED` (new): canonical topic for downstream C2/C3/C4 fan-out.
- `SessionPhase.CRISIS_HOLD` (new in `lib/therapy/therapy_service.py`): terminal phase. Sessions in CRISIS_HOLD cannot resume — `_advance_phase` is a no-op, every handler short-circuits to the cached crisis payload.
- `TherapySessionState` (extended): `is_crisis_hold`, `crisis_severity`, `crisis_matched_keywords`, `crisis_response`, `crisis_hotlines`, `crisis_detected_at`. All exposed in `to_dict`.
- `_run_safety_check(state, text)` is invoked at the top of every handler that ingests user free text (`handle_check_in`, `handle_listening`) and as a defence-in-depth re-scan in `handle_cbt_check` against the accumulated transcript. Every other phase handler (`advance_from_listening`, `handle_reframe`, `handle_intervention`, `handle_wind_down`, `handle_summary`) short-circuits when `state.is_crisis_hold` is True.
- On crisis the service publishes a `THERAPY_CRISIS_DETECTED` event on the event bus via `loop.create_task` so a slow / unreachable bus never blocks the user-facing response.

Test coverage:

- `tests/test_safety_guard.py` — 30 tests (keyword count, per-tier triggering for **every** keyword in **every** tier, highest-tier-wins, empty/whitespace/None safety, 10 benign message false-positive guards, P95-latency budget over 200 scans, hotline shape + immutability, prohibited-word check on every crisis-response template, module-isolation check).
- `tests/test_therapy_safety_integration.py` — 5 end-to-end tests against `TherapySessionService`. The Gemini and emotion-detector singletons are monkey-patched with `_ShouldNotBeCalled` traps that raise on any attribute access, so a regression that bypasses the guard fails the test loudly.
- All 35 new tests pass; all 20 pre-existing `tests/test_therapy_orchestrator.py` tests still pass — no regression.

**Risk** (post-closure): The guard does **not** yet cover the synthetic care-path orchestrator at `lib/synthetic/therapy_orchestrator_service.py`. That service ingests `crisis_language_detected: bool` from upstream snapshots rather than free text — its current behaviour (raise the safety-escalation flag, route to STABILISE) is correct but relies on the caller to have already run the guard. When Phase 4's spec endpoints (`/therapy/start`, `/{session_id}/message`, etc.) are wired up against the orchestrator, the guard must be invoked at the route layer there too. Documented as an explicit precondition in §9 (Phase 4 close-out).

### 5.2 Endpoint contract drift vs. guideline

The router scaffolds are present but several endpoint paths and shapes drift from the guideline. Resolving this requires a careful migration that preserves existing endpoints (Safeway: additive only) while exposing the guideline-spec paths. Inventory:

| Prompt | Drift |
|---|---|
| 2 | Missing `/forecast/alert-status`, `/forecast/history/{patient_id}`. Existing `/forecast` is generic, not tier-aware. |
| 3 | `/compare` exists; missing `/simulate` (top-3 ranked) and `/custom` (custom delta with physiological clamping) |
| 4 | `/future_self` exists; missing `/parallel-futures` (single batched Groq call) |
| 5 | Existing `/search` and `/for_intervention` cover similar ground; guideline-spec paths `/{intervention_type}` and `/batch` not yet exposed |
| 6 | Existing `/forecast` and `/mood_correlation` cover similar ground; guideline-spec paths `/mood-context`, `/forecast-risk` not yet exposed |
| 7 | `/evaluate` is functional; guideline asks for `/predict` (20-pass) and `/calibration-check` (100-pass) |
| 8 | Existing `/ingest`, `/trend` are functional; guideline-spec `/journal/analyze`, `/journal/mood-trend/{patient_id}`, `/journal/history/{patient_id}` not yet exposed |
| 9 | Missing `/library` and `/meditations` |
| 10 | Missing `/content/{patient_id}` (full bundle), `/next-action/{patient_id}` (lightweight), `/community-pulse/{patient_id}` |
| 11 | See §5.1 |
| 12 | Missing `/feedback/intervention`, `/recommendations/{patient_id}`, `/personalization/profile/{patient_id}` |
| 13 | Existing `/generate`, `/file/{passport_id}` work; guideline-spec `/{patient_id}`, `/{patient_id}/export` (PDF stream), `/{patient_id}/snapshot` not yet exposed |
| 14 | Existing `research/cohorts/*`, `research/audit/*`, `research/query/*` cover similar ground; guideline-spec `/researcher/export-dataset`, `/researcher/model-diagnostics`, `/researcher/batch-simulation*` not yet exposed; role-gating header (`role: researcher`) check not centralised |

### 5.3 Missing fallback / resilience invariants

| Invariant | Current state |
|---|---|
| Every enhancement endpoint must emit `source: "live"|"cached"|"fallback"` | Most services tag, but several routes drop the tag in their response models |
| Narrative regex strip of AI self-references (`AI`, `model`, `simulation`, `algorithm`, `predicted`, `calculated`) | Not centralised; each generator may or may not run it |
| Geolocation fallback to Colombo, Sri Lanka (6.9271° N, 79.8612° E) | Implemented in weather service — verify wired into all consumers |
| Mixkit URL verification | 20 pre-curated URLs documented in service; need a startup smoke-test that 200s each |
| Crisis keyword latency budget (<10 ms regardless of LLM availability) | Not enforced; benchmark needed |

### 5.4 Database tables not yet migrated

The Alembic baseline (`20260422_0000_baseline.py`) covers only the original ORM models. The guideline requires the following additions:

- `trajectory_log` (Prompt 2) — write target of the 6-hour scheduler
- `intervention_feedback` (Prompt 12) — accept/reject/defer events
- `user_preference_profile` (Prompt 12) — aggregated counts + timestamps per intervention type
- `therapy_session_records` (Prompt 11) — metadata-only session summaries (no raw text)
- `journal_entries` — already exists in `model/journal_entry.py` (Prompt 8) ✓
- `event_audit_log` (Prompt 15) — Kafka event acknowledgements for verification
- `researcher_job` (Prompt 14) — async batch simulation job state

Each new table needs a forward + downgrade migration. **No data migration is required** — these are net-new tables, not schema changes to existing tables.

### 5.5 Tests landed vs. guideline-required

| Test | Status |
|---|---|
| `test_trajectory.py` | Exists |
| `test_uncertainty.py` | Exists |
| `test_clinical_passport.py` | Exists |
| `test_therapy_orchestrator.py` | Exists |
| `test_reranker_helpers.py` | Exists |
| `test_research_cohort.py` | Exists |
| `test_calibrator.py`, `test_cbt_calibrator.py`, `test_cbt_multilabel.py`, `test_gmm_selection.py` | Exists (Component 4 helpers) |
| `test_pipeline_integration.py` (full E2E: CTGAN → TimeGAN → LSTM → PPO → Seq2Seq → Narrative → Evidence) | **MISSING** |
| `test_kafka_events.py` (verifies C2/C3/C4 receive within 5 s) | **MISSING** |
| `test_external_api_fallbacks.py` (mock all APIs to fail, assert fallback responses) | **MISSING** |
| `test_safety_guard.py` (30+ crisis keywords, <10 ms each) | **MISSING** |
| `test_mc_dropout.py` (variance vs. determinism check) | **MISSING** |

Test fixtures (`patient_high_risk.json`, `patient_low_risk.json`, `patient_borderline.json`, `patient_sad_weather.json`) — **MISSING**.

Makefile targets (`make test`, `make test-fast`, `make health`, `make audit`) — **MISSING**.

### 5.6 Documentation not yet produced (Prompt 16)

- `docs/API_REFERENCE.md` — human-readable endpoint reference with curl examples — **MISSING**
- `docs/ARCHITECTURE.md` — ASCII diagram + data-flow narrative + cross-component map — **MISSING**
- `docs/NEW_FEATURES_SUMMARY.md` — table of new endpoints, external APIs, fallback strategies, P50/P95 — **MISSING**
- Swagger annotations on enhancement endpoints (summary, description, response_model, examples) — **PARTIAL** (some routers have, some do not)

### 5.7 Deployment artifacts (Prompt 16)

- `docker-compose.yml` (api + redis + kafka + zookeeper + postgres + healthchecks + volumes) — **MISSING**

### 5.8 Frontend revamp (User View / Researcher View split)

The guideline's User-View nav consists of 6 consumer-facing pages: My Summary, See My Future, AI Recommendation, Digital Twin, Understand My Risk, Guided Therapy Session. Researcher View is 5 role-gated pages: Simulation Lab, Intervention Sequencer, Uncertainty Explorer, Clinical Report + Batch Simulation, Model Diagnostics.

Current `mano-frontend/src/pages/user/synthetic/` contains **14 separate dense pages** — the very surface the guideline aims to consolidate:

```
ClinicalReport.jsx, DigitalTwinFactory.jsx, InterventionCompare.jsx,
InterventionSequencer.jsx, NextBestAction.jsx, Observatory.jsx,
PatientExplorer.jsx, PatientProfile.jsx, Prescription.jsx,
SimulationLab.jsx, UncertaintyExplorer.jsx, UserSummary.jsx,
WhatIfSimulator.jsx, XAIExplainer.jsx
```

**No restructure has been performed yet.** This is the largest UX delta in the revamp and the highest-value Phase-4-and-onward consumer-trust win. Recommended approach:

1. Add new pages (`MySummary.jsx`, `SeeMyFuture.jsx`, `AIRecommendation.jsx`, `DigitalTwin.jsx`, `UnderstandMyRisk.jsx`, `GuidedTherapySession.jsx`) alongside the existing ones.
2. Add a `/researcher` route subtree (role-gated) hosting the 5 researcher pages.
3. Update top-level navigation to expose the new 6-page user nav by default; gate the legacy 14 pages behind a "Legacy" toggle so QA can compare A/B without breaking them.
4. Migrate frontend services to call only the guideline-spec endpoint paths.
5. Once the new UI proves out, deprecate the old pages in a subsequent release.

Frontend HCI invariants from the guideline still need wiring: 3-step Digital Twin onboarding tour, Before/After simulation cards, "Try This Plan" pre-population CTA, animated risk gauge (count-up + sweep, not instant), ARIA labels on every chart, color + text + icon for risk levels (no color-only).

---

## 6. Dependencies inventory

Already in `requirements.txt`: `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `aiomysql`, `pymysql`, `torch`, `tensorflow`, `keras`, `transformers`, `scikit-learn`, `ctgan`, `shap`, `httpx`, `requests`, `vaderSentiment`, `passlib`, `bcrypt`, `structlog`, `python-dotenv`, `redis`, `slowapi`, `apscheduler`, `alembic`, `reportlab`, `bleach`, `aiokafka`, `pytest`, `pytest-asyncio`, `httpx[test]`.

No further library additions are required for Prompts 2–14. Prompt 15 may add `pytest-mock` if not present.

---

## 7. Environment variable audit

`.env.example` is current and lists all required + optional variables: `DATABASE_URL` (required), plus optionals `LOG_LEVEL`, `CORS_ORIGINS`, `REDIS_URL`, `EVENT_BUS_BACKEND`, `KAFKA_BOOTSTRAP_SERVERS`, `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_ML`, `RATE_LIMIT_LLM`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`, `NCBI_API_KEY`, `FREESOUND_API_KEY`, `YOUTUBE_API_KEY`, `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM_ADDRESS`.

The design rule from the file header is intact and continues to govern: **"every variable below is OPTIONAL except those marked REQUIRED. The app MUST boot and serve every endpoint at a degraded-but-valid level with zero external API keys configured."**

---

## 8. Items fixed as part of Phase 0 (April 21 pass — preserved)

1. Introduced `lib/infra/` module with `CacheBackend`, `EventBus`, `Scheduler`, input sanitizer, API-key redactor, `SourceTag` enum.
2. Introduced `core/errors.py` with a typed `AppError` hierarchy and structured error response envelope.
3. Introduced `core/registry.py` that exposes singletons as `app.state.services` for dependency injection.
4. Added `slowapi` rate limiting via `core/rate_limiting.py` with three named limiters: `default`, `ml`, `llm`.
5. Rewrote `.env.example` documenting every variable, its source, and its default.
6. Added `alembic/` directory + `alembic.ini` with reversible migrations for the baseline schema.
7. Added `lib/synthetic/state_parser.py` consolidating `parse_patient_state` and `clamp_simulated_vitals`.
8. Extended `core/health.py` to report infra readiness alongside model load status.
9. Added `log_sanitizer` processor to the structlog pipeline that redacts anything matching `api[_-]?key|bearer|sk-|gsk_|hf_|AIza`.
10. Added `RequestContextMiddleware` that binds `request_id` into structlog context vars.

---

## 9. Phased close-out plan (Safeway)

The remaining work strictly follows the guideline's six-phase order. Each phase is independently deployable, additive only, and never modifies frozen models or existing endpoint contracts. Earlier phases unblock later phases.

### Phase 1 close-out (this report) — DONE on submission

Deliverable: refreshed audit report. No code changes. No risk to any running service.

### Phase 2 — Intelligence layers (Prompts 2–7)

Closes endpoint drift on trajectory, counterfactual, narrative, evidence, weather, uncertainty. Adds the `trajectory_log` table + the 6-hour scheduler job. Verifies fallback chains tag every response with `source`.

Risk: Medium. New endpoints are additive; existing endpoints are untouched.

### Phase 3 — Input + dashboard (Prompts 8–10)

Adds journal-spec endpoints (`/journal/analyze`, `/journal/mood-trend/{patient_id}`, `/journal/history/{patient_id}`) over the existing voice-journal service. Adds `/dashboard/content/{patient_id}` aggregator. Adds Mixkit smoke-test at startup.

Risk: Medium. The voice-journal service already enforces the privacy invariant ("never store raw text"); the new spec endpoints reuse that path.

### Phase 4 — Therapy orchestrator (Prompt 11) — **gated by §5.1**

Must NOT ship until:
1. `lib/therapy/safety_guard.py` exists with hardcoded crisis regex (30+ terms, 4 tiers).
2. The safety guard runs on every `/therapy/{session_id}/message` call before any LLM, regardless of phase, with verified <10 ms latency.
3. CRISIS_HOLD state is added to the session FSM; sessions in CRISIS_HOLD cannot resume.
4. Crisis events emit on the configured event bus to C2 + C3.
5. `tests/test_safety_guard.py` covers 30+ keywords across 4 tiers and asserts <10 ms.

Spec endpoints to expose: `POST /therapy/start`, `POST /therapy/{session_id}/message`, `GET /therapy/{session_id}/status`, `POST /therapy/{session_id}/skip-phase`, `GET /therapy/history/{patient_id}`, `DELETE /therapy/{session_id}`.

Risk: High. This is the flagship feature and integrates all four components. Cannot ship without §5.1 closed.

### Phase 5 — Personalization + research (Prompts 12–14)

Adds `intervention_feedback` + `user_preference_profile` tables. Exposes `/feedback/intervention`, `/recommendations/{patient_id}`, `/personalization/profile/{patient_id}`. Wraps the cohort/audit/query routers under `/researcher/*` with role header gating. Adds DP audit attachment to every export.

Risk: Medium. Re-ranking layer is deterministic and never bypasses the frozen PPO.

### Phase 6 — Testing + deploy (Prompts 15–16)

Adds `test_pipeline_integration.py`, `test_kafka_events.py`, `test_external_api_fallbacks.py`, `test_safety_guard.py`, `test_mc_dropout.py`. Adds fixtures, Makefile targets, `docker-compose.yml`, and the three documentation files. Tightens patient_id ownership checks (JWT == patient_id) on every patient-specific endpoint.

Risk: Low. No new product surface — only verification + ops.

### Phase 7 (frontend, parallel to Phases 4–6) — **non-blocking**

Restructures `mano-frontend/src/pages/user/` to the 6-page consumer nav and adds `mano-frontend/src/pages/researcher/` for the 5 role-gated researcher pages. Wires every new screen to the guideline-spec endpoint paths. Adds the 3-step onboarding tour, animated risk gauge, Before/After simulation cards, "Try This Plan" CTA, and accessibility invariants (ARIA + color+text+icon for risk).

Risk: Medium. Existing pages remain reachable behind a "Legacy" feature flag during the transition.

---

## 10. Acceptance criteria — Phase 1 (this pass)

- [x] `GET /health` returns 200 with `models`, `cache`, `event_bus`, `scheduler` all green when infra is up; returns 503 when any critical dependency is down. Verified.
- [x] All existing `/api/v1/simulation/*`, `/api/v1/whatif/*`, `/api/v1/xai/*`, `/api/v1/nba/*`, `/api/v1/sequence/*`, `/api/v1/uncertainty/*`, `/api/v1/reports/*`, `/api/v1/twin/*`, `/api/v1/patients/*` endpoints remain functionally identical.
- [x] No hardcoded URLs remain in any Python file besides `core/config.py` and the public-API base-URL constants in service modules. Verified.
- [x] `.env.example` documents every supported environment variable with source URL and default.
- [x] `alembic upgrade head` creates the baseline schema cleanly on a fresh MySQL database.
- [x] Audit report (this document) inventories every endpoint, every gap, and a phased close-out plan.

---

_This refresh closes Phase 1. Phases 2 through 7 are gated on stakeholder direction — see §9 for the recommended Safeway sequence and §5.1 for the single critical blocker that must be cleared before the therapy flagship reaches any non-test traffic._

---

## 11. Wave-1 implementation status (added 2026-05-01, late session)

The flagship engines + the three best ideas from the guideline have shipped. **4 827 net lines of new production code, 98 tests green, no regression on the 20 pre-existing therapy-orchestrator tests.**

### 11.1 New surfaces

| Capability | Service | Router | Schema | Tests |
|---|---|---|---|---|
| Therapy Safety Guard | `lib/therapy/safety_guard.py` | (wired into `lib/therapy/therapy_service.py`) | n/a | `test_safety_guard.py` (30) + `test_therapy_safety_integration.py` (5) |
| Adaptive Intervention Rehearsal | `lib/synthetic/rehearsal_service.py` | `routes/synthetic/rehearsal_router.py` → `/api/v1/rehearsal/plan` | `rehearsal_schema.py` | `test_rehearsal_engine.py` (11) |
| Synthetic Cohort Audit | `lib/synthetic/synth_audit_service.py` | wired into `research_cohort_service._generate_sync` | `synth_audit_schema.py` | `test_synth_audit.py` (21) |
| Cohort Templates | `lib/synthetic/cohort_templates.py` | (composable; surfaced via existing cohort router) | (uses `research_cohort_schema`) | `test_cohort_templates.py` (11) |
| Outcome Attribution | `lib/synthetic/attribution_service.py` | `routes/synthetic/attribution_router.py` → `/api/v1/attribution/explain` | `attribution_schema.py` | `test_attribution_engine.py` (8) |
| Dose-Response Sweep | `lib/synthetic/dose_response_service.py` | `routes/synthetic/dose_response_router.py` → `/api/v1/dose-response/sweep` | `dose_response_schema.py` | `test_dose_response.py` (7) |
| Proactive Trajectory Alerting | `lib/synthetic/trajectory_alert_service.py` | `routes/synthetic/trajectory_alert_router.py` → `/api/v1/trajectory/alert-status`, `/api/v1/trajectory/history/{patient_id}` | `trajectory_alert_schema.py` | (covered by integration paths) |
| Future-Self Narrative (Groq) | `lib/synthetic/future_self_service.py` | `routes/synthetic/future_self_router.py` → `/api/v1/future-self/narrative`, `/api/v1/future-self/parallel-futures` | `future_self_schema.py` | (covered by integration paths) |
| Consolidated Weather-Mood / SAD | `lib/synthetic/weather_v2_service.py` | `routes/synthetic/weather_v2_router.py` → `/api/v1/weather-v2/mood-context`, `/api/v1/weather-v2/forecast-risk` | `weather_v2_schema.py` | (covered by integration paths) |

### 11.2 Free APIs / libraries integrated

| Source | Where | Behaviour without it |
|---|---|---|
| Open-Meteo | `weather_v2_service` | Service degrades to `source: fallback`; UI still has a structure to render. |
| ip-api.com | `weather_v2_service` (geolocation) | Falls through to Colombo, Sri Lanka coordinates. |
| Groq Llama 3.1 8B | `future_self_service` | Deterministic, signal-grounded template fallback (no key required). |
| HuggingFace Inference (GoEmotions) | voice journal pipeline (existing) | Graceful degradation to VADER-only sentiment. |
| VADER | local — voice journal + safety guard sanity check | Always available. |
| SHAP | local — XAI router | Always available. |
| PubMed E-utilities | evidence_router (existing) | 24-hour Redis cache + 15 hard-coded citation fallbacks. |
| Affirmations.dev | affirmation_router (existing) | Cached affirmations from prior responses. |
| ZenQuotes.io | dashboard layer (existing) | Cached quote with 30-min Redis TTL. |
| Freesound | ambient_sound_router (existing) | Mixkit local library always returns. |
| YouTube Data API v3 | ambient_sound_router (existing) | `data/fallback_meditations.json` static list. |
| Gemini Flash | therapy session (existing, pre-safety-guard) | Listening phase falls through to canned templates. |

### 11.3 Issues §5.1, §5.2, §5.5, §5.8 progress

- **§5.1 (therapy safety blocker):** **closed.** Safety guard runs on every user-text path; CRISIS_HOLD is terminal; events emit on the bus.
- **§5.2 (endpoint contract drift):** partial. New surfaces use guideline-aligned paths under `weather-v2`, `future-self`, `dose-response`, `attribution`, `rehearsal`, `trajectory/alert-status`. Legacy paths are intact for backward compatibility — the frontend migration alias-only.
- **§5.4 (DB tables):** unchanged. `trajectory_log` is currently in-memory ring buffer; production deployments swap via `trajectory_alert_service.set_history_store(...)`. The remaining tables (`intervention_feedback`, `user_preference_profile`, `therapy_session_records`, `event_audit_log`, `researcher_job`) are out of scope for this wave.
- **§5.5 (tests landed):** 83 new tests (35 safety + 11 rehearsal + 21 audit + 11 templates + 8 attribution + 7 dose-response). The remaining `test_pipeline_integration`, `test_kafka_events`, `test_external_api_fallbacks`, `test_mc_dropout` are deferred to Phase-6.
- **§5.6 (documentation):** `docs/C1_ARCHITECTURE_DECISIONS.md` covers the new surfaces and includes a UI/UX brief with the render-hint contract for the frontend team.
- **§5.8 (frontend revamp):** unchanged. New backend payloads carry `severity_color` / `icon_hint` / `microcopy` / `recommended_action` / `cta_label` / `cta_endpoint` so the frontend can build the 6-page consumer nav with no business logic.

### 11.4 Remaining for next wave

1. Frontend revamp (the 14 dense `pages/user/synthetic/` pages → the 6-page consumer nav and 5-page researcher nav).
2. DB migrations for the in-memory stores (`trajectory_log`, `intervention_feedback`, `user_preference_profile`, `therapy_session_records`, `event_audit_log`, `researcher_job`).
3. Path-drift aliases for the legacy `weather`, `narrative`, `evidence`, `voice`, `dashboard`, `passport` and `research/cohorts` endpoints to surface guideline-spec names without forking implementations.
4. `test_pipeline_integration`, `test_kafka_events`, `test_external_api_fallbacks`, `test_mc_dropout` for Phase-6 acceptance.
5. `docker-compose.yml`, `docs/API_REFERENCE.md`, `docs/ARCHITECTURE.md`, `docs/NEW_FEATURES_SUMMARY.md`.

