/* ============================================================
   MANO AMISE — Backend API Client
   
   All API calls go through this module. Provides optimistic
   error handling and consistent response formatting.
   ============================================================ */

import { API_BASE_URL, TOKEN_KEY } from '../config/constants';

const API_BASE = `${API_BASE_URL}/api/v1`;

/**
 * Core fetch wrapper with error handling.
 * Returns { data, error } — never throws.
 */
export async function request(endpoint, options = {}) {
    return requestTo(`${API_BASE}${endpoint}`, options);
}

/** Same as request() but hits the bare API root (no /api/v1 prefix). */
export async function requestRoot(endpoint, options = {}) {
    return requestTo(`${API_BASE_URL}${endpoint}`, options);
}

async function requestTo(url, options = {}) {
    try {
        const token = localStorage.getItem(TOKEN_KEY);
        const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...authHeaders, ...options.headers },
            ...options,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            // Backend wraps errors as { error: { code, message } } OR { detail }
            const errorMsg = err.error?.message || err.detail || `HTTP ${response.status}`;
            return { data: null, error: errorMsg };
        }

        // Handle 204 No Content
        if (response.status === 204) return { data: null, error: null };

        const data = await response.json();
        return { data, error: null };
    } catch (err) {
        return { data: null, error: err.message || 'Network error' };
    }
}

// ─── Health ─────────────────────────────────────────
export const getHealth = () =>
    request('/health', { method: 'GET' });

// ─── Activities ─────────────────────────────────────
export const getActivityCategories = () =>
    requestRoot('/activity/categories', { method: 'GET' });

export const getActivityDetails = (activityId) =>
    requestRoot(`/activity/details/${activityId}`, { method: 'GET' });

// Component 4 enhancements (backwards-compatible query toggles):
//   with_uncertainty           — emit MC-Dropout uncertainty per recommendation
//   with_cold_start_fallback   — apply population-prior cold-start when signal is thin
//   diversity_lambda           — MMR rerank weight (1.0 = pure relevance, lower = more diverse)
//   diversity_top_k            — how many top results to apply MMR to
// FastAPI ignores unknown query params, so these are safe to pass even if a route
// hasn't been updated yet to forward them to the predictor.
const recommendationQueryParams = (opts = {}) => {
    const {
        with_uncertainty = true,
        with_cold_start_fallback = true,
        diversity_lambda = 0.7,
        diversity_top_k = 20,
    } = opts;
    const qs = new URLSearchParams({
        with_uncertainty: String(with_uncertainty),
        with_cold_start_fallback: String(with_cold_start_fallback),
        diversity_lambda: String(diversity_lambda),
        diversity_top_k: String(diversity_top_k),
    });
    return qs.toString();
};

export const getUserActivities = (userId, opts = {}) =>
    requestRoot(`/activity/${userId}?${recommendationQueryParams(opts)}`, { method: 'GET' });

export const getUserActivitiesByCategory = (userId, category, opts = {}) =>
    requestRoot(
        `/activity/${userId}/category/${category}?${recommendationQueryParams(opts)}`,
        { method: 'GET' },
    );

export const getCompletedActivities = (userId) =>
    requestRoot(`/activity/completed/${userId}`, { method: 'GET' });

export const completeActivity = (userId, activityId) =>
    requestRoot(`/activity/complete/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ activity_id: activityId }),
    });

// ─── Activity Feedback ─────────────────────────────
export const submitActivityFeedback = (userId, feedback) =>
    requestRoot(`/activity/feedback/${userId}`, {
        method: 'POST',
        body: JSON.stringify(feedback),
    });

export const getMyActivityFeedback = (userId, activityId) =>
    requestRoot(`/activity/feedback/${userId}/${activityId}`, { method: 'GET' });

export const getActivityEffectiveness = (activityId) =>
    requestRoot(`/activity/effectiveness/${activityId}`, { method: 'GET' });

export const getTopRatedActivities = () =>
    requestRoot('/activity/top-rated', { method: 'GET' });

// ─── Community ──────────────────────────────────────
export const getCommunityClusters = () =>
    requestRoot('/community/clusters', { method: 'GET' });

export const getUserCommunity = (userId) =>
    requestRoot(`/community/${userId}`, { method: 'GET' });

export const createCommunityPost = (communityId, userId, payload) =>
    requestRoot(`/community/${communityId}/post/${userId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
    });

export const getCommunityPosts = (communityId, userId) =>
    requestRoot(`/community/${communityId}/posts/${userId}`, { method: 'GET' });

export const getCommunityPostsPublic = (communityId) =>
    requestRoot(`/community/${communityId}/posts`, { method: 'GET' });

