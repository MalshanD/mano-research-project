import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, Play, RotateCcw, TrendingDown, TrendingUp, Minus, AlertCircle } from 'lucide-react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart,
    ReferenceLine, Legend
} from 'recharts';
import { simulateIntervention, predictRisk } from '../../../api/client';

const INTERVENTIONS = [
    { id: 0, label: 'Control (No Intervention)' },
    { id: 1, label: 'Wellness App' },
    { id: 2, label: 'CBT (Cognitive Behavioral Therapy)' },
    { id: 3, label: 'Exercise Program' },
    { id: 4, label: 'Medication' },
];

const VITALS_CHANNELS = [
    { key: 'sleep_hours', label: 'Sleep', color: '#8b5cf6', unit: 'hrs' },
    { key: 'sleep_quality', label: 'Quality', color: '#06b6d4', unit: '' },
    { key: 'heart_rate', label: 'HR', color: '#ef4444', unit: 'bpm' },
    { key: 'stress_level', label: 'Stress', color: '#f59e0b', unit: '' },
];

/* Default 7 days of vitals for quick testing */
const DEFAULT_VITALS = [
    { sleep_hours: 7.0, sleep_quality: 0.8, heart_rate: 72, stress_level: 0.3 },
    { sleep_hours: 6.5, sleep_quality: 0.7, heart_rate: 75, stress_level: 0.4 },
    { sleep_hours: 5.0, sleep_quality: 0.5, heart_rate: 80, stress_level: 0.6 },
    { sleep_hours: 4.5, sleep_quality: 0.4, heart_rate: 85, stress_level: 0.7 },
    { sleep_hours: 4.0, sleep_quality: 0.3, heart_rate: 88, stress_level: 0.8 },
    { sleep_hours: 3.5, sleep_quality: 0.2, heart_rate: 90, stress_level: 0.9 },
    { sleep_hours: 3.0, sleep_quality: 0.1, heart_rate: 95, stress_level: 0.95 },
];

const DEFAULT_STATIC = Array(20).fill(0.5);

function RiskGauge({ label, risk, confidence, probabilities }) {
    if (!risk) return null;
    const riskColors = { Low: 'var(--success)', Medium: 'var(--caution)', High: 'var(--risk)' };
    const color = riskColors[risk] || 'var(--text-muted)';
    const highRiskProb = probabilities ? probabilities[2] : 0;

    return (
        <div className="flex flex-col items-center" style={{ textAlign: 'center' }}>
            <span className="data-label mb-sm">{label}</span>
            {/* Circular gauge */}
            <div style={{ position: 'relative', width: 120, height: 120 }}>
                <svg viewBox="0 0 120 120" width="120" height="120">
                    {/* Background arc */}
                    <circle cx="60" cy="60" r="50" fill="none" stroke="var(--elevated)" strokeWidth="8"
                        strokeDasharray="251.3" strokeDashoffset="62.8" strokeLinecap="round"
                        transform="rotate(135 60 60)" />
                    {/* Value arc */}
                    <motion.circle
                        cx="60" cy="60" r="50" fill="none" stroke={color} strokeWidth="8"
                        strokeDasharray="251.3"
                        strokeLinecap="round"
                        transform="rotate(135 60 60)"
                        initial={{ strokeDashoffset: 251.3 }}
                        animate={{ strokeDashoffset: 251.3 - (188.5 * highRiskProb) }}
                        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
                    />
                </svg>
                <div style={{
                    position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center'
                }}>
                    <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-2xl)', fontWeight: 700, color }}>
                        {risk}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {confidence ? `${(confidence * 100).toFixed(0)}%` : ''}
                    </span>
                </div>
            </div>
        </div>
    );
}

