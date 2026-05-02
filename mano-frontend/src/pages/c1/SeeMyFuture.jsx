/**
 * See My Future — what-if simulator with weather pre-fill + Future-Self narratives.
 * NO mock fallback — gated by PatientStateGate.
 */
import { useNavigate } from 'react-router-dom';
import C1PageShell, { useBundleFetch } from '../../components/c1/C1PageShell';
import BeforeAfterCard from '../../components/c1/BeforeAfterCard';
import SeverityChip from '../../components/c1/SeverityChip';
import PatientStateGate from '../../components/c1/PatientStateGate';
import { fetchSeeMyFuture } from '../../lib/c1/apiClient';
import { usePatientState } from '../../lib/c1/usePatientState';
import { Sun } from 'lucide-react';

export default function SeeMyFuture() {
    const navigate = useNavigate();
    const { status, patientState, patientId, error: patientError, refresh } = usePatientState();
    const ready = status === 'ready';

    const { data, error, isLoading, retry } = useBundleFetch(
        () => ready
            ? fetchSeeMyFuture({ patient_state: patientState })
            : Promise.resolve({ data: null, error: null }),
        [ready ? patientId : null],
    );

    const handleTryThis = (arm) => navigate(`/c1/recommendation?prefill=${arm}`);
    const currentRender = data ? data.scenarios.find((s) => s.label === 'Continue current plan')?.render : null;

    return (
        <C1PageShell
            title={data?.page_title || 'See My Future'}
            subtitle={data?.page_subtitle}
            primaryAction={ready ? data?.primary_action : null}
            onPrimary={() => navigate('/c1/recommendation')}
            isLoading={ready && isLoading}
            error={ready ? error : null}
            onRetry={retry}
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                {data && (
                    <>
                        <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 p-4 flex items-start gap-3">
                            <Sun aria-hidden="true" className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
                            <div className="text-sm text-slate-700 dark:text-slate-300">
                                <p className="font-medium">{data.weather_prefill.location}</p>
                                <p className="mt-1">{data.advisory}{data.weather_prefill.recommendation ? ` ${data.weather_prefill.recommendation}` : ''}</p>
                            </div>
                        </div>
                        <div className="mt-4 flex items-center gap-3">
                            <span className="text-xs uppercase tracking-wider text-slate-500">Where you are now</span>
                            <SeverityChip
                                size="sm"
                                render={{
                                    severity_color: currentRender?.severity_color || 'amber-500',
                                    icon_hint: 'shield',
                                    microcopy: `${data.current_risk_level} risk - ${Math.round(data.current_high_risk_probability * 100)}% high-risk probability`,
                                }}
                            />
                        </div>
                        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {data.scenarios.map((s) => (
                                <BeforeAfterCard
                                    key={`${s.intervention_type}-${s.label}`}
                                    title={s.label}
                                    beforeRiskLevel={data.current_risk_level}
                                    beforeHighProb={data.current_high_risk_probability}
                                    beforeRender={{ severity_color: 'amber-500', icon_hint: 'shield', microcopy: 'Right now' }}
                                    afterRiskLevel={s.projected_risk_level}
                                    afterHighProb={s.projected_high_risk_probability}
                                    afterRender={s.render}
                                    deltaRender={s.render}
                                    narrative={s.narrative}
                                    onTryThisPlan={() => handleTryThis(s.intervention_type)}
                                />
                            ))}
                        </div>
                    </>
                )}
            </PatientStateGate>
        </C1PageShell>
    );
}
