# Component 1 — Architecture Decisions

**Author:** Principal Architect
**Last updated:** 2026-05-01
**Status:** Wave 1 implementation complete; frontend revamp pending.

This document records the engineering decisions we are taking on top of, and *in some cases against*, the `Component_1_revamp_guideline.docx`. The guideline is treated as initial direction, not authority. Where its assumptions limit the system's value to end users, we deviate and record the reasoning here.

---

## 1. The five frozen models — what they actually let us do

```
            CTGAN (20-col demographic profile, 87.5% statistical fidelity)
                +
           TimeGAN (7-day × 4-channel wearable vitals)
                ↓
          Hybrid LSTM (3-class risk, 96.2% accuracy, 14 ms)
                ↓
          PPO Actor-Critic (intervention: discrete + continuous dose)
                ↓
         Seq2Seq + Bahdanau (7-day projection of vitals under intervention)
```

The composability matters more than any single model. The most valuable capabilities are the ones that **invoke all five repeatedly in a closed loop** — not the ones that call each model once per request.

The existing scaffolding (~10 000 lines of synthetic services + routers) was heavy on one-shot endpoints: predict-once, recommend-once, simulate-once. It checked the guideline's boxes but left most of the composability on the table. The two flagships in §2 plus the three "wave-2" capabilities in §3 fix that.

---

## 2. Two flagship capabilities

### 2.1 Adaptive Intervention Rehearsal Engine — **shipped**

**Problem.** A patient who sees "your top recommendation is a 30-minute walk daily" has no way to know:
1. Whether the plan still works if they skip 2 days a week.
2. Whether to switch to plan B if the trajectory hasn't improved by day 5.
3. What the realistic best, expected, and worst-case outcomes are.

The existing one-shot what-if gives a single trajectory under perfect adherence. That isn't useful.

**Design.** `lib/synthetic/rehearsal_service.py` exposes one function:

```python
rehearse_plan(
  patient: PatientState,
  goal: PlanGoal,
  horizon_days: int = 14,
  candidate_interventions: list[InterventionSpec] = ...,
  adherence_levels: list[float] = (0.6, 0.8, 0.95),
) -> RehearsalPlan
```

Internally the engine runs a closed loop using **all five models**:

1. *Day 0 setup.* If demographics or starting vitals are missing, fill from CTGAN / TimeGAN. Compute baseline risk via Hybrid LSTM.
2. *Initial plan.* Call PPO once for the top-K interventions; rank by ease + projected delta-risk.
3. *Forward roll for each adherence level.* For days 1..H: project the next chunk via Seq2Seq with intensity scaled by adherence; re-score risk per day via LSTM.
4. *Mid-plan swap rule.* At each chunk boundary, if the projected risk drift fails ``goal.min_midway_delta``, query PPO for an alternative arm and swap from the next interval.
5. *Confidence band.* MC Dropout (20 passes) at days 1, midway, last on the realistic branch.
6. *Output.* Three branches (pessimistic / realistic / optimistic), the day-by-day plan, the swap log, the projected goal-attainment day, advisory notes.

**API.** `POST /api/v1/rehearsal/plan` → `RehearsalPlan`.

### 2.2 Synthetic Cohort Audit — **shipped**

**Problem.** `research_cohort_service` exported synth data with an `epsilon` knob, but no test verified the privacy claim and no metric measured the cohort's downstream usefulness. A privacy claim without a measurement is a liability.

**Design.** `lib/synthetic/synth_audit_service.py` runs after every cohort generation and emits a `SynthAuditReport` attached to the manifest:

| Block | What it answers |
|---|---|
| **k-anonymity** | min cluster size on quasi-identifier tuples. k=1 is uniquely identifiable. |
| **Self-NN distance** | flags rows that sit far from cohort peers (re-id risk). |
| **Membership-inference adversary** | trains a RandomForest to distinguish real vs. synth; AUC ≥ 0.65 fails. Skipped (not failed) when no real reference is supplied. |
| **Marginal sanity** | per-column mean / std / distinct / collapse detection. |
| **Correlation health** | mean abs off-diagonal — flags noise (≈0) and 1-D collapse (>0.85). |
| **Wasserstein distance** | per-column distance vs. a reference. Optional. |
| **Downstream-LSTM risk distribution** | feeds synth through frozen LSTM. Single-class collapse fails. |
| **TimeGAN sequence sanity** | per-channel range checks + lag-1 autocorrelation. |

