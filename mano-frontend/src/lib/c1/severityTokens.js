/**
 * Severity tokens shared across the Component-1 consumer-view pages.
 *
 * Backend payloads carry `severity_color` (Tailwind colour token like
 * "emerald-500") and `icon_hint` (lucide-react icon name like
 * "shield-check"). This module is the single source of truth for
 * resolving those strings into:
 *
 *   - Tailwind class fragments (text/bg/border/ring) we can compose,
 *   - lucide-react icon components,
 *   - aria-friendly text labels for screen readers.
 *
 * Centralising here means a UX revision is one file diff.
 */

import {
    ShieldCheck, Shield, ShieldAlert, Siren, Eye, AlertTriangle, CheckCircle,
    CloudRain, CloudFog, Cloud, Sun, Wind, Heart, Moon, Bed, BrainCircuit,
    Settings, Sparkles, Play, ArrowRight, Route, TrendingDown, TrendingUp,
    Minus, Check,
} from 'lucide-react';

// Colour-token → Tailwind class group. Keys must match what the backend
// emits in `severity_color`. Add new entries here, never inline.
const COLOR_MAP = {
    'emerald-500': {
        text: 'text-emerald-600',
        bg: 'bg-emerald-50 dark:bg-emerald-950/30',
        border: 'border-emerald-200 dark:border-emerald-800',
        ring: 'ring-emerald-300',
        chip: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
        accent: 'bg-emerald-500',
        ariaTone: 'positive',
    },
    'amber-500': {
        text: 'text-amber-600',
        bg: 'bg-amber-50 dark:bg-amber-950/30',
        border: 'border-amber-200 dark:border-amber-800',
        ring: 'ring-amber-300',
        chip: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
        accent: 'bg-amber-500',
        ariaTone: 'caution',
    },
    'orange-500': {
        text: 'text-orange-600',
        bg: 'bg-orange-50 dark:bg-orange-950/30',
        border: 'border-orange-200 dark:border-orange-800',
        ring: 'ring-orange-300',
        chip: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
        accent: 'bg-orange-500',
        ariaTone: 'warning',
    },
    'rose-600': {
        text: 'text-rose-700',
        bg: 'bg-rose-50 dark:bg-rose-950/30',
        border: 'border-rose-200 dark:border-rose-800',
        ring: 'ring-rose-300',
        chip: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
        accent: 'bg-rose-600',
        ariaTone: 'critical',
    },
};

// Icon-hint → lucide-react component. Frontend never invents an icon
// name — every value here is one the backend can emit.
const ICON_MAP = {
    'shield-check': ShieldCheck,
    'shield': Shield,
    'shield-alert': ShieldAlert,
    'siren': Siren,
    'eye': Eye,
    'alert-triangle': AlertTriangle,
    'check-circle': CheckCircle,
    'cloud-rain': CloudRain,
    'cloud-fog': CloudFog,
    'cloud': Cloud,
    'sun': Sun,
    'wind': Wind,
    'heart': Heart,
    'moon': Moon,
    'bed': Bed,
    'brain-circuit': BrainCircuit,
    'settings': Settings,
    'sparkles': Sparkles,
    'play': Play,
    'arrow-right': ArrowRight,
    'route': Route,
    'trending-down': TrendingDown,
    'trending-up': TrendingUp,
    'minus': Minus,
    'check': Check,
};

const FALLBACK = COLOR_MAP['emerald-500'];

/** Resolve a backend severity_color string into Tailwind class group. */
export function classesFor(severityColor) {
    return COLOR_MAP[severityColor] || FALLBACK;
}

/** Resolve a backend icon_hint into a lucide-react component reference. */
export function iconFor(iconHint) {
    return ICON_MAP[iconHint] || CheckCircle;
}

/** Compose a tone-of-voice prefix for screen readers. We never rely on
 *  colour alone (WCAG 2.2): every severity badge gets an aria-label
 *  that reads the tone + the microcopy. */
export function ariaLabelFor(severityColor, microcopy) {
    const { ariaTone } = classesFor(severityColor);
    const prefix = {
        positive: 'Status positive: ',
        caution: 'Caution: ',
        warning: 'Warning: ',
        critical: 'Critical alert: ',
    }[ariaTone] || '';
    return `${prefix}${microcopy || ''}`.trim();
}

/** Risk-level → human label; never trust the backend to spell it for us
 *  in the UI strings the user reads. Backend emits Low/Medium/High;
 *  here we attach plain-English context. */
export function riskLabelFor(level) {
    return {
        Low: 'Low risk',
        Medium: 'Medium risk',
        High: 'High risk',
    }[level] || level || 'Unknown';
}
