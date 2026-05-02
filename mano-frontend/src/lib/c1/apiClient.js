/**
 * Component-1 API client — thin wrapper around the existing api/client.js
 * that targets the new bundled-page endpoints.
 *
 * Each function here corresponds to one consumer-view page. The frontend
 * issues exactly ONE call per page, not five.
 */

import { request } from '../../api/client';

// Helper: POST or GET to /api/v1/<path>. The shared `request` already
// prepends /api/v1.
function post(path, body) {
    return request(path, { method: 'POST', body: JSON.stringify(body) });
}

function get(path) {
    return request(path, { method: 'GET' });
}

// ── Page bundles ────────────────────────────────────────────────────────

export function fetchMySummary({ patient_id, patient_state, user_name, lat, lon }) {
    return post('/summary/bundle', { patient_id, patient_state, user_name, lat, lon });
}

export function fetchSeeMyFuture({ patient_state, lat, lon, arms = null }) {
    return post('/see-my-future/preview', { patient_state, lat, lon, arms });
}

export function fetchAIRecommendation({ patient_state, prefill_arm = null }) {
    return post('/recommendation/bundle', { patient_state, prefill_arm });
}

export function fetchDigitalTwin() {
    return get('/digital-twin/bundle');
}

export function fetchUnderstandMyRisk({ patient_state }) {
    return post('/understand-my-risk/bundle', { patient_state });
}

export function fetchGuidedTherapyEntry() {
    return get('/guided-therapy/bundle');
}

// ── Standalone engines (used by Researcher View pages) ──────────────────

export function rehearsePlan(payload) {
    return post('/rehearsal/plan', payload);
}

export function explainAttribution(payload) {
    return post('/attribution/explain', payload);
}

export function sweepDoseResponse(payload) {
    return post('/dose-response/sweep', payload);
}

export function trajectoryAlertHistory(patientId, lookback = 30) {
    return get(`/trajectory/history/${encodeURIComponent(patientId)}?days_lookback=${lookback}`);
}

export function generateCohort(payload) {
    return post('/research/cohorts/generate', payload);
}

export function listCohorts() {
    return get('/research/cohorts');
}

export function generateNarrative(payload) {
    return post('/future-self/narrative', payload);
}

export function parallelFutures(payload) {
    return post('/future-self/parallel-futures', payload);
}