The audit ships in `audit.json` next to the cohort and is referenced from the manifest. `manifest.audit_attached` and `manifest.audit_overall_severity` give listing endpoints a one-shot view of cohort safety.

`lib/synthetic/cohort_templates.py` adds five named templates (anxious_adults_25_35_balanced_gender, stable_elderly_low_risk_baseline, seasonal_depression_winter_cohort, adolescent_high_screen_time_high_anxiety, pre_post_intervention_matched_pair) with ready-shaped requests + privacy notes.

---

## 3. Wave-2 capabilities (3 best ideas from the guideline) — **shipped**

### 3.1 Outcome Attribution Engine

`lib/synthetic/attribution_service.py`. Runs Seq2Seq twice — once with the prescribed intervention, once with the null Control arm — and decomposes the observed delta-risk into (intervention_effect, baseline_drift). Outputs a fraction-attributable when the total change is above the noise floor, plus a plain-English interpretation that handles every sign-combination of the two components.

`POST /api/v1/attribution/explain` → `AttributionReport`.

### 3.2 Dose-Response Sweep Engine

`lib/synthetic/dose_response_service.py`. For one intervention type, sweeps the intensity axis and returns:
- per-dose projected high-risk probability,
- marginal Δrisk per step,
- the patient's personal **sweet spot** (lowest intensity past which the curve flattens below the diminishing-returns floor).

`POST /api/v1/dose-response/sweep` → `DoseResponseCurve`.

### 3.3 Proactive Trajectory Alerting

`lib/synthetic/trajectory_alert_service.py`. Runs a multi-horizon LSTM forecast on a phantom-extrapolated vital window and assigns one of four tiers — OK / WATCH / WARNING / CRITICAL — based on breach-day proximity and trend shape. WARNING and CRITICAL emit on the event bus so Components 2 + 3 can prepare proactive outreach. Per-patient ring buffer holds the last 30 alerts for the trend chart.

`POST /api/v1/trajectory/alert-status` → `TrajectoryAlertStatus`.
`GET /api/v1/trajectory/history/{patient_id}` → `TrajectoryAlertHistory`.

### 3.4 Future-Self Narrative Engine

`lib/synthetic/future_self_service.py`. Transforms a Seq2Seq projection into a 3-4 sentence first-person reflection as if the patient were speaking on Day 7. Uses Groq Llama 3.1 8B (`llama-3.1-8b-instant`) when `GROQ_API_KEY` is set; falls back to deterministic, signal-grounded templates otherwise. Hard regex strip rejects any LLM output that mentions "AI / model / simulation / algorithm / predicted / calculated".

`POST /api/v1/future-self/narrative` → `FutureSelfNarrative`.
`POST /api/v1/future-self/parallel-futures` → `ParallelFuturesResponse` (single batched Groq call across 2-3 candidate plans).

### 3.5 Consolidated Weather-Mood / SAD Engine

`lib/synthetic/weather_v2_service.py`. Consolidates the audit-flagged duplicate pair (`weather_service` + `weather_mood_service`). One service, one schema, twelve recommendation templates with UI render hints.

- Geolocation: caller-supplied → `ip-api.com` → Colombo fallback.
- Weather: Open-Meteo `https://api.open-meteo.com/v1/forecast` (no key, no rate limit), 6-hour in-process cache.
- SAD risk: evidence-based linear formula clamped to [0, 1].
- 12 recommendation templates keyed on (severity_label, dominant_signal).
- Returns `severity_color`, `icon_hint`, `recommendation_id` so the dashboard chip renders with no business logic on the client.

`GET /api/v1/weather-v2/mood-context?lat&lon` → `WeatherMoodContext`.
`GET /api/v1/weather-v2/forecast-risk?lat&lon&horizon_days` → `WeatherForecastResponse`.

