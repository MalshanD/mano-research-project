/**
 * Understand My Risk — plain-English XAI with progressive SHAP toggle.
 * NO mock fallback — gated by PatientStateGate.
 */
import { useState } from 'react';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import AnimatedRiskGauge from '../../components/c1/AnimatedRiskGauge';
import PatientStateGate from '../../components/c1/PatientStateGate';
import { fetchUnderstandMyRisk } from '../../lib/c1/apiClient';
import { request } from '../../api/client';
import { usePatientState } from '../../lib/c1/usePatientState';
import { iconFor, classesFor } from '../../lib/c1/severityTokens';
import { ChevronDown, ChevronUp } from 'lucide-react';

function FactorCard({ f }) {
    const Icon = iconFor(f.icon_hint);
    const classes = classesFor(f.color);
    return (
        <li className={`rounded-2xl border ${classes.border} ${classes.bg} p-4`}>
            <div className="flex items-start gap-3">
                <Icon aria-hidden="true" className={`w-5 h-5 mt-0.5 ${classes.text}`} />
                <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-800 dark:text-slate-200">{f.plain_english}</p>
                    <div className="mt-2 h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden"
                         role="progressbar" aria-valuenow={f.magnitude_pct} aria-valuemin="0" aria-valuemax="100"
                         aria-label={`Magnitude ${f.magnitude_pct} percent`}>
                        <div className={`h-2 rounded-full ${classes.accent}`} style={{ width: `${f.magnitude_pct}%` }} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500 capitalize">{f.direction} risk - {f.magnitude_pct}% strength</p>
                </div>
            </div>
        </li>
    );
}

export default function UnderstandMyRisk() {
    const { status, patientState, patientId, error: patientError, refresh } = usePatientState();
    const ready = status === 'ready';
    const { data, error, isLoading, retry } = useBundleFetch(
        () => ready
            ? fetchUnderstandMyRisk({ patient_state: patientState })
            : Promise.resolve({ data: null, error: null }),
        [ready ? patientId : null],
    );

    const [showAdvanced, setShowAdvanced] = useState(false);
    const [advanced, setAdvanced] = useState(null);
    const [advancedLoading, setAdvancedLoading] = useState(false);

    const toggle = async () => {
        if (!showAdvanced && !advanced && patientState) {
            setAdvancedLoading(true);
            const { data: a, error: apiError } = await request('/xai/explain_risk', {
                method: 'POST',
                body: JSON.stringify(patientState),
            });
            if (apiError) {
                console.error("XAI Error:", apiError);
            }
            setAdvanced(a);
            setAdvancedLoading(false);
        }
        setShowAdvanced((s) => !s);
    };

    return (
        <C1PageShell
            title={data?.page_title || 'Understand My Risk'}
            subtitle={data?.page_subtitle}
            primaryAction={ready ? data?.primary_action : null}
            isLoading={ready && isLoading}
            error={ready ? error : null}
            onRetry={retry}
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                {data && (
                    <>
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-[auto_1fr] gap-6 items-center rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6">
                            <AnimatedRiskGauge
                                riskLevel={data.risk_level}
                                confidence={data.risk_confidence}
                                severityColor={data.risk_render.severity_color}
                                iconHint={data.risk_render.icon_hint}
                                sublabel={`${Math.round(data.risk_confidence * 100)}% confidence`}
                            />
                            <div>
                                <p className="text-xs uppercase tracking-wider text-slate-500">In one sentence</p>
                                <p className="mt-2 text-lg font-medium text-slate-900 dark:text-slate-100">{data.plain_english_summary}</p>
                            </div>
                        </div>
                        <h2 className="mt-8 text-lg font-semibold text-slate-900 dark:text-slate-100">What is pushing this up or down</h2>
                        <ul className="mt-3 space-y-3">
                            {data.top_factors.map((f) => <FactorCard key={f.feature} f={f} />)}
                        </ul>
                        {data.advanced_available && (
                            <div className="mt-6">
                                <button type="button" onClick={toggle}
                                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800">
                                    {showAdvanced ? <ChevronUp aria-hidden="true" className="w-4 h-4" /> : <ChevronDown aria-hidden="true" className="w-4 h-4" />}
                                    {data.advanced_label}
                                </button>
                                {showAdvanced && (
                                    <div className="mt-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40 p-4">
                                        {advancedLoading ? (
                                            <p className="text-sm text-slate-500">Loading SHAP waterfall...</p>
                                        ) : advanced ? (
                                            <pre className="text-xs overflow-x-auto text-slate-800 dark:text-slate-200">{JSON.stringify(advanced, null, 2)}</pre>
                                        ) : (
                                            <p className="text-sm text-slate-500">Could not load the technical breakdown.</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                )}
            </PatientStateGate>
        </C1PageShell>
    );
}
