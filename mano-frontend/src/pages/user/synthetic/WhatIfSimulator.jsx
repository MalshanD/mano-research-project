/* ============================================================
   MANO AMISE — "What-If" Lifestyle Simulator
   
   Interactive Digital Twin: users adjust lifestyle sliders and
   instantly see projected health outcomes vs their baseline.
   ============================================================ */
import { useState, useCallback, useEffect } from 'react';
import { getPatient, simulateWhatIf } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    AreaChart, Area, LineChart, Line,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    SlidersHorizontal, Moon, Heart, Brain, Activity,
    TrendingDown, TrendingUp, Minus, ArrowRight, Loader
} from 'lucide-react';

/* ── Slider Config ───────────────────────────────── */
const SLIDERS = [
    { key: 'sleep_hours', label: 'Sleep Duration', icon: Moon, min: 0, max: 12, step: 0.5, unit: 'hrs', color: 'var(--safe)' },
    { key: 'sleep_quality', label: 'Sleep Quality', icon: Activity, min: 0, max: 1, step: 0.05, unit: '', color: 'var(--predict)' },
    { key: 'heart_rate', label: 'Resting Heart Rate', icon: Heart, min: 50, max: 120, step: 1, unit: 'bpm', color: 'var(--caution)' },
    { key: 'stress_level', label: 'Stress Level', icon: Brain, min: 0, max: 1, step: 0.05, unit: '', color: 'var(--risk)' },
];

/* ── Build initial patient state from DB record ──── */
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

    return {
        static_data: { features: static_features },
        dynamic_history,
    };
}

/* ── Compute current averages from patient history ─ */
function getCurrentAverages(patientState) {
    if (!patientState) return {};
    const hist = patientState.dynamic_history;
    return {
        sleep_hours: Math.round(hist.reduce((s, d) => s + d.sleep_hours, 0) / 7 * 10) / 10,
        sleep_quality: Math.round(hist.reduce((s, d) => s + d.sleep_quality, 0) / 7 * 100) / 100,
        heart_rate: Math.round(hist.reduce((s, d) => s + d.heart_rate, 0) / 7),
        stress_level: Math.round(hist.reduce((s, d) => s + d.stress_level, 0) / 7 * 100) / 100,
    };
}

/* ── Risk badge component ────────────────────────── */
function RiskBadge({ risk, label }) {
    if (!risk) return null;
    const colorMap = { Low: 'var(--safe)', Medium: 'var(--caution)', High: 'var(--risk)' };
    const color = colorMap[risk.current_risk_class] || 'var(--text-muted)';
    const confidence = (risk.confidence * 100).toFixed(0);

    return (
        <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-4)' }}>
            <div className="data-label" style={{ marginBottom: 'var(--sp-2)' }}>{label}</div>
            <div style={{
                fontSize: '1.6rem',
                fontWeight: 700,
                color,
                fontFamily: 'var(--font-data)',
            }}>
                {risk.current_risk_class}
            </div>
            <div className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                {confidence}% confidence
            </div>
            <div style={{ display: 'flex', gap: 'var(--sp-2)', justifyContent: 'center', marginTop: 'var(--sp-2)' }}>
                {['Low', 'Medium', 'High'].map((level, i) => (
                    <span key={level} style={{
                        fontSize: '0.7rem',
                        color: level === risk.current_risk_class ? color : 'var(--text-muted)',
                        fontFamily: 'var(--font-data)',
                    }}>
                        {level}: {(risk.probabilities[i] * 100).toFixed(0)}%
                    </span>
                ))}
            </div>
        </div>
    );
}