// Component 4 enhancements on the community feed (filter-bubble mitigation +
// SHAP-style explainability + MC-Dropout uncertainty). Same backwards-compatible
// pattern: FastAPI ignores unknown query params until the route forwards them
// to rank_feed_posts.
//   exploration_rate       — fraction of top-N reserved for serendipity (0 disables)
//   with_explanations      — attach top-k SHAP feature-group attributions
//   explanation_top_k      — how many drivers to keep per post
//   with_uncertainty       — attach MC-Dropout uncertainty band
//   exploration_top_n      — size of the head we apply exploration to
export const getCommunityFeed = (userId, opts = {}) => {
    const {
        exploration_rate = 0.15,
        with_explanations = true,
        explanation_top_k = 3,
        with_uncertainty = true,
        exploration_top_n = 20,
    } = opts;
    const qs = new URLSearchParams({
        exploration_rate: String(exploration_rate),
        with_explanations: String(with_explanations),
        explanation_top_k: String(explanation_top_k),
        with_uncertainty: String(with_uncertainty),
        exploration_top_n: String(exploration_top_n),
    });
    return requestRoot(`/community/feed/${userId}?${qs.toString()}`, { method: 'GET' });
};

export const getCommunityUsers = (communityId) =>
    requestRoot(`/community/${communityId}/users`, { method: 'GET' });

// ─── Mood Check-In ──────────────────────────────────
export const submitMoodCheckIn = (userId, mood) =>
    requestRoot(`/community/mood/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ mood }),
    });

export const getMoodToday = (userId) =>
    requestRoot(`/community/mood/${userId}/today`, { method: 'GET' });

export const getCommunityMoodPulse = (userId) =>
    requestRoot(`/community/mood/${userId}/pulse`, { method: 'GET' });

export const getMoodHistory = (userId, days = 7) =>
    requestRoot(`/community/mood/${userId}/history?days=${days}`, { method: 'GET' });

// ─── Streaks & Badges ──────────────────────────────
export const getUserStreaks = (userId) =>
    requestRoot(`/community/streaks/${userId}`, { method: 'GET' });

export const getUserBadges = (userId) =>
    requestRoot(`/community/badges/${userId}`, { method: 'GET' });

// ─── Post Reactions ─────────────────────────────────
export const togglePostReaction = (postId, userId, reactionType) =>
    requestRoot(`/community/post/${postId}/react/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ reaction_type: reactionType }),
    });

export const getPostReactions = (postId, userId) =>
    requestRoot(`/community/post/${postId}/reactions/${userId}`, { method: 'GET' });

// ─── Weekly Wellness Summary ────────────────────────
export const getWeeklyWellnessSummary = (userId) =>
    requestRoot(`/community/wellness-summary/${userId}`, { method: 'GET' });

// ─── Crisis Detection Safety Net ────────────────────
export const runSafetyCheck = (userId) =>
    requestRoot(`/community/crisis/safety-check/${userId}`, { method: 'GET' });

export const getCrisisAlerts = (userId, activeOnly = true) =>
    requestRoot(`/community/crisis/alerts/${userId}?active_only=${activeOnly}`, { method: 'GET' });

export const resolveCrisisAlert = (alertId) =>
    requestRoot(`/community/crisis/resolve/${alertId}`, { method: 'POST' });

// ─── CBT Thought Journal ───────────────────────────
export const createJournalEntry = (userId, entryText, entryDate = null) =>
    requestRoot(`/community/journal/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ entry_text: entryText, entry_date: entryDate }),
    });

export const analyzeJournalText = (userId, text) =>
    requestRoot(`/community/journal/${userId}/analyze`, {
        method: 'POST',
        body: JSON.stringify({ text }),
    });

export const getJournalEntries = (userId, days = 30) =>
    requestRoot(`/community/journal/${userId}/entries?days=${days}`, { method: 'GET' });

export const getJournalEntry = (userId, entryId) =>
    requestRoot(`/community/journal/${userId}/entry/${entryId}`, { method: 'GET' });

export const getJournalTrends = (userId, days = 30) =>
    requestRoot(`/community/journal/${userId}/trends?days=${days}`, { method: 'GET' });

export const rateJournalReframe = (userId, entryId, foundHelpful) =>
    requestRoot(`/community/journal/${userId}/feedback/${entryId}`, {
        method: 'POST',
        body: JSON.stringify({ found_helpful: foundHelpful }),
    });

export const getDistortionCatalog = () =>
    requestRoot('/community/journal/catalog', { method: 'GET' });

// ─── Patients ───────────────────────────────────────
export const listPatients = (skip = 0, limit = 50) =>
    request(`/patients?skip=${skip}&limit=${limit}`);

export const getPatient = (id) =>
    request(`/patients/${id}`);

export const createPatient = (patient) =>
    request('/patients', { method: 'POST', body: JSON.stringify(patient) });

export const updatePatient = (id, patient) =>
    request(`/patients/${id}`, { method: 'PUT', body: JSON.stringify(patient) });

export const deletePatient = (id) =>
    request(`/patients/${id}`, { method: 'DELETE' });

export const getPatientByUser = (userId) =>
    request(`/patients/by-user/${userId}`);

export const createPatientFromUser = (userId, heartRate = 72) =>
    request(`/patients/from-user/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ latest_heart_rate: heartRate }),
    });

