/** Uncertainty Explorer (Researcher) - MC Dropout against live patient state. */
import { useState } from 'react';
import C1PageShell from '../../../components/c1/C1PageShell';
import PatientStateGate from '../../../components/c1/PatientStateGate';
import { request } from '../../../api/client';
import { usePatientState } from '../../../lib/c1/usePatientState';
import { Gauge } from 'lucide-react';

export default function UncertaintyExplorer() {
    const { status, patientState, error: patientError, refresh } = usePatientState();
    const [n, setN] = useState(30);
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [opError, setOpError] = useState(null);

    const run = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await request('/uncertainty/evaluate', {
            method: 'POST',
            body: JSON.stringify({ patient_state: patientState, n_samples: n }),
        });
        setResult(data); setOpError(error); setBusy(false);
    };

    return (
        <C1PageShell title="Uncertainty Explorer" subtitle="MC Dropout - mean, std, mutual information, predictive entropy for the live patient state.">
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    <div className="flex items-center gap-2">
                        <Gauge className="w-5 h-5 text-slate-500" />
                        <h2 className="text-base font-semibold">MC Dropout</h2>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                        <label className="text-sm text-slate-700 dark:text-slate-300">
                            Samples
                            <input type="number" min="5" max="200" step="5" value={n} onChange={(e) => setN(Number(e.target.value))}
                                className="ml-2 w-20 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 text-sm" />
                        </label>
                        <button type="button" onClick={run} disabled={busy}
                            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-1.5 text-sm font-medium disabled:opacity-50">
                            {busy ? 'Sampling...' : 'Evaluate'}
                        </button>
                    </div>
                    {opError && <p className="mt-3 text-sm text-rose-700">Operation failed: {String(opError)}</p>}
                    {result && (
                        <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3">
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-sm">
                                <p className="text-xs text-slate-500">Predictive entropy</p>
                                <p className="mt-1 font-semibold">{result.predictive_entropy?.toFixed?.(4)}</p>
                            </div>
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-sm">
                                <p className="text-xs text-slate-500">Mutual information (epistemic)</p>
                                <p className="mt-1 font-semibold">{result.mutual_information?.toFixed?.(4)}</p>
                            </div>
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-sm">
                                <p className="text-xs text-slate-500">Prediction stability</p>
                                <p className="mt-1 font-semibold">{result.prediction_stability?.toFixed?.(2)}</p>
                            </div>
                        </div>
                    )}
                    {result && <pre className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-xs overflow-x-auto max-h-72">{JSON.stringify(result, null, 2)}</pre>}
                </div>
            </PatientStateGate>
        </C1PageShell>
    );
}
