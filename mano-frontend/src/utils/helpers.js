import { clsx } from 'clsx';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { RISK_LEVELS, SENTIMENT_LABELS, DATE_FORMATS } from '../config/constants';

/**
 * Merge class names conditionally
 */
export const cn = (...inputs) => clsx(inputs);

/**
 * Get risk level based on score
 */
export const getRiskLevel = (score) => {
    if (score < RISK_LEVELS.LOW.threshold) return RISK_LEVELS.LOW;
    if (score < RISK_LEVELS.MEDIUM.threshold) return RISK_LEVELS.MEDIUM;
    if (score < RISK_LEVELS.HIGH.threshold) return RISK_LEVELS.HIGH;
    if (score < RISK_LEVELS.SEVERE.threshold) return RISK_LEVELS.SEVERE;
    return RISK_LEVELS.CRITICAL;
};

/**
 * Get sentiment label based on score
 */
export const getSentimentLabel = (score) => {
    for (const [key, value] of Object.entries(SENTIMENT_LABELS)) {
        if (score >= value.min && score <= value.max) {
            return value;
        }
    }
    return SENTIMENT_LABELS.NEUTRAL;
};

/**
 * Format score as percentage
 */
export const formatScore = (score, decimals = 0) => {
    return `${(score * 100).toFixed(decimals)}%`;
};

/**
 * Format date with various options
 */
export const formatDate = (date, formatType = 'DISPLAY') => {
    if (!date) return '';

    const dateObj = typeof date === 'string' ? parseISO(date) : date;

    if (formatType === 'relative') {
        return formatDistanceToNow(dateObj, { addSuffix: true });
    }

    return format(dateObj, DATE_FORMATS[formatType] || DATE_FORMATS.DISPLAY);
};

/**
 * Truncate text with ellipsis
 */
export const truncateText = (text, maxLength = 100) => {
    if (!text || text.length <= maxLength) return text;
    return `${text.substring(0, maxLength).trim()}...`;
};

/**
 * Capitalize first letter
 */
export const capitalize = (str) => {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

/**
 * Generate initials from name
 */
export const getInitials = (firstName, lastName) => {
    const first = firstName?.charAt(0)?.toUpperCase() || '';
    const last = lastName?.charAt(0)?.toUpperCase() || '';
    return `${first}${last}` || '?';
};

/**
 * Format phone number
 */
export const formatPhone = (phone) => {
    if (!phone) return '';
    const cleaned = phone.replace(/\D/g, '');
    const match = cleaned.match(/^(\d{1})(\d{3})(\d{3})(\d{4})$/);
    if (match) {
        return `${match[1]}-${match[2]}-${match[3]}-${match[4]}`;
    }
    return phone;
};

/**
 * Debounce function
 */
export const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

/**
 * Throttle function
 */
export const throttle = (func, limit) => {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
};

/**
 * Deep clone object
 */
export const deepClone = (obj) => {
    return JSON.parse(JSON.stringify(obj));
};

/**
 * Check if value is empty
 */
export const isEmpty = (value) => {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string') return value.trim() === '';
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
};

/**
 * Generate unique ID
 */
export const generateId = () => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Sleep/delay function
 */
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Safe JSON parse
 */
export const safeJsonParse = (str, fallback = null) => {
    try {
        return JSON.parse(str);
    } catch {
        return fallback;
    }
};

/**
 * Get color class based on risk level
 */
export const getRiskColorClass = (level) => {
    const colorMap = {
        LOW: 'text-success-500',
        MEDIUM: 'text-warning-500',
        HIGH: 'text-accent-500',
        SEVERE: 'text-crisis-500',
        CRITICAL: 'text-crisis-600',
    };
    return colorMap[level] || 'text-neutral-500';
};

/**
 * Get background color class based on risk level
 */
export const getRiskBgClass = (level) => {
    const colorMap = {
        LOW: 'bg-success-100',
        MEDIUM: 'bg-warning-100',
        HIGH: 'bg-accent-100',
        SEVERE: 'bg-crisis-100',
        CRITICAL: 'bg-crisis-200',
    };
    return colorMap[level] || 'bg-neutral-100';
};

/**
 * Calculate trend direction
 */
export const getTrendDirection = (current, previous) => {
    if (!previous || current === previous) return 'STABLE';
    return current > previous ? 'WORSENING' : 'IMPROVING';
};

/**
 * Format number with suffix (1K, 1M, etc.)
 */
export const formatNumber = (num) => {
    if (num >= 1000000) {
        return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
        return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
};

/**
 * Validate email format
 */
export const isValidEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
};

/**
 * Storage helpers
 */
export const storage = {
    get: (key) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch {
            return null;
        }
    },
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch {
            return false;
        }
    },
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch {
            return false;
        }
    },
    clear: () => {
        try {
            localStorage.clear();
            return true;
        } catch {
            return false;
        }
    },
};