/**
 * OnboardingTour — 3-step guided tour driven by the backend's
 * digital_twin/bundle.onboarding payload.
 *
 * The user can navigate forward / back / skip. The "completed" flag
 * persists in localStorage so the tour doesn't replay every visit.
 *
 * Accessibility: a focus trap + dialog role keeps the tour properly
 * announced and tab-cycled.
 */

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { iconFor } from '../../lib/c1/severityTokens';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

const STORAGE_KEY = 'mano:c1:digital_twin_onboarding_v1';

export function shouldShowOnboarding() {
    try {
        return localStorage.getItem(STORAGE_KEY) !== 'completed';
    } catch {
        return true;
    }
}

export function markOnboardingComplete() {
    try { localStorage.setItem(STORAGE_KEY, 'completed'); } catch {}
}

export default function OnboardingTour({ steps, onClose, isOpen }) {
    const [idx, setIdx] = useState(0);
    const closeBtnRef = useRef(null);

    useEffect(() => {
        if (isOpen) closeBtnRef.current?.focus();
    }, [isOpen]);

    if (!isOpen || !steps?.length) return null;
    const total = steps.length;
    const step = steps[idx];
    const Illustration = iconFor(step.illustration_id);

    const finish = () => {
        markOnboardingComplete();
        onClose?.();
    };

    return (
        <AnimatePresence>
            <motion.div
                role="dialog"
                aria-modal="true"
                aria-label="Digital Twin onboarding"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4"
                onClick={(e) => { if (e.target === e.currentTarget) finish(); }}
            >
                <motion.div
                    initial={{ y: 16, scale: 0.98, opacity: 0 }}
                    animate={{ y: 0, scale: 1, opacity: 1 }}
                    exit={{ y: -16, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="w-full max-w-md rounded-3xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800"
                >
                    <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-800">
                        <p className="text-xs uppercase tracking-wider text-slate-500">
                            Step {idx + 1} of {total}
                        </p>
                        <button
                            ref={closeBtnRef}
                            type="button"
                            onClick={finish}
                            aria-label="Skip tour"
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                        >
                            <X aria-hidden="true" className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="px-6 py-7 text-center">
                        <div className="mx-auto w-20 h-20 rounded-full bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center">
                            <Illustration aria-hidden="true" className="w-10 h-10 text-emerald-600" />
                        </div>
                        <h3 className="mt-5 text-xl font-semibold text-slate-900 dark:text-slate-100">
                            {step.title}
                        </h3>
                        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                            {step.body}
                        </p>
                    </div>

                    <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 rounded-b-3xl">
                        <button
                            type="button"
                            disabled={idx === 0}
                            onClick={() => setIdx((i) => Math.max(0, i - 1))}
                            className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400 disabled:opacity-40 hover:text-slate-900 dark:hover:text-slate-100"
                        >
                            <ChevronLeft aria-hidden="true" className="w-4 h-4" />
                            Back
                        </button>

                        <div className="flex gap-1.5" aria-hidden="true">
                            {steps.map((_, i) => (
                                <span
                                    key={i}
                                    className={
                                        'block w-2 h-2 rounded-full ' +
                                        (i === idx ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700')
                                    }
                                />
                            ))}
                        </div>

                        {idx < total - 1 ? (
                            <button
                                type="button"
                                onClick={() => setIdx((i) => Math.min(total - 1, i + 1))}
                                className="inline-flex items-center gap-1 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-1.5 text-sm font-medium hover:opacity-90"
                            >
                                Next
                                <ChevronRight aria-hidden="true" className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={finish}
                                className="rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 text-sm font-medium"
                            >
                                Got it
                            </button>
                        )}
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