// ─── Simulation ─────────────────────────────────────
export const predictRisk = (patientState) =>
    request('/simulation/predict_risk', {
        method: 'POST',
        body: JSON.stringify(patientState),
    });

export const simulateIntervention = (payload) =>
    request('/simulation/simulate_intervention', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

export const simulateBatch = (payload) =>
    request('/simulation/simulate_batch', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

export const prescribeAI = (patientState) =>
    request('/simulation/prescribe_ai', {
        method: 'POST',
        body: JSON.stringify(patientState),
    });

// ─── What-If Simulator ──────────────────────────────
export const simulateWhatIf = (payload) =>
    request('/whatif/what_if', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// ─── XAI (Explainable AI) ───────────────────────────
export const explainRisk = (patientState) =>
    request('/xai/explain_risk', {
        method: 'POST',
        body: JSON.stringify(patientState),
    });

// ─── Next-Best-Action ───────────────────────────────
export const getNextBestAction = (patientState) =>
    request('/nba/recommend', {
        method: 'POST',
        body: JSON.stringify(patientState),
    });

// ─── Intervention Sequencing ────────────────────────
export const runSequence = (payload) =>
    request('/sequence/run_sequence', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// ─── MC Dropout Uncertainty ─────────────────────────
export const evaluateUncertainty = (payload) =>
    request('/uncertainty/evaluate', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// ─── Clinical Reports ───────────────────────────────
export const generateReport = (payload) =>
    request('/reports/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// ─── Digital Twin Factory ───────────────────────────
export const generateTwin = (payload) =>
    request('/twin/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

export const personalTwin = (payload) =>
    request('/twin/personal', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// ─── Enhanced Insights (SHAP + Counterfactuals) ───────
// POST versions — accept a manual 16-feature payload (kept for other callers)
export const predictWithInsights = (payload) =>
    request('/insights/predict', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

export const generateCounterfactual = (payload) =>
    request('/insights/counterfactual', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

// GET versions — backend fetches the user's real assessment answers from the DB
// Use these from the Insights page so results reflect actual user data.
export const predictInsightsForUser = (userId) =>
    request(`/insights/predict/user/${userId}`, { method: 'GET' });

export const counterfactualForUser = (userId, targetReduction = 5.0) =>
    request(`/insights/counterfactual/user/${userId}?target_reduction=${targetReduction}`, { method: 'GET' });

// ─── Enhanced Dashboard ────────────────────────────────
export const getDashboardContent = () =>
    request('/dashboard/content', { method: 'GET' });

export const analyzeJournalSentiment = (text) =>
    request('/dashboard/journal-sentiment', {
        method: 'POST',
        body: JSON.stringify({ text }),
    });

export const getMoodTrend = (entries) =>
    request('/dashboard/mood-trend', {
        method: 'POST',
        body: JSON.stringify({ entries }),
    });

// ─── Guided Wellness Session (Therapy) ─────────────────
export const startTherapySession = (userId) =>
    request('/therapy/start', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
    });

export const getTherapyStatus = (sessionId) =>
    request(`/therapy/${sessionId}/status`, { method: 'GET' });

export const therapyCheckIn = (sessionId, moodScore, concern) =>
    request(`/therapy/${sessionId}/check-in`, {
        method: 'POST',
        body: JSON.stringify({ mood_score: moodScore, concern }),
    });

export const therapySendMessage = (sessionId, message, persona = 'counselor') =>
    request(`/therapy/${sessionId}/message`, {
        method: 'POST',
        body: JSON.stringify({ message, persona }),
    });

export const therapyAdvance = (sessionId) =>
    request(`/therapy/${sessionId}/advance`, { method: 'POST' });

export const therapyGetCBT = (sessionId) =>
    request(`/therapy/${sessionId}/cbt`, { method: 'GET' });

export const therapyGetReframe = (sessionId) =>
    request(`/therapy/${sessionId}/reframe`, { method: 'GET' });

export const therapyGetPlan = (sessionId) =>
    request(`/therapy/${sessionId}/plan`, { method: 'GET' });

export const therapyGetRelax = (sessionId) =>
    request(`/therapy/${sessionId}/relax`, { method: 'GET' });

export const therapyComplete = (sessionId, finalMoodScore) =>
    request(`/therapy/${sessionId}/complete`, {
        method: 'POST',
        body: JSON.stringify({ final_mood_score: finalMoodScore }),
    });

// ─── Enhanced C1: Narrative + PubMed Evidence ──────────
export const generateNarrative = (interventionName, simulationData, userProfile = null) =>
    request('/enhanced/narrative', {
        method: 'POST',
        body: JSON.stringify({
            intervention_name: interventionName,
            simulation_data: simulationData,
            user_profile: userProfile,
        }),
    });

export const getEvidenceCards = (interventionType, maxResults = 3) =>
    request(`/enhanced/evidence/${encodeURIComponent(interventionType)}?max_results=${maxResults}`, {
        method: 'GET',
    });
