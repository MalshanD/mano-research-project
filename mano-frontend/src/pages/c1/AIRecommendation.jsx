/**
 * AI Recommendation — merged Next Best Action + Compare + Prescription.
 * Three ranked plan cards with PubMed evidence, gated by PatientStateGate.
 */
import { useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import SeverityChip from '../../components/c1/SeverityChip';
import PatientStateGate from '../../components/c1/PatientStateGate';
import { fetchAIRecommendation } from '../../lib/c1/apiClient';
import { request } from '../../api/client';
import { usePatientState } from '../../lib/c1/usePatientState';
import { Trophy, BookOpen, Check, X, Clock } from 'lucide-react';

function CardBadge({ rank }) {
    if (rank === 1) {
        return (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 px-2 py-0.5 text-xs font-semibold">
                <Trophy aria-hidden="true" className="w-3.5 h-3.5" /> Top pick for you
            </span>
        );
    }
    return <span className="text-xs uppercase tracking-wider text-slate-500">Alternative #{rank - 1}</span>;
}

function EvidenceCard({ evidence }) {
    if (!evidence?.length) return null;
    return (
        <div className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3">
            <p className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500">
                <BookOpen aria-hidden="true" className="w-3.5 h-3.5" /> Research evidence
            </p>
            <ul className="mt-1.5 space-y-1.5">
                {evidence.map((e, i) => (
                    <li key={i} className="text-xs text-slate-700 dark:text-slate-300">
                        <a href={e.pubmed_url || '#'} target={e.pubmed_url ? '_blank' : undefined}
                           rel={e.pubmed_url ? 'noopener noreferrer' : undefined}
                           className="font-medium underline-offset-2 hover:underline">{e.title}</a>
                        <span className="ml-1 text-slate-500"> {e.snippet}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default function AIRecommendation() {
    const [params] = useSearchParams();
    const prefillArm = params.get('prefill');
    const { status, patientState, patientId, error: patientError, refresh } = usePatientState();
    const ready = status === 'ready';
    const [feedback, setFeedback] = useState(null);

    const { data, error, isLoading, retry } = useBundleFetch(
        () => ready
            ? fetchAIRecommendation({ patient_state: patientState, prefill_arm: prefillArm ? Number(prefillArm) : null })
            : Promise.resolve({ data: null, error: null }),
        [ready ? patientId : null, prefillArm],
    );

    const send = async (arm, action) => {
        if (!patientId) return;
        setFeedback({ arm, action, pending: true });
        const { error: e } = await request('/feedback/intervention', {
            method: 'POST',
            body: JSON.stringify({ patient_id: patientId, intervention_type: arm, feedback: action, context: {} }),
        });
        setFeedback({ arm, action, pending: false, error: e });
    };

    return (
        <C1PageShell
            title={data?.page_title || 'AI Recommendation'}
            subtitle={data?.page_subtitle}
            primaryAction={ready ? data?.primary_action : null}
            onPrimary={() => data?.cards?.[0] && send(data.cards[0].intervention_type, 'accept')}
            isLoading={ready && isLoading}
            error={ready ? error : null}
            onRetry={retry}
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                {data && (
                    <div className="mt-4 space-y-4">
                        {data.cards.map((c) => {
                            const isPrefilled = data.pre_filled_intervention &&
                                data.pre_filled_intervention.arm === c.intervention_type;
                            return (
                                <article key={`${c.rank}-${c.intervention_type}`}
                                    className={'rounded-2xl bg-white dark:bg-slate-900 border p-5 shadow-sm transition ' +
                                        (c.rank === 1 ? 'border-emerald-300 dark:border-emerald-700 ring-1 ring-emerald-200/50' : 'border-slate-200 dark:border-slate-800') +
                                        (isPrefilled ? ' ring-2 ring-amber-300' : '')}>
                                    <header className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <CardBadge rank={c.rank} />
                                            <h2 className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{c.label}</h2>
                                            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{c.why_this}</p>
                                        </div>
                                        <SeverityChip render={c.render} size="sm" />
                                    </header>
                                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-2 text-center">
                                            <p className="text-slate-500">Delta Risk</p>
                                            <p className={`mt-0.5 font-semibold ${c.delta_high_risk_probability < 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                                                {c.delta_high_risk_probability >= 0 ? '+' : ''}{(c.delta_high_risk_probability * 100).toFixed(1)}%
                                            </p>
                                        </div>
                                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-2 text-center">
                                            <p className="text-slate-500">Confidence</p>
                                            <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-200">{Math.round(c.confidence * 100)}%</p>
                                        </div>
                                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-2 text-center">
                                            <p className="text-slate-500">Ease</p>
                                            <p className="mt-0.5 font-semibold text-slate-800 dark:text-slate-200">{Math.round(c.ease_score * 100)}%</p>
                                        </div>
                                    </div>
                                    {c.narrative_snippet && (
                                        <blockquote className="mt-4 border-l-2 border-emerald-300 pl-3 text-sm italic text-slate-700 dark:text-slate-300">
                                            &ldquo;{c.narrative_snippet}&rdquo;
                                        </blockquote>
                                    )}
                                    <EvidenceCard evidence={c.evidence} />
                                    <footer className="mt-4 flex flex-wrap gap-2">
                                        <button type="button" onClick={() => send(c.intervention_type, 'accept')}
                                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 text-sm font-medium">
                                            <Check aria-hidden="true" className="w-4 h-4" /> Accept
                                        </button>
                                        <button type="button" onClick={() => send(c.intervention_type, 'defer')}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 px-3 py-1.5 text-sm font-medium">
                                            <Clock aria-hidden="true" className="w-4 h-4" /> Maybe later
                                        </button>
                                        <button type="button" onClick={() => send(c.intervention_type, 'reject')}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 px-3 py-1.5 text-sm font-medium">
                                            <X aria-hidden="true" className="w-4 h-4" /> Not for me
                                        </button>
                                        {feedback?.arm === c.intervention_type && !feedback.pending && !feedback.error && (
                                            <span className="self-center text-xs text-emerald-700">Recorded.</span>
                                        )}
                                    </footer>
                                </article>
                            );
                        })}
                    </div>
                )}
            </PatientStateGate>
        </C1PageShell>
    );
}
