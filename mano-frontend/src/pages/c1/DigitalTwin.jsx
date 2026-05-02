/**
 * Digital Twin — onboarding-first page.
 *
 * First-time visitors see the 3-step OnboardingTour. Once dismissed,
 * they land on the privacy promises + the "Generate my Digital Twin"
 * primary action. Generation calls the existing /twin/generate
 * endpoint and shows the synthetic profile + 7-day vitals preview.
 */

import { useEffect, useState } from 'react';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import OnboardingTour, {
    shouldShowOnboarding,
} from '../../components/c1/OnboardingTour';
import { fetchDigitalTwin } from '../../lib/c1/apiClient';
import { request } from '../../api/client';
import { ShieldCheck, Sparkles } from 'lucide-react';

export default function DigitalTwin() {
    const { data, error, isLoading, retry } = useBundleFetch(fetchDigitalTwin, []);
    const [showTour, setShowTour] = useState(false);
    const [twin, setTwin] = useState(null);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        if (data && shouldShowOnboarding()) setShowTour(true);
    }, [data]);

    const generate = async () => {
        setGenerating(true);
        const { data: t, error: e } = await request('/twin/generate', {
            method: 'POST',
            body: JSON.stringify({}),
        });
        if (!e) setTwin(t);
        setGenerating(false);
    };

    return (
        <>
            {data && (
                <OnboardingTour
                    isOpen={showTour}
                    steps={data.onboarding}
                    onClose={() => setShowTour(false)}
                />
            )}

            <C1PageShell
                title={data?.page_title || 'Digital Twin'}
                subtitle={data?.page_subtitle}
                primaryAction={data?.primary_action}
                onPrimary={generate}
                isLoading={isLoading}
                error={error}
                onRetry={retry}
            >
                {data && (
                    <>
                        {/* Privacy promises card */}
                        <div className="mt-4 rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20 p-5">
                            <div className="flex items-start gap-3">
                                <ShieldCheck aria-hidden="true" className="w-5 h-5 text-emerald-700 mt-0.5" />
                                <div>
                                    <h2 className="text-base font-semibold text-emerald-900 dark:text-emerald-100">
                                        How we keep your data private
                                    </h2>
                                    <ul className="mt-3 space-y-2">
                                        {data.privacy_promises.map((p, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
                                                <span aria-hidden="true" className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                                                <span>{p}</span>
                                            </li>
                                        ))}
                                    </ul>
                                    <button
                                        type="button"
                                        onClick={() => setShowTour(true)}
                                        className="mt-4 text-sm text-emerald-700 dark:text-emerald-300 hover:underline"
                                    >
                                        Replay the tour
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Generated twin preview */}
                        {twin && (
                            <div className="mt-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                                <div className="flex items-center gap-2">
                                    <Sparkles aria-hidden="true" className="w-5 h-5 text-emerald-600" />
                                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                                        Your synthetic twin
                                    </h2>
                                </div>
                                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                                    Built fresh just now. Regenerate at any time.
                                </p>
                                <pre className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-xs overflow-x-auto text-slate-800 dark:text-slate-200 max-h-72">
                                    {JSON.stringify(twin, null, 2)}
                                </pre>
                                <button
                                    type="button"
                                    onClick={generate}
                                    disabled={generating}
                                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                                >
                                    Regenerate
                                </button>
                            </div>
                        )}

                        {/* Generate hint */}
                        {!twin && (
                            <div className="mt-6 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/50 dark:bg-slate-900/40 p-8 text-center">
                                <Sparkles aria-hidden="true" className="w-8 h-8 mx-auto text-emerald-500" />
                                <p className="mt-3 text-sm text-slate-600 dark:text-slate-400 max-w-sm mx-auto">
                                    Click <strong>Generate my Digital Twin</strong> above to create
                                    a fresh synthetic profile you can experiment with — no real data is used.
                                </p>
                                {generating && (
                                    <p className="mt-3 text-xs text-slate-500">Generating…</p>
                                )}
                            </div>
                        )}
                    </>
                )}
            </C1PageShell>
        </>
    );
}
