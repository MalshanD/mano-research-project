/**
 * Guided Therapy Session — entry page.
 *
 * Shows the 7-phase progress strip and the safety promise card.
 * Primary action starts a new session (which transitions the user
 * into the existing chat-style therapy flow at /therapy).
 */

import { useNavigate } from 'react-router-dom';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import { fetchGuidedTherapyEntry } from '../../lib/c1/apiClient';
import { ShieldCheck } from 'lucide-react';

export default function GuidedTherapy() {
    const navigate = useNavigate();
    const { data, error, isLoading, retry } = useBundleFetch(fetchGuidedTherapyEntry, []);

    return (
        <C1PageShell
            title={data?.page_title || 'Guided Therapy Session'}
            subtitle={data?.page_subtitle}
            primaryAction={data?.primary_action}
            onPrimary={() => navigate('/therapy')}
            isLoading={isLoading}
            error={error}
            onRetry={retry}
            skeletonCardCount={2}
        >
            {data && (
                <>
                    <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                            What to expect
                        </h2>
                        <ol className="mt-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                            {data.phases.map((p, i) => (
                                <li
                                    key={p.id}
                                    className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-center"
                                >
                                    <p className="text-xs text-slate-500">Phase {i + 1}</p>
                                    <p className="mt-0.5 text-sm font-medium text-slate-900 dark:text-slate-100">
                                        {p.label}
                                    </p>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                        ~{p.minutes} min
                                    </p>
                                </li>
                            ))}
                        </ol>
                    </div>

                    <div className="mt-4 rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20 p-5">
                        <div className="flex items-start gap-3">
                            <ShieldCheck aria-hidden="true" className="w-5 h-5 text-emerald-700 mt-0.5" />
                            <div>
                                <h2 className="text-base font-semibold text-emerald-900 dark:text-emerald-100">
                                    Your safety always comes first
                                </h2>
                                <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
                                    {data.safety_promise}
                                </p>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </C1PageShell>
    );
}