function TrajectoryChart({ baseline, simulated, channel }) {
    const data = baseline.map((day, i) => ({
        day: `Day ${i + 1}`,
        baseline: day[channel.key],
        simulated: simulated?.[i]?.[channel.key] ?? null,
    }));

    return (
        <div className="glass-card" style={{ padding: 'var(--space-md)' }}>
            <div className="flex items-center justify-between mb-sm">
                <span className="data-label">{channel.label}</span>
                <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {channel.unit}
                </span>
            </div>
            <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
                    <defs>
                        <linearGradient id={`grad-${channel.key}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={channel.color} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={channel.color} stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id={`grad-sim-${channel.key}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
                            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false} width={35} />
                    <Tooltip
                        contentStyle={{
                            background: 'var(--elevated)', border: '1px solid var(--glass-border)',
                            borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)',
                            fontFamily: 'var(--font-data)', color: 'var(--text-primary)'
                        }}
                    />
                    {/* Baseline — ghost trajectory */}
                    <Area type="monotone" dataKey="baseline" stroke={channel.color} strokeWidth={2}
                        fill={`url(#grad-${channel.key})`} strokeDasharray="6 3" dot={false} name="Baseline" />
                    {/* Simulated — solid trajectory */}
                    {simulated && (
                        <Area type="monotone" dataKey="simulated" stroke="#10b981" strokeWidth={2.5}
                            fill={`url(#grad-sim-${channel.key})`} dot={false} name="Projected"
                            animationDuration={800} animationEasing="ease-out" />
                    )}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

export default function SimulationLab() {
    const [intervention, setIntervention] = useState(2);
    const [intensity, setIntensity] = useState(0.7);
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const vitals = DEFAULT_VITALS;
    const staticFeatures = DEFAULT_STATIC;

    const handleSimulate = async () => {
        setRunning(true);
        setError(null);
        setResult(null);

        const payload = {
            patient_state: {
                static_data: { features: staticFeatures },
                dynamic_history: vitals,
            },
            intervention_type: intervention,
            intensity: intensity,
        };

        const res = await simulateIntervention(payload);
        setRunning(false);

        if (res.error) {
            setError(res.error);
        } else {
            setResult(res.data);
        }
    };

    const handleReset = () => {
        setResult(null);
        setError(null);
        setIntervention(2);
        setIntensity(0.7);
    };

    const reduction = result?.risk_reduction_score ?? null;
    const TrendIcon = reduction > 0 ? TrendingDown : reduction < 0 ? TrendingUp : Minus;
    const trendClass = reduction > 0 ? 'text-success' : reduction < 0 ? 'text-risk' : 'text-muted';

    return (
        <div className="fade-in">
            <div className="page-header">
                <h1 className="page-title">Simulation Lab</h1>
                <p className="page-subtitle">Direct manipulation simulation — apply interventions and observe causal trajectories</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 'var(--space-lg)' }}>
                {/* ─── Control Panel ─── */}
                <div className="flex flex-col gap-lg">
                    {/* Intervention Selector */}
                    <div className="glass-card">
                        <div className="data-label mb-md">Intervention Type</div>
                        <div className="flex flex-col gap-xs">
                            {INTERVENTIONS.map(({ id, label }) => (
                                <button
                                    key={id}
                                    onClick={() => setIntervention(id)}
                                    className={`btn ${intervention === id ? 'btn-primary' : 'btn-ghost'}`}
                                    style={{
                                        justifyContent: 'flex-start', width: '100%',
                                        fontSize: 'var(--text-xs)', padding: 'var(--space-sm) var(--space-md)',
                                    }}
                                >
                                    <span style={{
                                        width: 8, height: 8, borderRadius: '50%',
                                        background: intervention === id ? 'var(--text-inverse)' : 'var(--text-muted)',
                                        flexShrink: 0,
                                    }} />
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Intensity Slider — Direct Manipulation */}
                    <div className="glass-card">
                        <div className="flex items-center justify-between mb-md">
                            <span className="data-label">Intensity</span>
                            <span className="data-value" style={{ fontSize: 'var(--text-lg)' }}>
                                {(intensity * 100).toFixed(0)}%
                            </span>
                        </div>
                        <input
                            type="range" min="0" max="1" step="0.05"
                            value={intensity}
                            onChange={e => setIntensity(parseFloat(e.target.value))}
                            className="intensity-slider w-full"
                        />
                        <div className="flex justify-between mt-sm" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                            <span>Minimal</span>
                            <span>Maximum</span>
                        </div>
                    </div>

                    {/* Run Button */}
                    <button
                        className="btn btn-primary w-full"
                        onClick={handleSimulate}
                        disabled={running}
                        style={{ justifyContent: 'center', padding: 'var(--space-md)', fontSize: 'var(--text-base)' }}
                    >
                        {running ? (
                            <>
                                <div className="pulse-dot" style={{ width: 12, height: 12 }} />
                                Simulating...
                            </>
                        ) : (
                            <>
                                <Play size={18} />
                                Run Simulation
                            </>
                        )}
                    </button>

                    {result && (
                        <button className="btn btn-ghost w-full" onClick={handleReset} style={{ justifyContent: 'center' }}>
                            <RotateCcw size={16} />
                            Reset
                        </button>
                    )}
                </div>

                {/* ─── Temporal Canvas ─── */}
                <div className="flex flex-col gap-lg">
                    {error && (
                        <motion.div
                            className="glass-card"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            style={{ borderColor: 'var(--risk-dim)', background: 'var(--risk-dim)' }}
                        >
                            <div className="flex items-center gap-sm text-risk">
                                <AlertCircle size={16} />
                                <span>{typeof error === 'string' ? error : 'Simulation failed'}</span>
                            </div>
                        </motion.div>
                    )}

                    {/* Risk Gauges — Before / After */}
                    {(result || running) && (
                        <motion.div
                            className="glass-card no-hover"
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                        >
                            <div className="data-label mb-md">Risk State Comparison</div>
                            {running ? (
                                <div className="flex justify-between gap-lg">
                                    <div className="shimmer" style={{ width: 140, height: 160 }} />
                                    <div className="shimmer" style={{ width: 80, height: 40, alignSelf: 'center' }} />
                                    <div className="shimmer" style={{ width: 140, height: 160 }} />
                                </div>
                            ) : result && (
                                <div className="flex items-center justify-between" style={{ justifyContent: 'space-evenly' }}>
                                    <RiskGauge
                                        label="Before (Baseline)"
                                        risk={result.original_risk?.current_risk_class}
                                        confidence={result.original_risk?.confidence}
                                        probabilities={result.original_risk?.probabilities}
                                    />

                                    {/* Causal Force Arrow */}
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.5 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: 0.4, duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
                                        className="flex flex-col items-center gap-xs"
                                    >
                                        <TrendIcon size={28} className={trendClass} />
                                        <span className={`velocity-indicator ${reduction > 0 ? 'decreasing' : reduction < 0 ? 'increasing' : 'stable'}`}
                                            style={{ fontSize: 'var(--text-lg)' }}
                                        >
                                            {reduction !== null ? `${(Math.abs(reduction) * 100).toFixed(1)}%` : '—'}
                                        </span>
                                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                            {reduction > 0 ? 'Risk Reduced' : reduction < 0 ? 'Risk Increased' : 'No Change'}
                                        </span>
                                    </motion.div>

                                    <RiskGauge
                                        label="After (Projected)"
                                        risk={result.projected_risk?.current_risk_class}
                                        confidence={result.projected_risk?.confidence}
                                        probabilities={result.projected_risk?.probabilities}
                                    />
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* Trajectory Charts — Temporal Layer */}
                    {(result || running) && (
                        <motion.div
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
                        >
                            <div className="flex items-center gap-sm mb-md">
                                <FlaskConical size={16} className="text-predict" />
                                <span className="data-label">Trajectory Canvas — Baseline (dashed) vs Projected (solid)</span>
                            </div>
                            {running ? (
                                <div className="grid-2">
                                    {[...Array(4)].map((_, i) => (
                                        <div key={i} className="shimmer" style={{ height: 180, borderRadius: 'var(--radius-lg)' }} />
                                    ))}
                                </div>
                            ) : result && (
                                <div className="grid-2">
                                    {VITALS_CHANNELS.map(channel => (
                                        <TrajectoryChart
                                            key={channel.key}
                                            baseline={vitals}
                                            simulated={result.future_vitals}
                                            channel={channel}
                                        />
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* Empty State */}
                    {!result && !running && !error && (
                        <div className="glass-card no-hover" style={{
                            textAlign: 'center', padding: 'var(--space-3xl)',
                            display: 'flex', flexDirection: 'column', alignItems: 'center',
                            justifyContent: 'center', minHeight: 400
                        }}>
                            <FlaskConical size={48} style={{ color: 'var(--text-muted)', opacity: 0.2, marginBottom: 'var(--space-lg)' }} />
                            <p style={{ color: 'var(--text-muted)', maxWidth: 360 }}>
                                Select an intervention and intensity, then run the simulation to observe predicted trajectories.
                            </p>
                            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-sm)', opacity: 0.6 }}>
                                The temporal canvas will visualize cause → transition → effect
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