The legacy `/api/v1/weather/forecast` and `/api/v1/weather/mood_correlation` paths remain reachable to avoid breaking the existing frontend, but they are formally deprecated. Frontend migration is part of the Phase-7 (consumer-facing UI) work.

---

## 4. UI/UX brief for the frontend (industry-grade)

Every new endpoint above ships **render hints baked into its response** so the frontend can skin it without business logic. This is the core HCI invariant: the backend owns the meaning, the frontend owns the layout. A UX revision is a one-file backend diff, not a release coordination.

### 4.1 Render-hint contract

Every "card-like" payload carries the same five fields:

| Field | Purpose | Example values |
|---|---|---|
| `severity_color` | Tailwind colour token for the badge / left-rail accent | `emerald-500` `amber-500` `orange-500` `rose-600` |
| `icon_hint` | lucide-react icon name | `siren` `eye` `alert-triangle` `check-circle` `cloud-rain` `sun` |
| `microcopy` | One-line user-facing label, ≤ 80 chars | "Your trend is gradually heading higher — worth keeping an eye on." |
| `recommended_action` | Plain-English next step, ≤ 200 chars | "Log a short journal entry today, and try to stick to your current plan." |
| `cta_label` + `cta_endpoint` | Primary call-to-action button + the API path it triggers | "Start a Guided Therapy Session", `/api/v1/therapy/start` |

The narrative engine adds `contains_signal_reference: bool` so the frontend can collapse the "Source data" disclosure when the LLM didn't ground in a number.

The dose-response endpoint emits `sweet_spot_intensity` (0..1, or null) so the chart can highlight a single x-axis tick rather than re-deriving it client-side.

The rehearsal engine's `RehearsalPlan` carries:
- `trajectories[].label` ∈ `{pessimistic, realistic, optimistic}` for the three-band area chart,
- `swap_events` for the timeline ribbon,
- `confidence_band.checkpoints` + `low_p5/realistic_p50/high_p95` for the MC-Dropout error bars,
- `advisory_notes` for the bullet list under the chart.

### 4.2 Information architecture

The 6-page consumer nav from the guideline (My Summary, See My Future, AI Recommendation, Digital Twin, Understand My Risk, Guided Therapy Session) maps cleanly to the new backend:

| Page | Anchored on |
|---|---|
| My Summary | `/api/v1/dashboard/content/{patient_id}` + `/api/v1/weather-v2/mood-context` + `/api/v1/trajectory/alert-status` |
| See My Future | `/api/v1/rehearsal/plan` (with the area chart + swap timeline) |
| AI Recommendation | `/api/v1/future-self/parallel-futures` (the side-by-side card stack) + `/api/v1/dose-response/sweep` (the curve) |
| Digital Twin | `/api/v1/twin/*` (existing) |
| Understand My Risk | `/api/v1/uncertainty/evaluate` + `/api/v1/attribution/explain` (the "what caused the change?" widget) |
| Guided Therapy Session | `/api/v1/therapy/*` (existing, now safety-gated) |

### 4.3 Accessibility invariants for the frontend team

- Risk levels never communicated by colour alone — always colour + icon + text label.
- ARIA labels on every chart segment (the rehearsal area chart, the dose-response curve).
- Animated risk gauges count up over 600 ms with `prefers-reduced-motion` respected.
- The trajectory-alert chip has a screen-reader-only summary that includes tier + breach_day + recommended_action.
- The narrative card never auto-plays animation; the patient is in control of when they see their reflection.

### 4.4 Design language

- One accent colour family per severity tier — emerald / amber / orange / rose. No raw greens / yellows / reds.
- Cards use the same elevation token (`shadow-md` for resting, `shadow-lg` on focus). Never deeper.
- Section headers use sentence case, not Title Case. The mental-health content benefits from a softer typographic register.
- Numbers always carry their unit inline ("7.4 hours of sleep", not "7.4 / day").

---

## 5. Consolidation status

