/**
 * Model Diagnostics (Researcher) — health + load status of the five
 * frozen models, plus the trajectory-alert ring buffer + recent cohort
 * audits.
 */

import { useEffect, useState } from 'react';
import C1PageShell from '../../../components/c1/C1PageShell';
import { request, requestRoot } from '../../../api/client';
import { Activity, Cpu, Database, Server, Wifi, Boxes } from 'lucide-react';

function StatusRow({ icon: Icon, label, value, ok }) {
    const tone = ok === true ? 'text-emerald-700 bg-emerald-50' :
                 ok === false ? 'text-rose-700 bg-rose-50' :
                 'text-slate-700 bg-slate-50';
    return (
        <li className="flex items-center justify-between gap-3 py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <div className="flex items-center gap-2">
                <Icon aria-hidden="true" className="w-4 h-4 text-slate-400" />
                <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${tone}`}>{value}</span>
        </li>
    );
}

export default function ModelDiagnostics() {
    const [health, setHealth] = useState(null);
    const [cohorts, setCohorts] = useState(null);

    useEffect(() => {
        (async () => {
            const { data: h } = await requestRoot('/health');
            setHealth(h);
            const { data: c } = await request('/research/cohorts');
            setCohorts(c);
        })();
    }, []);

    const models = health?.models || {};
    return (
        <C1PageShell
            title="Model Diagnostics"
            subtitle="Live readiness of the frozen Component-1 models, infrastructure, and the latest synthetic-cohort audits."
        >
            <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-slate-500" />
                        <h2 className="text-base font-semibold">Frozen models</h2>
                    </div>
                    <ul className="mt-3">
                        {['lstm', 'simulator', 'agent', 'timegan', 'ctgan'].map((k) => (
                            <StatusRow
                                key={k} icon={Activity} label={k.toUpperCase()}
                                value={models[k] ? 'Loaded' : 'Not loaded'} ok={models[k]}
                            />
                        ))}
                    </ul>
                    <p className="mt-3 text-xs text-slate-500">
                        GPU enabled: {String(health?.gpu_enabled || false)} · device: {health?.device || '—'}
                    </p>
                </div>

                <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                    <div className="flex items-center gap-2">
                        <Server className="w-5 h-5 text-slate-500" />
                        <h2 className="text-base font-semibold">Infrastructure</h2>
                    </div>
                    <ul className="mt-3">
                        <StatusRow
                            icon={Database} label="Database"
                            value={health?.db?.reachable ? 'Reachable' : 'Down'}
                            ok={!!health?.db?.reachable}
                        />
                        <StatusRow
                            icon={Boxes} label={`Cache (${health?.cache?.backend || '—'})`}
                            value={health?.cache?.reachable ? 'OK' : 'Degraded'}
                            ok={!!health?.cache?.reachable}
                        />
                        <StatusRow
                            icon={Wifi} label={`Event bus (${health?.event_bus?.backend || '—'})`}
                            value={health?.event_bus?.reachable ? 'OK' : 'Degraded'}
                            ok={!!health?.event_bus?.reachable}
                        />
                        <StatusRow
                            icon={Activity} label="Scheduler"
                            value={health?.scheduler?.running ? 'Running' : 'Stopped'}
                            ok={!!health?.scheduler?.running}
                        />
                    </ul>
                </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                <h2 className="text-base font-semibold">Recent synthetic cohorts</h2>
                <p className="mt-1 text-xs text-slate-500">
                    Each cohort ships with an embedded audit (k-anonymity, membership-inference adversary, downstream LSTM check).
                </p>
                {cohorts?.cohorts?.length ? (
                    <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
                        {cohorts.cohorts.map((c) => (
                            <li key={c.cohort_id} className="py-2 flex items-center justify-between text-sm">
                                <div className="min-w-0">
                                    <p className="font-medium text-slate-900 dark:text-slate-100 truncate">{c.cohort_id}</p>
                                    <p className="text-xs text-slate-500">
                                        {c.num_patients} patients · seed {c.seed} · audit: {c.audit_overall_severity || 'n/a'}
                                    </p>
                                </div>
                                <a href={`/api/v1/research/cohorts/${c.cohort_id}`} target="_blank" rel="noopener noreferrer" className="text-emerald-700 text-xs underline">
                                    Manifest
                                </a>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-slate-500">No cohorts have been generated yet.</p>
                )}
            </div>
        </C1PageShell>
    );
}