/* ── Delta indicator ─────────────────────────────── */
function DeltaIndicator({ delta }) {
    if (delta === null || delta === undefined) return null;
    const isGood = delta > 0.01;
    const isBad = delta < -0.01;
    const Icon = isGood ? TrendingDown : isBad ? TrendingUp : Minus;
    const color = isGood ? 'var(--safe)' : isBad ? 'var(--risk)' : 'var(--text-muted)';
    const label = isGood
        ? `${(delta * 100).toFixed(1)}% risk reduction`
        : isBad
            ? `${(Math.abs(delta) * 100).toFixed(1)}% risk increase`
            : 'Minimal change';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card"
            style={{
                textAlign: 'center',
                padding: 'var(--sp-4)',
                borderColor: color,
                borderWidth: '1px',
                borderStyle: 'solid',
            }}
        >
            <Icon size={28} color={color} style={{ marginBottom: 'var(--sp-2)' }} />
            <div style={{ fontSize: '1.2rem', fontWeight: 600, color, fontFamily: 'var(--font-data)' }}>
                {label}
            </div>
        </motion.div>
    );
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function WhatIfSimulator() {
    const { patientId } = usePatient();
    const [selectedId, setSelectedId] = useState(null);
    const [patientState, setPatientState] = useState(null);
    const [currentAvg, setCurrentAvg] = useState({});
    const [targets, setTargets] = useState({});
    const [blendDays, setBlendDays] = useState(3);
    const [result, setResult] = useState(null);
    const [simulating, setSimulating] = useState(false);
    const [error, setError] = useState(null);

    /* ── Load patient data ─────────────────────── */
    const handleSelectPatient = useCallback(async (id) => {
        setSelectedId(id);
        setResult(null);
        setError(null);

        const { data, error: err } = await getPatient(id);
        if (err) { setError(err); return; }

        const state = buildPatientState(data);
        setPatientState(state);

        const avg = getCurrentAverages(state);
        setCurrentAvg(avg);

        // Initialize targets to current averages
        setTargets({ ...avg });
    }, []);

    /* ── Run simulation ────────────────────────── */
    const handleSimulate = useCallback(async () => {
        if (!patientState) return;
        setSimulating(true);
        setError(null);

        const payload = {
            patient_state: patientState,
            lifestyle_targets: targets,
            blend_days: blendDays,
        };

        const { data, error: err } = await simulateWhatIf(payload);
        setSimulating(false);

        if (err) { setError(err); return; }
        setResult(data);
    }, [patientState, targets, blendDays]);

    /* ── Auto-load logged-in user's patient ───── */
    useEffect(() => {
        if (patientId) handleSelectPatient(patientId);
    }, [patientId]); // eslint-disable-line react-hooks/exhaustive-deps

    /* ── Build chart data ──────────────────────── */
    const chartData = result ? result.baseline_trajectory.map((b, i) => {
        const m = result.modified_trajectory[i];
        return {
            day: `Day ${b.day}`,
            base_sleep: b.sleep_hours,
            mod_sleep: m.sleep_hours,
            base_quality: b.sleep_quality,
            mod_quality: m.sleep_quality,
            base_hr: b.heart_rate,
            mod_hr: m.heart_rate,
            base_stress: b.stress_level,
            mod_stress: m.stress_level,
        };
    }) : [];

    /* ── Chart configurations ──────────────────── */
    const charts = [
        { title: 'Sleep Duration', baseKey: 'base_sleep', modKey: 'mod_sleep', color: 'var(--safe)', unit: 'hrs' },
        { title: 'Sleep Quality', baseKey: 'base_quality', modKey: 'mod_quality', color: 'var(--predict)', unit: '' },
        { title: 'Heart Rate', baseKey: 'base_hr', modKey: 'mod_hr', color: 'var(--caution)', unit: 'bpm' },
        { title: 'Stress Level', baseKey: 'base_stress', modKey: 'mod_stress', color: 'var(--risk)', unit: '' },
    ];

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
                        <SlidersHorizontal size={28} />
                        What-If Lifestyle Simulator
                    </h1>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                        Adjust your lifestyle parameters and see how your projected health trajectory changes
                    </p>
                </div>
            </header>



            {/* Main Controls */}
            <AnimatePresence>
                {patientState && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        {/* Lifestyle Sliders */}
                        <div className="glass-card" style={{ marginBottom: 'var(--sp-5)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-4)' }}>
                                <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Lifestyle Targets</h2>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                                    <span className="data-label">Blend window:</span>
                                    <select
                                        value={blendDays}
                                        onChange={(e) => setBlendDays(parseInt(e.target.value))}
                                        style={{
                                            padding: '4px 8px',
                                            background: 'var(--surface)',
                                            border: '1px solid var(--border)',
                                            borderRadius: 6,
                                            color: 'var(--text-primary)',
                                            fontSize: '0.85rem',
                                        }}
                                    >
                                        {[1, 2, 3, 4, 5, 6, 7].map(d => (
                                            <option key={d} value={d}>{d} day{d > 1 ? 's' : ''}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                gap: 'var(--sp-4)',
                            }}>
                                {SLIDERS.map(({ key, label, icon: Icon, min, max, step, unit, color }) => {
                                    const current = currentAvg[key];
                                    const target = targets[key] ?? current;
                                    const changed = current !== undefined && Math.abs(target - current) > step * 0.5;

                                    return (
                                        <div key={key} style={{
                                            padding: 'var(--sp-3)',
                                            background: 'var(--surface)',
                                            borderRadius: 12,
                                            border: changed ? `1px solid ${color}` : '1px solid var(--border)',
                                            transition: 'border-color var(--duration-normal) var(--ease-out)',
                                        }}>
                                            <div style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between',
                                                marginBottom: 'var(--sp-2)',
                                            }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                                                    <Icon size={16} color={color} />
                                                    <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{label}</span>
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                                                    {current !== undefined && (
                                                        <span className="data-label" style={{ fontSize: '0.75rem' }}>
                                                            now: {typeof current === 'number' && max <= 1
                                                                ? `${(current * 100).toFixed(0)}%`
                                                                : `${current}${unit}`}
                                                        </span>
                                                    )}
                                                    <ArrowRight size={12} color="var(--text-muted)" />
                                                    <span style={{
                                                        fontFamily: 'var(--font-data)',
                                                        fontSize: '0.85rem',
                                                        color: changed ? color : 'var(--text-primary)',
                                                        fontWeight: 600,
                                                    }}>
                                                        {max <= 1
                                                            ? `${(target * 100).toFixed(0)}%`
                                                            : `${target}${unit}`}
                                                    </span>
                                                </div>
                                            </div>

                                            <input
                                                type="range"
                                                min={min}
                                                max={max}
                                                step={step}
                                                value={target}
                                                onChange={(e) => setTargets(prev => ({
                                                    ...prev,
                                                    [key]: parseFloat(e.target.value),
                                                }))}
                                                style={{
                                                    width: '100%',
                                                    accentColor: color,
                                                    cursor: 'pointer',
                                                }}
                                            />
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Simulate Button */}
                            <div style={{ marginTop: 'var(--sp-4)', textAlign: 'center' }}>
                                <button
                                    className="btn-primary"
                                    onClick={handleSimulate}
                                    disabled={simulating}
                                    style={{
                                        minWidth: 220,
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: 'var(--sp-2)',
                                    }}
                                >
                                    {simulating ? (
                                        <>
                                            <Loader size={16} className="spin" />
                                            Simulating your future...
                                        </>
                                    ) : (
                                        <>
                                            <SlidersHorizontal size={16} />
                                            Simulate Lifestyle Change
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="glass-card" style={{
                                borderColor: 'var(--risk)',
                                color: 'var(--risk)',
                                marginBottom: 'var(--sp-5)',
                            }}>
                                ⚠ {typeof error === 'string' ? error : 'Simulation failed. Check backend connection.'}
                            </div>
                        )}

                        {/* Results */}
                        <AnimatePresence>
                            {result && (
                                <motion.div
                                    initial={{ opacity: 0, y: 30 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.5 }}
                                >
                                    {/* Risk Comparison */}
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: '1fr auto 1fr',
                                        gap: 'var(--sp-4)',
                                        marginBottom: 'var(--sp-5)',
                                        alignItems: 'center',
                                    }}>
                                        <RiskBadge risk={result.baseline_risk} label="Baseline Risk" />
                                        <DeltaIndicator delta={result.risk_delta} />
                                        <RiskBadge risk={result.modified_risk} label="Modified Risk" />
                                    </div>

                                    {/* Summary */}
                                    <div className="glass-card" style={{
                                        marginBottom: 'var(--sp-5)',
                                        borderLeft: `3px solid ${result.risk_delta > 0 ? 'var(--safe)' : 'var(--caution)'}`,
                                    }}>
                                        <p style={{ fontSize: '0.95rem', lineHeight: 1.6 }}>
                                            {result.improvement_summary}
                                        </p>
                                    </div>

                                    {/* Trajectory Charts */}
                                    <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                                        Projected 7-Day Trajectories
                                    </h2>
                                    <p className="data-label" style={{ marginBottom: 'var(--sp-4)' }}>
                                        Dashed = baseline (current lifestyle) • Solid = modified (your targets)
                                    </p>

                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                                        gap: 'var(--sp-4)',
                                    }}>
                                        {charts.map(({ title, baseKey, modKey, color }) => (
                                            <div key={title} className="glass-card" style={{ padding: 'var(--sp-3)' }}>
                                                <div className="data-label" style={{ marginBottom: 'var(--sp-2)' }}>
                                                    {title}
                                                </div>
                                                <ResponsiveContainer width="100%" height={200}>
                                                    <AreaChart data={chartData}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                                        <XAxis
                                                            dataKey="day"
                                                            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                                                            axisLine={{ stroke: 'var(--border)' }}
                                                        />
                                                        <YAxis
                                                            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
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
                                                        />
                                                        {/* Baseline: dashed ghost */}
                                                        <Area
                                                            type="monotone"
                                                            dataKey={baseKey}
                                                            stroke={color}
                                                            strokeDasharray="6 3"
                                                            strokeOpacity={0.5}
                                                            fill={color}
                                                            fillOpacity={0.05}
                                                            name="Baseline"
                                                        />
                                                        {/* Modified: solid */}
                                                        <Area
                                                            type="monotone"
                                                            dataKey={modKey}
                                                            stroke={color}
                                                            strokeWidth={2}
                                                            fill={color}
                                                            fillOpacity={0.15}
                                                            name="Modified"
                                                        />
                                                    </AreaChart>
                                                </ResponsiveContainer>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Loading patient data */}
            {!selectedId && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <SlidersHorizontal size={48} color="var(--text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.3 }} />
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: 'var(--sp-2)' }}>Loading your profile...</p>
                </div>
            )}
        </motion.div>
    );
}
