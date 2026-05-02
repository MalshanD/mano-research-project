/* ============================================================
   MANO AMISE — Intervention Sequencer
   
   Multi-step treatment planning: build a sequence of interventions
   and see the cumulative trajectory + risk at each milestone.
   ============================================================ */
import { useState, useCallback, useEffect } from 'react';
import { getPatient, runSequence } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ListOrdered, Plus, Trash2, Play, Loader, AlertTriangle,
    ArrowRight, ChevronDown
} from 'lucide-react';

const INTERVENTIONS = [
    { id: 0, name: 'Control', color: '#64748b' },
    { id: 1, name: 'Wellness App', color: '#22d3ee' },
    { id: 2, name: 'CBT', color: '#a78bfa' },
    { id: 3, name: 'Exercise', color: '#34d399' },
    { id: 4, name: 'Medication', color: '#fb923c' },
];

/* ── Build patient state ─────────────────────────── */
function buildPatientState(patient) {
    if (!patient) return null;

    // Use actual vitals stored in DB; fall back to component1 if missing
    let dynamic_history;
    if (patient.latest_vitals && patient.latest_vitals.length === 7) {
        dynamic_history = patient.latest_vitals.map(v => ({
            sleep_hours: v.sleep_hours,
            sleep_quality: v.sleep_quality,
            heart_rate: v.heart_rate,
            stress_level: v.stress_level,
        }));
    } else {
        dynamic_history = Array.from({ length: 7 }, () => ({
            sleep_hours: 6.5 + (Math.random() - 0.5),
            sleep_quality: 0.6 + (Math.random() - 0.5) * 0.2,
            heart_rate: 75 + (Math.random() - 0.5) * 10,
            stress_level: 0.5 + (Math.random() - 0.5) * 0.2,
        }));
    }

    // Use the actual 20-dim feature vector stored in the patient record
    const static_features =
        patient.static_features && patient.static_features.length === 20
            ? patient.static_features
            : Array(20).fill(0);

    return { static_data: { features: static_features }, dynamic_history };
}

