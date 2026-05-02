import { API_BASE_URL } from './constants';

// API Endpoints Configuration
export const API_ENDPOINTS = {
    // Authentication
    AUTH: {
        LOGIN: '/api/auth/login',
        REGISTER: '/api/auth/register',
        // Unified login+register endpoint: creates user if not exists, logs in otherwise
        CREATE_OR_LOGIN: '/users/create/',
        LOGOUT: '/api/auth/logout',
        REFRESH: '/api/auth/refresh',
        ME: '/api/auth/me',
        VERIFY_EMAIL: '/api/auth/verify-email',
        FORGOT_PASSWORD: '/api/auth/forgot-password',
        CHANGE_PASSWORD: '/api/auth/change-password',
    },

    // Predictions (Component 2 - LSTM)
    PREDICTIONS: {
        BASE: '/api/predictions',
        DIRECT: '/api/predictions/direct',
        PHQ9: '/api/predictions/questionnaire/phq9',
        GAD7: '/api/predictions/questionnaire/gad7',
        PSS: '/api/predictions/questionnaire/pss',
        ALL_QUESTIONNAIRES: '/api/predictions/questionnaire/all',
        HISTORY: '/api/predictions/history',
        TRENDS: '/api/predictions/trends',
    },

    // Chat (Component 3 - Chatbot)
    CHAT: {
        CREATE_SESSION: '/chat/session/create',  // POST /chat/session/create/{user_id}
        SESSIONS: '/chat/session',               // GET /chat/session/{user_id}
        MESSAGE: '/chat/message',                // POST body: {session_id, message, persona}
        MESSAGES: '/chat/message',               // GET /chat/message/{session_id}
        DELETE_SESSION: '/chat/session',         // DELETE /chat/session/{session_id}
    },

    // Clustering (Component 4 - GMM)
    CLUSTERS: {
        ASSIGN: '/api/clusters/assign',
        CURRENT: '/api/clusters/current',
        PEERS: '/api/clusters/peers',
        ACTIVITIES: '/api/clusters/activities',
        TRANSITIONS: '/api/clusters/transitions',
        STATISTICS: '/api/clusters/statistics',
    },

    // Synthetic Data (Component 1 - GAN)
    SYNTHETIC: {
        GENERATE: '/api/component1-data/generate',
        PRIVACY_BUDGET: '/api/component1-data/privacy-budget',
        SIMULATE: '/api/component1-data/simulate',
    },

    // User Profile
    PROFILE: {
        ME: '/api/mental-health/profiles/me',
        HIGH_RISK: '/api/mental-health/profiles/high-risk',
        BY_CLUSTER: '/api/mental-health/profiles/cluster',
    },

    // System Alerts
    ALERTS: {
        BASE: '/api/alerts',
        CRISIS: '/api/alerts/crisis',
        RESOLVE: '/api/alerts/{id}/resolve',
        ASSIGN: '/api/alerts/{id}/assign',
    },

    // Interventions
    INTERVENTIONS: {
        START: '/api/intervention-outcomes/start',
        COMPLETE: '/api/intervention-outcomes/{id}/complete',
        HISTORY: '/api/intervention-outcomes/history',
    },
};

// WebSocket Topics
export const WS_TOPICS = {
    CHAT: '/app/chat.send',
    CRISIS_ALERTS: '/topic/crisis.alerts',
    PROFESSIONAL_CRISIS: '/topic/professionals/crisis',
    USER_PREDICTIONS: '/user/queue/predictions',
    USER_CLUSTER_UPDATES: '/user/queue/cluster-updates',
    USER_INTERVENTIONS: '/user/queue/interventions',
    USER_CHAT_NOTIFICATIONS: '/user/queue/chat-notifications',
};

// Build full URL
export const buildUrl = (endpoint, params = {}) => {
    let url = `${API_BASE_URL}${endpoint}`;

    // Replace path parameters
    Object.keys(params).forEach((key) => {
        url = url.replace(`{${key}}`, params[key]);
    });

    return url;
};

// Build URL with query parameters
export const buildUrlWithQuery = (endpoint, queryParams = {}) => {
    const url = new URL(`${API_BASE_URL}${endpoint}`);

    Object.keys(queryParams).forEach((key) => {
        if (queryParams[key] !== undefined && queryParams[key] !== null) {
            url.searchParams.append(key, queryParams[key]);
        }
    });

    return url.toString();
};

export default API_ENDPOINTS;