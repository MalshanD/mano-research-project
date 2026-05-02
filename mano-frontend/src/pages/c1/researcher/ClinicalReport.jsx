/**
 * Clinical Report + Batch Simulation (Researcher).
 *
 * Two tabs. The Clinical Report tab calls /reports/generate; the
 * Batch tab calls /simulation/simulate_batch. Both run against the
 * live patient state — never mock data.
 */

import { useState } from 'react';
import C1PageShell from '../../../components/c1/C1PageShell';
import PatientStateGate from '../../../components/c1/PatientStateGate';
import { request } from '../../../api/client';
import { usePatientState } from '../../../lib/c1/usePatientState';
import { FileText, Layers } from 'lucide-react';

export default function ClinicalReport() {
    const { status, patientState, error: patientError, refresh } = usePatientState();
    const [tab, setTab] = useState('report');
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [opError, setOpError] = useState(null);

    const runReport = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await request('/reports/generate', {
            method: 'POST',
            body: JSON.stringify({ patient_state: patientState }),
        });
        setResult(data); setOpError(error); setBusy(false);
    };

    const runBatch = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await request('/simulation/simulate_batch', {
            method: 'POST',
            body: JSON.stringify({
                patient_state: patientState,
                interventions: [
                    { intervention_type: 1, intensity: 0.3 },
                    { intervention_type: 2, intensity: 0.5 },
                    { intervention_type: 3, intensity: 0.7 },
                ],
            }),
        });
        setResult(data); setOpError(error); setBusy(false);
    };

    return (
        <C1PageShell
            title="Clinical Report + Batch Simulation"
            subtitle="Generate a structured clinical report or sweep a batch of intervention vectors against the live patient state."
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                <div className="mt-4 flex gap-2">
                    <button
                        type="button"
                        onClick={() => { setTab('report'); setResult(null); setOpError(null); }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${tab === 'report' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'}`}
                    >
                        Clinical report
                    </button>
                    <button
                        type="button"
                        onClick={() => { setTab('batch'); setResult(null); setOpError(null); }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${tab === 'batch' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'}`}
                    >
                        Batch simulation
                    </button>
                </div>

                <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    {tab === 'report' ? (
                        <>
                            <div className="flex items-start gap-3">
                                <FileText className="w-5 h-5 text-emerald-600 mt-0.5" />
                                <div>
                                    <h2 className="text-base font-semibold">Generate a clinical report</h2>
                                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                                        Returns a structured summary suitable for sharing with a
                                        licensed mental-health professional.
                                    </p>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={runReport}
                                disabled={busy}
                                className="mt-4 inline-flex items-center gap-1 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-2 text-sm font-medium disabled:opacity-50"
                            >
                                {busy ? 'Generating…' : 'Generate report'}
                            </button>
                        </>
                    ) : (
                        <>
                            <div className="flex items-start gap-3">
                                <Layers className="w-5 h-5 text-emerald-600 mt-0.5" />
                                <div>
                                    <h2 className="text-base font-semibold">Run a batch simulation</h2>
                                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                                        Simulates three default intervention vectors against the
                                        chosen patient state in one round-trip.
                                    </p>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={runBatch}
                                disabled={busy}
                                className="mt-4 inline-flex items-center gap-1 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-2 text-sm font-medium disabled:opacity-50"
                            >
                                {busy ? 'Sweeping…' : 'Run batch'}
                            </button>
                        </>
                    )}

                    {opError && <p className="mt-3 text-sm text-rose-700">Operation failed: {String(opError)}</p>}
                    {result && (
                        <pre className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-xs overflow-x-auto max-h-96">
                            {JSON.stringify(result, null, 2)}
                        </pre>
                    )}
                </div>
            </PatientStateGate>
        </C1PageShell>
    );
}