/* ── Risk badge ──────────────────────────────────── */
function RiskBadge({ risk, size = 'normal' }) {
    if (!risk) return null;
    const colorMap = { Low: 'var(--safe)', Medium: 'var(--caution)', High: 'var(--risk)' };
    const c = colorMap[risk.current_risk_class] || 'var(--text-muted)';
    return (
        <span style={{
            fontSize: size === 'small' ? '0.85rem' : '1.2rem',
            fontWeight: 700, color: c, fontFamily: 'var(--font-data)',
        }}>
            {risk.current_risk_class}
        </span>
    );
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function InterventionSequencer() {
    const { patientId } = usePatient();
    const [selectedId, setSelectedId] = useState(null);
    const [patientData, setPatientData] = useState(null);

    // Sequence builder
    const [steps, setSteps] = useState([
        { intervention_type: 2, intensity: 0.6 },
        { intervention_type: 3, intensity: 0.5 },
    ]);

    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /* ── Patient selection ────────────────────── */
    const handleSelectPatient = useCallback(async (id) => {
        setSelectedId(id);
        setResult(null);
        setError(null);
        const { data, error: err } = await getPatient(id);
        if (err) { setError(err); return; }
        setPatientData(data);
    }, []);

    /* ── Auto-load logged-in user's patient ───── */
    useEffect(() => {
        if (patientId) handleSelectPatient(patientId);
    }, [patientId]); // eslint-disable-line react-hooks/exhaustive-deps

    /* ── Step management ──────────────────────── */
    const addStep = () => {
        if (steps.length >= 5) return;
        setSteps([...steps, { intervention_type: 1, intensity: 0.5 }]);
    };

    const removeStep = (i) => {
        if (steps.length <= 1) return;
        setSteps(steps.filter((_, idx) => idx !== i));
    };

    const updateStep = (i, field, value) => {
        const next = [...steps];
        next[i] = { ...next[i], [field]: value };
        setSteps(next);
    };

    /* ── Run sequence ─────────────────────────── */
    const handleRun = useCallback(async () => {
        if (!patientData) return;
        setLoading(true);
        setError(null);
        setResult(null);

        const state = buildPatientState(patientData);
        const { data, error: err } = await runSequence({ patient_state: state, steps });
        setLoading(false);

        if (err) { setError(err); return; }
        setResult(data);
    }, [patientData, steps]);

    /* ── Build combined trajectory chart data ─── */
    const chartData = [];
    if (result) {
        result.steps.forEach((step, si) => {
            step.projected_vitals.forEach((v, di) => {
                chartData.push({
                    day: si * 7 + di + 1,
                    label: `S${si + 1} D${di + 1}`,
                    sleep_hours: v.sleep_hours,
                    heart_rate: v.heart_rate,
                    stress_level: v.stress_level,
                    stepName: step.intervention_name,
                    stepColor: INTERVENTIONS.find(x => x.name === step.intervention_name)?.color || '#64748b',
                });
            });
        });
    }

    return (
        <motion.div
            className="page"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
        >
            {/* Header */}
            <header className="page-header">
                <div>
                    <h1 style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                        <ListOrdered size={28} />
                        Intervention Sequencer
                    </h1>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                        Chain multiple interventions to model multi-phase treatment plans
                    </p>
                </div>
            </header>



            {/* Step Builder */}
            {selectedId && patientData && (
                <div className="glass-card" style={{ marginBottom: 'var(--sp-5)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-3)' }}>
                        <div className="data-label">Treatment Sequence ({steps.length} steps • {steps.length * 7} days)</div>
                        <button
                            onClick={addStep}
                            disabled={steps.length >= 5}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 4,
                                padding: '6px 12px', borderRadius: 8,
                                background: steps.length >= 5 ? 'var(--surface)' : 'rgba(99,102,241,0.15)',
                                border: 'none', color: steps.length >= 5 ? 'var(--text-muted)' : 'var(--predict)',
                                cursor: steps.length >= 5 ? 'not-allowed' : 'pointer',
                                fontSize: '0.8rem', fontWeight: 600,
                            }}
                        >
                            <Plus size={14} /> Add Step
                        </button>
                    </div>

                    {steps.map((step, i) => {
                        const intervention = INTERVENTIONS.find(x => x.id === step.intervention_type) || INTERVENTIONS[0];
                        return (
                            <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
                                padding: 'var(--sp-2) var(--sp-3)', marginBottom: 'var(--sp-2)',
                                borderRadius: 8, background: 'var(--surface)',
                                borderLeft: `3px solid ${intervention.color}`,
                            }}>
                                <span style={{
                                    fontFamily: 'var(--font-data)', fontSize: '0.8rem',
                                    color: 'var(--text-muted)', minWidth: 28,
                                }}>
                                    #{i + 1}
                                </span>

                                <select
                                    value={step.intervention_type}
                                    onChange={(e) => updateStep(i, 'intervention_type', parseInt(e.target.value))}
                                    style={{
                                        flex: 1, padding: '6px 8px',
                                        background: 'var(--void)', border: '1px solid var(--border)',
                                        borderRadius: 6, color: 'var(--text-primary)',
                                        fontSize: '0.85rem',
                                    }}
                                >
                                    {INTERVENTIONS.map(int => (
                                        <option key={int.id} value={int.id}>{int.name}</option>
                                    ))}
                                </select>

                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
                                    <span className="data-label" style={{ fontSize: '0.7rem' }}>
                                        {(step.intensity * 100).toFixed(0)}%
                                    </span>
                                    <input
                                        type="range" min="0.1" max="1" step="0.05"
                                        value={step.intensity}
                                        onChange={(e) => updateStep(i, 'intensity', parseFloat(e.target.value))}
                                        style={{ width: 80, accentColor: intervention.color }}
                                    />
                                </div>

                                <button
                                    onClick={() => removeStep(i)}
                                    disabled={steps.length <= 1}
                                    style={{
                                        background: 'none', border: 'none',
                                        color: steps.length <= 1 ? 'var(--border)' : 'var(--risk)',
                                        cursor: steps.length <= 1 ? 'not-allowed' : 'pointer',
                                        padding: 4,
                                    }}
                                >
                                    <Trash2 size={14} />
                                </button>

                                {i < steps.length - 1 && (
                                    <ArrowRight size={14} color="var(--text-muted)"
                                        style={{ position: 'absolute', right: -20 }} />
                                )}
                            </div>
                        );
                    })}

                    {/* Run Button */}
                    <button
                        onClick={handleRun}
                        disabled={loading}
                        style={{
                            marginTop: 'var(--sp-3)', width: '100%',
                            padding: 'var(--sp-2) var(--sp-4)',
                            borderRadius: 8, border: 'none',
                            background: 'linear-gradient(135deg, var(--predict), var(--safe))',
                            color: '#fff', fontSize: '0.95rem', fontWeight: 600,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                            opacity: loading ? 0.6 : 1,
                        }}
                    >
                        {loading ? (
                            <><Loader size={16} className="spin" /> Simulating {steps.length} steps...</>
                        ) : (
                            <><Play size={16} /> Run Sequence ({steps.length * 7} days)</>
                        )}
                    </button>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card" style={{
                    borderColor: 'var(--risk)', color: 'var(--risk)', marginBottom: 'var(--sp-5)',
                }}>
                    <AlertTriangle size={16} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof error === 'string' ? error : 'Sequencing failed.'}
                </div>
            )}

            {/* Results */}
            <AnimatePresence>
                {result && !loading && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        {/* Summary */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-5)',
                            borderLeft: `3px solid ${result.total_risk_reduction > 0 ? 'var(--safe)' : 'var(--caution)'}`,
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.7 }}>
                                {result.summary}
                            </p>
                        </div>

                        {/* Risk Timeline */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Risk Progression
                        </h2>

                        <div style={{
                            display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
                            marginBottom: 'var(--sp-4)', flexWrap: 'wrap',
                        }}>
                            {/* Baseline */}
                            <div style={{
                                padding: 'var(--sp-2) var(--sp-3)',
                                background: 'var(--surface)', borderRadius: 8,
                                textAlign: 'center',
                            }}>
                                <div className="data-label" style={{ fontSize: '0.65rem' }}>Baseline</div>
                                <RiskBadge risk={result.baseline_risk} size="small" />
                            </div>

                            {result.steps.map((step, i) => {
                                const intColor = INTERVENTIONS.find(x => x.name === step.intervention_name)?.color || '#64748b';
                                return (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                                        <ArrowRight size={14} color="var(--text-muted)" />
                                        <div style={{
                                            padding: 'var(--sp-2) var(--sp-3)',
                                            background: 'var(--surface)', borderRadius: 8,
                                            borderTop: `2px solid ${intColor}`,
                                            textAlign: 'center',
                                        }}>
                                            <div className="data-label" style={{ fontSize: '0.65rem' }}>
                                                #{step.step_number} {step.intervention_name}
                                            </div>
                                            <RiskBadge risk={step.risk_after} size="small" />
                                            <div style={{
                                                fontSize: '0.65rem',
                                                fontFamily: 'var(--font-data)',
                                                color: step.risk_delta_from_previous > 0 ? 'var(--safe)' : 'var(--risk)',
                                            }}>
                                                Δ {step.risk_delta_from_previous > 0 ? '+' : ''}{(step.risk_delta_from_previous * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}

                            <ArrowRight size={14} color="var(--text-muted)" />
                            <div style={{
                                padding: 'var(--sp-2) var(--sp-3)',
                                background: result.total_risk_reduction > 0
                                    ? 'rgba(45, 212, 191, 0.1)' : 'rgba(255, 76, 76, 0.1)',
                                borderRadius: 8, textAlign: 'center',
                                border: `1px solid ${result.total_risk_reduction > 0 ? 'var(--safe)' : 'var(--risk)'}`,
                            }}>
                                <div className="data-label" style={{ fontSize: '0.65rem' }}>Total Δ</div>
                                <span style={{
                                    fontFamily: 'var(--font-data)',
                                    fontSize: '1rem', fontWeight: 700,
                                    color: result.total_risk_reduction > 0 ? 'var(--safe)' : 'var(--risk)',
                                }}>
                                    {result.total_risk_reduction > 0 ? '+' : ''}{(result.total_risk_reduction * 100).toFixed(1)}%
                                </span>
                            </div>
                        </div>

                        {/* Combined Trajectory Chart */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Vital Signs Trajectory ({chartData.length} days)
                        </h2>

                        <div className="glass-card" style={{ marginBottom: 'var(--sp-5)', padding: 'var(--sp-3)' }}>
                            <ResponsiveContainer width="100%" height={250}>
                                <AreaChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis
                                        dataKey="day"
                                        tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                        label={{ value: 'Day', position: 'insideBottomRight', fill: 'var(--text-muted)', fontSize: 10 }}
                                    />
                                    <YAxis
                                        tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: 'var(--card)',
                                            border: '1px solid var(--border)',
                                            borderRadius: 8,
                                            color: 'var(--text-primary)',
                                            fontSize: '0.8rem',
                                        }}
                                        labelFormatter={(v) => `Day ${v}`}
                                    />
                                    <Area
                                        type="monotone" dataKey="heart_rate"
                                        stroke="#f87171" fill="#f87171" fillOpacity={0.1}
                                        strokeWidth={2} name="Heart Rate"
                                    />
                                    <Area
                                        type="monotone" dataKey="sleep_hours"
                                        stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.1}
                                        strokeWidth={2} name="Sleep Hours"
                                    />
                                    <Area
                                        type="monotone" dataKey="stress_level"
                                        stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.1}
                                        strokeWidth={2} name="Stress Level"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Step Details */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Step Details
                        </h2>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                            gap: 'var(--sp-3)', marginBottom: 'var(--sp-5)',
                        }}>
                            {result.steps.map((step, i) => {
                                const intColor = INTERVENTIONS.find(x => x.name === step.intervention_name)?.color || '#64748b';
                                return (
                                    <motion.div
                                        key={i}
                                        className="glass-card"
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.1 }}
                                        style={{ borderLeft: `3px solid ${intColor}` }}
                                    >
                                        <div className="data-label" style={{ fontSize: '0.7rem' }}>
                                            Step {step.step_number} • Days {(i * 7) + 1}–{(i + 1) * 7}
                                        </div>
                                        <div style={{ fontSize: '1rem', fontWeight: 600, margin: 'var(--sp-1) 0' }}>
                                            {step.intervention_name}
                                        </div>
                                        <div style={{
                                            display: 'flex', justifyContent: 'space-between',
                                            alignItems: 'flex-end',
                                        }}>
                                            <div>
                                                <span className="data-label" style={{ fontSize: '0.65rem' }}>Intensity</span>
                                                <div style={{
                                                    fontFamily: 'var(--font-data)', fontSize: '0.9rem',
                                                    color: intColor,
                                                }}>
                                                    {(step.intensity * 100).toFixed(0)}%
                                                </div>
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <span className="data-label" style={{ fontSize: '0.65rem' }}>Risk After</span>
                                                <div><RiskBadge risk={step.risk_after} size="small" /></div>
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Loading profile */}
            {!selectedId && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <ListOrdered size={48} color="var(--text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.3 }} />
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>Loading your treatment plan...</p>
                </div>
            )}
        </motion.div>
    );
}