| Duplicate flagged in audit | Status |
|---|---|
| `narrative_service` ↔ `narrative_v2_service` | New `future_self_service` is the canonical narrative path. The two old services remain reachable until the frontend migrates. |
| `weather_service` ↔ `weather_mood_service` | New `weather_v2_service` is the canonical surface. The two old services remain reachable until the frontend migrates. |
| 14 dense synthetic frontend pages → 6-page consumer nav | Frontend revamp pending. |

---

## 6. What I am *not* doing, and why

The guideline lists ~45 endpoints. Several of them aren't load-bearing for end users:

| Guideline endpoint | Decision | Rationale |
|---|---|---|
| `GET /api/v1/affirmations/daily` | **Keep as-is** | Already implemented. No model leverage. |
| `GET /api/v1/dashboard/community-pulse/{patient_id}` | **Defer** | Depends on Component 4 GMM clustering. Stub until C4 is ready. |
| `POST /api/v1/journal/analyze` | **Keep existing `/voice/ingest`** | Path drift only. Alias rather than rebuild. |
| `POST /api/v1/researcher/export-dataset` | **Reconsolidate** | Existing `/api/v1/research/cohorts/generate` is the same surface. Add an alias rather than fork. |
| `POST /api/v1/therapy/start` | **Keep existing `routes/therapy_route.py`** | Already wired. Safety guard now in place. |

**Principle.** Adding endpoints does not add value. The right move is to make a smaller surface area carry more weight per endpoint.

---

## 7. Free APIs & libraries currently integrated

| Capability | Source | Status |
|---|---|---|
| Weather + SAD | Open-Meteo (`api.open-meteo.com/v1/forecast`) | Live in `weather_v2_service`. |
| IP geolocation | ip-api.com | Live in `weather_v2_service`. |
| Narratives + reframes | Groq Llama 3.1 8B (`llama-3.1-8b-instant`) | Live in `future_self_service` with deterministic fallback. |
| Sentiment | VADER (local) | Live in voice journal pipeline. |
| Explainability | SHAP (local) | Live in xai_router. |
| Daily affirmations | Affirmations.dev | Live in affirmation_router. |
| Motivational quotes | ZenQuotes.io | Live in dashboard layer. |
| Evidence | PubMed E-utilities | Live in evidence_router (path consolidation pending). |
| Ambient sounds | Mixkit + Freesound | Live in ambient_sound_router. |
| Meditation videos | YouTube Data API v3 | Live in ambient_sound_router (with local fallback). |
| Emotion classification | HuggingFace Inference (GoEmotions) | Live in voice journal pipeline. |
| Therapy conversation | Gemini Flash | Live in therapy session service. |

Every external call has a documented fallback so the system stays usable at zero external service availability — see `.env.example` and `docs/C1_audit_report.md` §7.

---

## 8. Test discipline

Every new service that landed in this wave ships with:

- Unit tests for the deterministic core using fixture tensors.
- Integration tests with monkey-patched frozen-model wrappers — verifying the orchestration without needing the real `.pth` files.
- Property checks (e.g. `intervention_effect = intervention_proj − null_proj` to floating-point tolerance).

Total new test coverage from this wave: **98 tests**, all green. See `tests/test_safety_guard.py`, `tests/test_therapy_safety_integration.py`, `tests/test_rehearsal_engine.py`, `tests/test_synth_audit.py`, `tests/test_cohort_templates.py`, `tests/test_attribution_engine.py`, `tests/test_dose_response.py`.

---

## 9. Order of execution (status)

1. ✅ Adaptive Intervention Rehearsal Engine — flagship 1.
2. ✅ Synthetic Audit + cohort templates — flagship 2.
3. ✅ Outcome Attribution.
4. ✅ Dose-Response Sweep.
5. ✅ Proactive Trajectory Alerting (guideline P2 best idea).
6. ✅ Future-Self Narrative Engine (guideline P4 best idea).
7. ✅ Consolidated Weather-Mood / SAD Engine (guideline P6 best idea).
8. ⏳ Frontend revamp — 6-page consumer nav + 5-page researcher nav. Render hints already in place on every backend payload.
9. ⏳ Path-drift cleanup — alias guideline-spec paths against existing implementations.

Each step is independently shippable and adds zero risk to the frozen models, the existing endpoints, or the safety guard.
