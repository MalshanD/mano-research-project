// API Configuration
// In development the Vite proxy forwards /api and /users to the FastAPI backend,
// so we intentionally use an empty base URL (same-origin) to avoid CORS issues.
// Set VITE_API_BASE_URL in .env for staging / production deployments.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
// SockJS requires http:// (not ws://) — it handles the WebSocket upgrade internally
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'http://localhost:8000/ws';



// ML Services (for direct access if needed)
export const ML_SERVICES = {
    LSTM: import.meta.env.VITE_LSTM_URL || 'http://localhost:5001',
    GAN: import.meta.env.VITE_GAN_URL || 'http://localhost:5002',
    CHATBOT: import.meta.env.VITE_CHATBOT_URL || 'http://localhost:5003',
    GMM: import.meta.env.VITE_GMM_URL || 'http://localhost:5004',
};

// Authentication
export const TOKEN_KEY = 'mano_access_token';
export const REFRESH_TOKEN_KEY = 'mano_refresh_token';
export const TOKEN_EXPIRY_KEY = 'mano_token_expiry';

// User Roles
export const ROLES = {
    USER: 'ROLE_USER',
    PROFESSIONAL: 'ROLE_HEALTHCARE_PROFESSIONAL',
    RESEARCHER: 'ROLE_RESEARCHER',
    ADMIN: 'ROLE_ADMIN',
};

// Risk Levels
export const RISK_LEVELS = {
    LOW: { key: 'LOW', label: 'Low', color: 'success', threshold: 0.3 },
    MEDIUM: { key: 'MEDIUM', label: 'Medium', color: 'warning', threshold: 0.5 },
    HIGH: { key: 'HIGH', label: 'High', color: 'accent', threshold: 0.7 },
    SEVERE: { key: 'SEVERE', label: 'Severe', color: 'crisis', threshold: 0.85 },
    CRITICAL: { key: 'CRITICAL', label: 'Critical', color: 'crisis', threshold: 1.0 },
};

// Crisis Levels
export const CRISIS_LEVELS = {
    NONE: { key: 'NONE', label: 'None', severity: 0 },
    LOW: { key: 'LOW', label: 'Low', severity: 1 },
    MEDIUM: { key: 'MEDIUM', label: 'Medium', severity: 2 },
    HIGH: { key: 'HIGH', label: 'High', severity: 3 },
    CRITICAL: { key: 'CRITICAL', label: 'Critical', severity: 4 },
};

// Cluster Categories
export const CLUSTERS = {
    THRIVING: { id: 0, name: 'Thriving', resilience: 'HIGH_RESILIENCE', severity: 'NONE' },
    STABLE: { id: 1, name: 'Stable', resilience: 'MODERATE_RESILIENCE', severity: 'LOW' },
    STRUGGLING: { id: 2, name: 'Struggling', resilience: 'LOW_RESILIENCE', severity: 'MEDIUM' },
    AT_RISK: { id: 3, name: 'At Risk', resilience: 'VERY_LOW_RESILIENCE', severity: 'HIGH' },
    CRISIS: { id: 4, name: 'Crisis', resilience: 'CRITICAL', severity: 'VERY_HIGH' },
};

// Questionnaire Types
export const QUESTIONNAIRES = {
    PHQ9: {
        key: 'phq9',
        name: 'PHQ-9',
        fullName: 'Patient Health Questionnaire-9',
        description: 'Depression screening tool',
        questions: 9,
        maxScore: 27,
        scale: [0, 1, 2, 3],
    },
    GAD7: {
        key: 'gad7',
        name: 'GAD-7',
        fullName: 'Generalized Anxiety Disorder-7',
        description: 'Anxiety screening tool',
        questions: 7,
        maxScore: 21,
        scale: [0, 1, 2, 3],
    },
    PSS: {
        key: 'pss',
        name: 'PSS',
        fullName: 'Perceived Stress Scale',
        description: 'Stress measurement tool',
        questions: 10,
        maxScore: 40,
        scale: [0, 1, 2, 3, 4],
    },
};

// Sentiment Labels
export const SENTIMENT_LABELS = {
    VERY_NEGATIVE: { min: -1.0, max: -0.6, label: 'Very Negative', color: 'crisis' },
    NEGATIVE: { min: -0.6, max: -0.2, label: 'Negative', color: 'warning' },
    NEUTRAL: { min: -0.2, max: 0.2, label: 'Neutral', color: 'neutral' },
    POSITIVE: { min: 0.2, max: 0.6, label: 'Positive', color: 'success' },
    VERY_POSITIVE: { min: 0.6, max: 1.0, label: 'Very Positive', color: 'success' },
};

// Pagination
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Date Formats
export const DATE_FORMATS = {
    DISPLAY: 'MMM d, yyyy',
    DISPLAY_TIME: 'MMM d, yyyy h:mm a',
    INPUT: 'yyyy-MM-dd',
    API: "yyyy-MM-dd'T'HH:mm:ss",
    TIME_ONLY: 'h:mm a',
    RELATIVE: 'relative',
};

// Animation Durations (in ms)
export const ANIMATION = {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
};

// Breakpoints (matching Tailwind)
export const BREAKPOINTS = {
    SM: 640,
    MD: 768,
    LG: 1024,
    XL: 1280,
    '2XL': 1536,
};

// Local Storage Keys
export const STORAGE_KEYS = {
    THEME: 'mano_theme',
    SIDEBAR_COLLAPSED: 'mano_sidebar_collapsed',
    RECENT_CONVERSATIONS: 'mano_recent_conversations',
    USER_PREFERENCES: 'mano_user_preferences',
};

// Emergency Resources
export const EMERGENCY_RESOURCES = [
    {
        name: 'National Mental Health Helpline',
        phone: '1926',
        description: 'Available 24/7',
        type: 'call',
    },
    {
        name: 'Lanka Life Line',
        phone: '1375',
        description: 'non-profit, confidential community helpline',
        type: 'text',
    },
    {
        name: 'Emergency Services',
        phone: '911',
        description: 'For immediate emergencies',
        type: 'call',
    },
    {
        name: 'Sri Lanka Sumithrayo',
        phone: '+94 767 520 620',
        description: 'Sumithrayo offers emotional support',
        type: 'call',
    },
];

// Crisis Keywords (client-side detection)
export const CRISIS_KEYWORDS = [
    'suicide', 'suicidal', 'kill myself', 'end my life', 'want to die',
    'self-harm', 'hurt myself', 'cutting', 'overdose',
    'hopeless', 'no reason to live', 'better off dead',
    'can\'t go on', 'end it all', 'give up',
];