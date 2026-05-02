/**
 * Intervention Sequencer (Researcher) — sequential composition of
 * multiple interventions over a multi-week horizon. Sits on top of
 * /api/v1/sequence/run_sequence and renders the per-week trajectory.
 *
 * NO mock fallback — gated by PatientStateGate.
 */

import { useState } from 'react';
import C1PageShell from '../../../components/c1/C1PageShell';
import PatientStateGate from '../../../components/c1/PatientStateGate';
import { request } from '../../../api/client';
import { usePatientState } from '../../../lib/c1/usePatientState';
import { ListOrdered, Plus, Trash2 } from 'lucide-react';

const ARMS = [
    { id: 0, label: 'Control' },
    { id: 1, label: 'Wellness app' },
    { id: 2, label: 'CBT' },
    { id: 3, label: 'Exercise' },
    { id: 4, label: 'Medication' },
];

export default function InterventionSequencer() {
    const { status, patientState, error: patientError, refresh } = usePatientState();
    const [steps, setSteps] = useState([
        { intervention_type: 2, intensity: 0.5, weeks: 1 },
        { intervention_type: 3, intensity: 0.4, weeks: 1 },
    ]);
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const [opError, setOpError] = useState(null);

    const updateStep = (i, key, val) => {
        setSteps((s) => s.map((step, idx) => idx === i ? { ...step, [key]: val } : step));
    };
    const addStep = () => setSteps((s) => [...s, { intervention_type: 1, intensity: 0.5, weeks: 1 }]);
    const removeStep = (i) => setSteps((s) => s.filter((_, idx) => idx !== i));

    const run = async () => {
        if (!patientState) return;
        setBusy(true); setOpError(null);
        const { data, error } = await request('/sequence/run_sequence', {
            method: 'POST',
            body: JSON.stringify({ patient_state: patientState, sequence: steps }),
        });
        setResult(data); setOpError(error); setBusy(false);
    };

    return (
        <C1PageShell
            title="Intervention Sequencer"
            subtitle="Stack interventions across multiple weeks. Useful for studying combined arms and step-down protocols."
        >
            <PatientStateGate status={status} error={patientError} onRetry={refresh}>
                <div className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    <div className="flex items-center gap-2">
                        <ListOrdered className="w-5 h-5 text-slate-500" />
                        <h2 className="text-base font-semibold">Sequence steps</h2>
                    </div>
                    <ol className="mt-3 space-y-2">
                        {steps.map((s, i) => (
                            <li key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                                <span className="text-xs uppercase tracking-wider text-slate-500 w-12">Step {i + 1}</span>
                                <select
                                    value={s.intervention_type}
                                    onChange={(e) => updateStep(i, 'intervention_type', Number(e.target.value))}
                                    className="rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 text-sm"
                                    aria-label={`Intervention for step ${i + 1}`}
                                >
                                    {ARMS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                                </select>
                                <label className="text-xs text-slate-500">Intensity</label>
                                <input
                                    type="number" step="0.1" min="0" max="1"
                                    value={s.intensity}
                                    onChange={(e) => updateStep(i, 'intensity', Number(e.target.value))}
                                    className="w-20 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 text-sm"
                                />
                                <label className="text-xs text-slate-500">Weeks</label>
                                <input
                                    type="number" step="1" min="1" max="8"
                                    value={s.weeks}
                                    onChange={(e) => updateStep(i, 'weeks', Number(e.target.value))}
                                    className="w-16 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 text-sm"
                                />
                                <button
                                    type="button"
                                    onClick={() => removeStep(i)}
                                    aria-label={`Remove step ${i + 1}`}
                                    className="ml-auto text-slate-400 hover:text-rose-600"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </li>
                        ))}
                    </ol>
                    <div className="mt-3 flex gap-2">
                        <button
                            type="button"
                            onClick={addStep}
                            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
                        >
                            <Plus className="w-4 h-4" /> Add step
                        </button>
                        <button
                            type="button"
                            onClick={run}
                            disabled={busy}
                            className="inline-flex items-center gap-1 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
                        >
                            {busy ? 'Running…' : 'Run sequence'}
                        </button>
                    </div>
                    {opError && <p className="mt-3 text-sm text-rose-700">Operation failed: {String(opError)}</p>}
                    {result && (
                        <pre className="mt-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 p-3 text-xs overflow-x-auto max-h-72">
                            {JSON.stringify(result, null, 2)}
                        </pre>
                    )}
                </div>
            </PatientStateGate>
        </C1PageShell>
    );
}
