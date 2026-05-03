/**
 * My Summary — the dashboard landing page.
 *
 * One bundled fetch (/api/v1/summary/bundle) returns risk + 7-day
 * metrics + weather + trajectory alert + affirmation + quote +
 * primary CTA. The page binds directly off it.
 *
 * UX invariants:
 *  - One H1, one subtitle, one primary CTA above the fold.
 *  - Risk gauge animates on first paint (count up + sweep).
 *  - Severity is communicated by colour + icon + text label, never
 *    colour alone.
 *  - Loading state uses the skeleton, not a spinner.
 *  - NO mock fallback data — when the patient profile or 7-day
 *    vitals window is missing, the PatientStateGate renders an
 *    actionable empty state instead.
 */

import { useNavigate } from 'react-router-dom';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import AnimatedRiskGauge from '../../components/c1/AnimatedRiskGauge';
import SeverityChip from '../../components/c1/SeverityChip';
import PatientStateGate from '../../components/c1/PatientStateGate';
import { fetchMySummary } from '../../lib/c1/apiClient';
import { usePatientState } from '../../lib/c1/usePatientState';
import { Moon, Heart, Wind, Droplet, MessageSquareQuote } from 'lucide-react';

function MetricCard({ icon: Icon, label, value, unit }) {
    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-slate-500">
                <Icon aria-hidden="true" className="w-4 h-4" />
                <span className="text-xs uppercase tracking-wider">{label}</span>
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {value}
                <span className="ml-1 text-sm font-normal text-slate-500">{unit}</span>
            </p>
        </div>
    );
}

export default function MySummary() {
    const navigate = useNavigate();
    const {
        status, patientState, patientId, patientName, error: patientError, refresh,
    } = usePatientState();

    const ready = status === 'ready';

    const { data, error, isLoading, retry } = useBundleFetch(
        () => ready
            ? fetchMySummary({ patient_id: patientId, patient_state: patientState, user_name: patientName })
            : Promise.resolve({ data: null, error: null }),
        [ready ? patientId : null],
    );

    const handlePrimary = () => {
        const action = data?.primary_action;
        if (!action) return;
        if (action.endpoint.includes('/therapy/start')) navigate('/c1/therapy');
        else if (action.endpoint.includes('/recommendation')) navigate('/c1/recommendation');
        else if (action.endpoint.includes('/rehearsal')) navigate('/c1/future');
        else if (action.endpoint.includes('/see-my-future')) navigate('/c1/future');
        else navigate('/c1/future');
    };

    return (
        <C1PageShell
            title={data?.page_title || 'My Summary'}
            subtitle={data?.page_subtitle || 'How you’re doing today, in plain language.'}
            primaryAction={ready ? data?.primary_action : null}
            onPrimary={handlePrimary}
            isLoading={ready && isLoading}
            error={ready ? error : null}
            onRetry={retry}
            skeletonCardCount={4}
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                {data && (
                    <>
                        <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-950 p-6">
                            <div className="self-center">
                                <p className="text-xs uppercase tracking-wider text-slate-500">Greeting</p>
                                <p className="mt-1 text-xl sm:text-2xl font-medium text-slate-900 dark:text-slate-100 max-w-md">
                                    {data.greeting}
                                </p>
                                <SeverityChip render={data.risk_render} className="mt-4" />
                            </div>
                            <div className="self-center justify-self-center lg:justify-self-end">
                                <AnimatedRiskGauge
                                    riskLevel={data.risk_level}
                                    confidence={data.risk_confidence}
                                    severityColor={data.risk_render.severity_color}
                                    iconHint={data.risk_render.icon_hint}
                                    sublabel={`${Math.round(data.risk_confidence * 100)}% confidence`}
                                />
                            </div>
                        </div>

                        <h2 className="mt-8 text-lg font-semibold text-slate-900 dark:text-slate-100">
                            Last 7 days at a glance
                        </h2>
                        <div className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3">
                            <MetricCard icon={Moon} label="Sleep" value={data.seven_day_metrics.sleep_hours} unit="hrs" />
                            <MetricCard icon={Droplet} label="Sleep quality" value={data.seven_day_metrics.sleep_quality_pct} unit="%" />
                            <MetricCard icon={Heart} label="Heart rate" value={data.seven_day_metrics.heart_rate_bpm} unit="bpm" />
                            <MetricCard icon={Wind} label="Stress" value={data.seven_day_metrics.stress_pct} unit="%" />
                        </div>

                        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                                <p className="text-xs uppercase tracking-wider text-slate-500">Trajectory</p>
                                <p className="mt-2 font-medium text-slate-900 dark:text-slate-100">
                                    {data.trajectory_alert.microcopy}
                                </p>
                                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                                    {data.trajectory_alert.recommended_action}
                                </p>
                                <SeverityChip
                                    size="sm"
                                    className="mt-3"
                                    render={{
                                        severity_color: data.trajectory_alert.severity_color,
                                        icon_hint: data.trajectory_alert.icon_hint,
                                        microcopy: `Tier: ${data.trajectory_alert.tier}`,
                                    }}
                                >
                                    {`${data.trajectory_alert.tier.toUpperCase()} tier`}
                                </SeverityChip>
                            </div>
                            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                                <p className="text-xs uppercase tracking-wider text-slate-500">Weather · {data.weather_context.location}</p>
                                <p className="mt-2 font-medium text-slate-900 dark:text-slate-100">
                                    {data.weather_context.recommendation}
                                </p>
                                <SeverityChip
                                    size="sm"
                                    className="mt-3"
                                    render={{
                                        severity_color: data.weather_context.severity_color,
                                        icon_hint: data.weather_context.icon_hint,
                                        microcopy: `SAD risk: ${data.weather_context.sad_severity_label}`,
                                    }}
                                >
                                    {`SAD risk: ${data.weather_context.sad_severity_label}`}
                                </SeverityChip>
                            </div>
                        </div>

                        {(data.affirmation || data.quote) && (
                            <div className="mt-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-emerald-50/50 dark:bg-emerald-950/20 p-5">
                                <div className="flex items-start gap-3">
                                    <MessageSquareQuote aria-hidden="true" className="w-5 h-5 text-emerald-700 mt-0.5" />
                                    <div>
                                        {data.affirmation && (
                                            <p className="text-sm text-slate-800 dark:text-slate-200">{data.affirmation}</p>
                                        )}
                                        {data.quote && (
                                            <p className="mt-2 text-xs italic text-slate-600 dark:text-slate-400">
                                                &ldquo;{data.quote.text}&rdquo; &mdash; {data.quote.author}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </PatientStateGate>
        </C1PageShell>
    );
}
