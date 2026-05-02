import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, Play, TrendingDown, TrendingUp, Minus, Award, Zap } from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
    RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend
} from 'recharts';
import { simulateBatch } from '../../../api/client';

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

const INTERVENTION_COLORS = {
    'Control': '#475569',
    'Wellness App': '#8b5cf6',
    'CBT': '#06b6d4',
    'Exercise': '#10b981',
    'Medication': '#f59e0b',
};

export default function InterventionCompare() {
    const [intensity, setIntensity] = useState(0.7);
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleRun = async () => {
        setRunning(true);
        setError(null);
        setResult(null);

        const payload = {
            patient_state: {
                static_data: { features: DEFAULT_STATIC },
                dynamic_history: DEFAULT_VITALS,
            },
            intensity,
        };

        const res = await simulateBatch(payload);
        setRunning(false);

        if (res.error) {
            setError(typeof res.error === 'string' ? res.error : 'Batch simulation failed');
        } else {
            setResult(res.data);
        }
    };

    const barData = result?.comparisons?.map(c => ({
        name: c.intervention_name,
        reduction: +(c.risk_reduction_score * 100).toFixed(1),
        color: INTERVENTION_COLORS[c.intervention_name] || 'var(--text-muted)',
    })) || [];

    const radarData = result?.comparisons ? (() => {
        const metrics = ['sleep_hours', 'sleep_quality', 'heart_rate', 'stress_level'];
        const metricLabels = ['Sleep', 'Quality', 'HR Calm', 'Low Stress'];
        return metricLabels.map((label, mi) => {
            const row = { metric: label };
            result.comparisons.forEach(c => {
                const lastDay = c.future_vitals?.[6];
                if (lastDay) {
                    let val = lastDay[metrics[mi]];
                    // Normalize: for HR, invert (lower = better); for stress, invert
                    if (mi === 2) val = Math.max(0, 1 - (val - 40) / 160);  // HR: 40-200 → 1-0
                    if (mi === 3) val = 1 - val; // stress: lower = better
                    if (mi === 0) val = val / 10; // sleep: scale to 0-1 roughly
                    row[c.intervention_name] = +val.toFixed(2);
                }
            });
            return row;
        });
    })() : [];

    const riskBadge = { Low: 'badge-safe', Medium: 'badge-caution', High: 'badge-risk' };

    return (
        <div className="fade-in">
            <div className="page-header">
                <h1 className="page-title">Intervention Compare</h1>
                <p className="page-subtitle">Branching future visualization — all interventions tested simultaneously</p>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-lg mb-lg">
                <div className="glass-card flex items-center gap-lg" style={{ padding: 'var(--space-md) var(--space-lg)', flex: 1, maxWidth: 500 }}>
                    <div className="flex-1">
                        <div className="flex items-center justify-between mb-sm">
                            <span className="data-label">Intensity</span>
                            <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-sm)', color: 'var(--safe)' }}>
                                {(intensity * 100).toFixed(0)}%
                            </span>
                        </div>
                        <input type="range" min="0" max="1" step="0.05" value={intensity}
                            onChange={e => setIntensity(parseFloat(e.target.value))}
                            className="intensity-slider w-full" />
                    </div>
                </div>
                <button className="btn btn-primary" onClick={handleRun} disabled={running}
                    style={{ padding: 'var(--space-md) var(--space-xl)' }}>
                    {running ? (
                        <><div className="pulse-dot" style={{ width: 10, height: 10 }} /> Comparing...</>
                    ) : (
                        <><Play size={16} /> Compare All</>
                    )}
                </button>
            </div>

            {error && (
                <div className="glass-card mb-lg" style={{ borderColor: 'var(--risk-dim)', background: 'var(--risk-dim)' }}>
                    <span className="text-risk">{error}</span>
                </div>
            )}

            {/* Results */}
            {running && (
                <div className="grid-2">
                    <div className="shimmer" style={{ height: 350, borderRadius: 'var(--radius-lg)' }} />
                    <div className="shimmer" style={{ height: 350, borderRadius: 'var(--radius-lg)' }} />
                    <div className="shimmer" style={{ height: 200, borderRadius: 'var(--radius-lg)', gridColumn: 'span 2' }} />
                </div>
            )}

            {result && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
                    {/* Best Intervention Banner */}
                    <motion.div
                        className="glass-card mb-lg"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.1, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                        style={{
                            background: 'linear-gradient(135deg, var(--safe-dim), var(--predict-dim))',
                            borderColor: 'var(--safe)', display: 'flex', alignItems: 'center', gap: 'var(--space-lg)'
                        }}
                    >
                        <div style={{
                            width: 48, height: 48, borderRadius: 'var(--radius-full)',
                            background: 'var(--safe)', display: 'flex', alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Award size={24} color="var(--text-inverse)" />
                        </div>
                        <div>
                            <div className="data-label">Recommended Intervention</div>
                            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--safe)' }}>
                                {result.best_intervention}
                            </div>
                            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                                Risk reduction: {(Math.abs(result.best_risk_reduction) * 100).toFixed(1)}%
                            </div>
                        </div>
                    </motion.div>

                    <div className="grid-2 mb-lg">
                        {/* Bar Chart — Risk Reduction Ranking */}
                        <motion.div className="glass-card no-hover"
                            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2, duration: 0.5 }}
                        >
                            <div className="data-label mb-md">Risk Reduction by Intervention</div>
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart data={barData} layout="vertical" margin={{ left: 80, right: 20, top: 5, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                                    <XAxis type="number" tick={{ fontSize: 10, fill: '#475569' }} axisLine={false} tickLine={false}
                                        tickFormatter={v => `${v}%`} />
                                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }}
                                        axisLine={false} tickLine={false} width={80} />
                                    <Tooltip
                                        formatter={(v) => [`${v}%`, 'Reduction']}
                                        contentStyle={{
                                            background: 'var(--elevated)', border: '1px solid var(--glass-border)',
                                            borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)',
                                            fontFamily: 'var(--font-data)', color: 'var(--text-primary)'
                                        }}
                                    />
                                    <Bar dataKey="reduction" radius={[0, 6, 6, 0]} animationDuration={800}>
                                        {barData.map((entry, i) => (
                                            <Cell key={i} fill={entry.color} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </motion.div>

                        {/* Radar Chart — Multi-dimensional outcome comparison */}
                        <motion.div className="glass-card no-hover"
                            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3, duration: 0.5 }}
                        >
                            <div className="data-label mb-md">Outcome Profile — End of Simulation</div>
                            <ResponsiveContainer width="100%" height={280}>
                                <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                                    <PolarGrid stroke="rgba(255,255,255,0.06)" />
                                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                                    <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 1]} />
                                    {result.comparisons?.map(c => (
                                        <Radar key={c.intervention_name} name={c.intervention_name}
                                            dataKey={c.intervention_name}
                                            stroke={INTERVENTION_COLORS[c.intervention_name] || '#475569'}
                                            fill={INTERVENTION_COLORS[c.intervention_name] || '#475569'}
                                            fillOpacity={0.1} strokeWidth={2}
                                        />
                                    ))}
                                    <Legend wrapperStyle={{ fontSize: 10, color: '#94a3b8' }} />
                                </RadarChart>
                            </ResponsiveContainer>
                        </motion.div>
                    </div>

                    {/* Detailed Cards */}
                    <div className="data-label mb-md">All Interventions — Ranked</div>
                    <div className="grid-auto">
                        {result.comparisons?.map((comp, i) => {
                            const reduction = comp.risk_reduction_score;
                            const TrendIcon = reduction > 0 ? TrendingDown : reduction < 0 ? TrendingUp : Minus;
                            const isBest = comp.intervention_name === result.best_intervention;
                            return (
                                <motion.div
                                    key={comp.intervention_id}
                                    className="glass-card"
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.3 + i * 0.08, duration: 0.4 }}
                                    style={isBest ? { borderColor: 'var(--safe)', boxShadow: '0 0 20px var(--safe-dim)' } : {}}
                                >
                                    <div className="flex items-center justify-between mb-md">
                                        <div className="flex items-center gap-sm">
                                            <div style={{
                                                width: 10, height: 10, borderRadius: '50%',
                                                background: INTERVENTION_COLORS[comp.intervention_name] || 'var(--text-muted)'
                                            }} />
                                            <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{comp.intervention_name}</span>
                                        </div>
                                        {isBest && (
                                            <span className="badge badge-safe"><Zap size={10} /> Best</span>
                                        )}
                                    </div>

                                    <div className="flex items-center justify-between mb-sm">
                                        <span className={`badge ${riskBadge[comp.original_risk?.current_risk_class] || 'badge-predict'}`}>
                                            {comp.original_risk?.current_risk_class || '—'}
                                        </span>
                                        <span style={{ color: 'var(--text-muted)' }}>→</span>
                                        <span className={`badge ${riskBadge[comp.projected_risk?.current_risk_class] || 'badge-predict'}`}>
                                            {comp.projected_risk?.current_risk_class || '—'}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-xs mt-md" style={{ fontSize: 'var(--text-xs)' }}>
                                        <TrendIcon size={14} className={reduction > 0 ? 'text-success' : reduction < 0 ? 'text-risk' : 'text-muted'} />
                                        <span className={reduction > 0 ? 'text-success' : reduction < 0 ? 'text-risk' : 'text-muted'}
                                            style={{ fontFamily: 'var(--font-data)', fontWeight: 600 }}>
                                            {(Math.abs(reduction) * 100).toFixed(1)}% {reduction > 0 ? 'reduction' : reduction < 0 ? 'increase' : ''}
                                        </span>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                </motion.div>
            )}

            {/* Empty state */}
            {!result && !running && !error && (
                <div className="glass-card no-hover" style={{ textAlign: 'center', padding: 'var(--space-3xl)' }}>
                    <BarChart3 size={48} style={{ color: 'var(--text-muted)', opacity: 0.2, marginBottom: 'var(--space-md)' }} />
                    <p className="text-muted">Run the comparison to evaluate all 5 interventions simultaneously.</p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', opacity: 0.6, marginTop: 'var(--space-sm)' }}>
                        Branching future visualization — see every possible trajectory at once
                    </p>
                </div>
            )}
        </div>
    );
}
