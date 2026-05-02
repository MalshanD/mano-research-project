/**
 * PrimaryActionBar — the *one* primary CTA above the fold per page.
 *
 * Backed by the bundle's `primary_action: { label, endpoint, method, icon_hint }`.
 * Always one button, always sticky-above-the-fold on mobile, always
 * the same visual weight so users build a habit of where to look.
 */

import { iconFor } from '../../lib/c1/severityTokens';

export default function PrimaryActionBar({ action, onClick, disabled = false }) {
    if (!action) return null;
    const Icon = iconFor(action.icon_hint);
    return (
        <div className="sticky top-0 z-10 -mx-4 sm:mx-0 bg-gradient-to-b from-white via-white/95 to-transparent dark:from-slate-950 dark:via-slate-950/95 px-4 sm:px-0 pb-2 pt-3">
            <button
                type="button"
                onClick={onClick}
                disabled={disabled}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 text-sm font-semibold shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-emerald-500 transition"
            >
                <Icon aria-hidden="true" className="w-4 h-4" />
                <span>{action.label}</span>
            </button>
        </div>
    );
}
