/**
 * Simulation Lab (Researcher) — rehearsal + dose-response over the live patient state.
 */
import { useState } from 'react';
import C1PageShell from '../../../components/c1/C1PageShell';
import PatientStateGate from '../../../components/c1/PatientStateGate';
import { rehearsePlan, sweepDoseResponse } from '../../../lib/c1/apiClient';
import { usePatientState } from '../../../lib/c1/usePatientState';
import { Beaker, Wand2 } from 'lucide-react';

export default function SimulationLab() {
    const { status, patientState, error: patientError, refresh } = usePatientState();
    const [tab, setTab] = useState('rehearsal');
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [opError, setOpError] = useState(null);

    const runRehearsal = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await rehearsePlan({ patient_state: patientState, horizon_days: 14 });
        setResult(data); setOpError(error); setBusy(false);
    };

    const runDoseResponse = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await sweepDoseResponse({ patient_state: patientState, intervention_type: 2, horizon_days: 7 });
        setResult(data); setOpError(error); setBusy(false);
    };

    return (
        <C1PageShell title="Simulation Lab" subtitle="Closed-loop rehearsal and dose-response sweeps over the frozen models, driven by the live patient state.">
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                <div className="mt-4 flex gap-2">
                    <button type="button" onClick={() => { setTab('rehearsal'); setResult(null); setOpError(null); }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${tab === 'rehearsal' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'}`}>
                        Adaptive Rehearsal
                    </button>
                    <button type="button" onClick={() => { setTab('dose'); setResult(null); setOpError(null); }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${tab === 'dose' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'}`}>
                        Dose-Response Sweep
                    </button>
                </div>
                <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    {tab === 'rehearsal' ? (
                        <>
                            <div className="flex items-start gap-3">
                                <Beaker className="w-5 h-5 text-emerald-600 mt-0.5" />
                                <div>
                                    <h2 className="text-base font-semibold">Adaptive Intervention Rehearsal</h2>
                                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Multi-day closed-loop plan with mid-plan PPO swaps.</p>
                                </div>
                            </div>
                            <button type="button" onClick={runRehearsal} disabled={busy}
                                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-2 text-sm font-medium disabled:opacity-50">
                                {busy ? 'Running...' : 'Run rehearsal'}
                            </button>
                        </>
                    ) : (
                        <>
                            <div className="flex items-start gap-3">
                                <Wand2 className="w-5 h-5 text-emerald-600 mt-0.5" />
                                <div>
                                    <h2 className="text-base font-semibold">Dose-Response Sweep</h2>
                                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Sweep the intensity axis for one intervention.</p>
                                </div>
                            </div>
                            <button type="button" onClick={runDoseResponse} disabled={busy}
                                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-2 text-sm font-medium disabled:opacity-50">
                                {busy ? 'Running...' : 'Sweep CBT'}
                            </button>
                        </>
                    )}
                    {opError && <p className="mt-3 text-sm text-rose-700">Operation failed: {String(opError)}</p>}
                    {result && <pre className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-xs overflow-x-auto max-h-96">{JSON.stringify(result, null, 2)}</pre>}
                </div>
            </PatientStateGate>
        </C1PageShell>
    );
}
