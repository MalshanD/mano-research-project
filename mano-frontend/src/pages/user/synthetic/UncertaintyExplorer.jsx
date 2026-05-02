/* ============================================================
   MANO AMISE — Uncertainty Explorer (MC Dropout)
   
   Runs the LSTM N times with dropout enabled to get a distribution
   of predictions. Shows reliability, entropy, and per-class stats.
   ============================================================ */
import { useState, useCallback, useEffect } from 'react';
import { getPatient, evaluateUncertainty } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell, ErrorBar
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Gauge, Loader, AlertTriangle, ShieldCheck, ShieldAlert,
    CheckCircle2
} from 'lucide-react';

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

const CLASS_COLORS = { Low: 'var(--safe)', Medium: 'var(--caution)', High: 'var(--risk)' };

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function UncertaintyExplorer() {
    const { patientId } = usePatient();
    const [selectedId, setSelectedId] = useState(null);
    const [nSamples, setNSamples] = useState(30);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /* ── Patient select + auto-run ────────────── */
    const handleSelectPatient = useCallback(async (id) => {
        setSelectedId(id);
        setResult(null);
        setError(null);
        setLoading(true);

        const { data: ptData, error: ptErr } = await getPatient(id);
        if (ptErr) { setError(ptErr); setLoading(false); return; }

        const state = buildPatientState(ptData);
        const { data, error: uncErr } = await evaluateUncertainty({
            patient_state: state,
            n_samples: nSamples,
        });
        setLoading(false);

        if (uncErr) { setError(uncErr); return; }
        setResult(data);
    }, [nSamples]);

    /* ── Auto-load logged-in user's patient ───── */
    useEffect(() => {
        if (patientId) handleSelectPatient(patientId);
    }, [patientId, nSamples]); // eslint-disable-line react-hooks/exhaustive-deps

    /* ── Chart data ────────────────────────────── */
    const chartData = result?.class_distributions?.map(d => ({
        name: d.risk_class,
        mean: parseFloat((d.mean_probability * 100).toFixed(1)),
        std: parseFloat((d.std_probability * 100).toFixed(1)),
        min: parseFloat((d.min_probability * 100).toFixed(1)),
        max: parseFloat((d.max_probability * 100).toFixed(1)),
    })) || [];

    /* ── Stability ring SVG ──────────────────── */
    const StabilityRing = ({ stability }) => {
        const radius = 40;
        const circumference = 2 * Math.PI * radius;
        const progress = circumference * (1 - stability);
        const color = stability > 0.8 ? 'var(--safe)' : stability > 0.5 ? 'var(--caution)' : 'var(--risk)';

        return (
            <svg width={100} height={100} viewBox="0 0 100 100">
                <circle cx={50} cy={50} r={radius}
                    fill="none" stroke="var(--surface)" strokeWidth={6}
                />
                <circle cx={50} cy={50} r={radius}
                    fill="none" stroke={color} strokeWidth={6}
                    strokeDasharray={circumference}
                    strokeDashoffset={progress}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                    style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
                />
                <text x={50} y={46} textAnchor="middle" fill={color}
                    fontSize="18" fontWeight="700" fontFamily="var(--font-data)">
                    {(stability * 100).toFixed(0)}%
                </text>
                <text x={50} y={62} textAnchor="middle" fill="var(--text-muted)" fontSize="8">
                    Stability
                </text>
            </svg>
        );
    };

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
                        <Gauge size={28} />
                        Uncertainty Explorer
                    </h1>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                        MC Dropout — runs the LSTM N times with dropout enabled to reveal prediction confidence
                    </p>
                </div>
            </header>

            {/* Controls */}
            <div className="glass-card" style={{ marginBottom: 'var(--sp-5)' }}>
                <div>
                    <div className="data-label" style={{ marginBottom: 'var(--sp-2)' }}>MC Samples</div>
                    <select
                        value={nSamples}
                        onChange={(e) => setNSamples(parseInt(e.target.value))}
                        style={{
                            padding: 'var(--sp-2) var(--sp-3)',
                            background: 'var(--surface)', border: '1px solid var(--border)',
                            borderRadius: 8, color: 'var(--text-primary)',
                            fontSize: '0.95rem',
                        }}
                    >
                        {[10, 20, 30, 50, 100].map(n => (
                            <option key={n} value={n}>{n} samples</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Loading */}
            {loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-6)' }}>
                    <Loader size={32} className="spin" color="var(--predict)" />
                    <p style={{ marginTop: 'var(--sp-2)', color: 'var(--text-secondary)' }}>
                        Running {nSamples} MC forward passes...
                    </p>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card" style={{
                    borderColor: 'var(--risk)', color: 'var(--risk)', marginBottom: 'var(--sp-5)',
                }}>
                    <AlertTriangle size={16} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof error === 'string' ? error : 'Uncertainty evaluation failed.'}
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
                        {/* Top metrics row */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                            gap: 'var(--sp-4)',
                            marginBottom: 'var(--sp-5)',
                        }}>
                            {/* Stability Ring */}
                            <div className="glass-card" style={{
                                display: 'flex', flexDirection: 'column', alignItems: 'center',
                                padding: 'var(--sp-3)',
                            }}>
                                <StabilityRing stability={result.prediction_stability} />
                                <div style={{
                                    marginTop: 'var(--sp-1)',
                                    display: 'flex', alignItems: 'center', gap: 4,
                                    fontSize: '0.75rem', fontWeight: 600,
                                    color: result.is_reliable ? 'var(--safe)' : 'var(--caution)',
                                }}>
                                    {result.is_reliable ? (
                                        <><CheckCircle2 size={12} /> Reliable</>
                                    ) : (
                                        <><AlertTriangle size={12} /> Use Caution</>
                                    )}
                                </div>
                            </div>

                            {/* Point Estimate */}
                            <div className="glass-card" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Point Estimate</div>
                                <div style={{
                                    fontSize: '1.5rem', fontWeight: 700, margin: 'var(--sp-2) 0',
                                    color: CLASS_COLORS[result.point_estimate.current_risk_class],
                                    fontFamily: 'var(--font-data)',
                                }}>
                                    {result.point_estimate.current_risk_class}
                                </div>
                                <div className="data-label">
                                    {(result.point_estimate.confidence * 100).toFixed(0)}% confidence
                                </div>
                            </div>

                            {/* Entropy */}
                            <div className="glass-card" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Predictive Entropy</div>
                                <div style={{
                                    fontSize: '1.5rem', fontWeight: 700, margin: 'var(--sp-2) 0',
                                    fontFamily: 'var(--font-data)',
                                    color: result.predictive_entropy < 0.5 ? 'var(--safe)'
                                        : result.predictive_entropy < 1.0 ? 'var(--caution)' : 'var(--risk)',
                                }}>
                                    {result.predictive_entropy.toFixed(3)}
                                </div>
                                <div className="data-label">
                                    {result.predictive_entropy < 0.5 ? 'Low (confident)' :
                                        result.predictive_entropy < 1.0 ? 'Moderate' : 'High (uncertain)'}
                                </div>
                            </div>

                            {/* Mutual Information */}
                            <div className="glass-card" style={{ padding: 'var(--sp-3)', textAlign: 'center' }}>
                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Epistemic Uncertainty</div>
                                <div style={{
                                    fontSize: '1.5rem', fontWeight: 700, margin: 'var(--sp-2) 0',
                                    fontFamily: 'var(--font-data)',
                                    color: result.mutual_information < 0.1 ? 'var(--safe)'
                                        : result.mutual_information < 0.3 ? 'var(--caution)' : 'var(--risk)',
                                }}>
                                    {result.mutual_information.toFixed(4)}
                                </div>
                                <div className="data-label">
                                    MI (model uncertainty)
                                </div>
                            </div>
                        </div>

                        {/* Summary */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-5)',
                            borderLeft: `3px solid ${result.is_reliable ? 'var(--safe)' : 'var(--caution)'}`,
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.7 }}>
                                {result.uncertainty_summary}
                            </p>
                        </div>

                        {/* Class Distribution Chart */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Class Probability Distribution (Mean ± Std across {result.n_samples} samples)
                        </h2>

                        <div className="glass-card" style={{ marginBottom: 'var(--sp-5)', padding: 'var(--sp-3)' }}>
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis
                                        dataKey="name"
                                        tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                    />
                                    <YAxis
                                        tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                        domain={[0, 100]}
                                        label={{
                                            value: 'Probability %',
                                            angle: -90,
                                            position: 'insideLeft',
                                            fill: 'var(--text-muted)', fontSize: 10,
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: 'var(--card)',
                                            border: '1px solid var(--border)',
                                            borderRadius: 8,
                                            color: 'var(--text-primary)', fontSize: '0.8rem',
                                        }}
                                        formatter={(val, name) => [`${val}%`, name === 'mean' ? 'Mean Prob' : name]}
                                    />
                                    <Bar dataKey="mean" radius={[4, 4, 0, 0]}>
                                        {chartData.map((entry, i) => (
                                            <Cell
                                                key={i}
                                                fill={CLASS_COLORS[entry.name] || 'var(--text-muted)'}
                                                fillOpacity={0.7}
                                            />
                                        ))}
                                        <ErrorBar dataKey="std" width={8} strokeWidth={2} stroke="var(--text-secondary)" />
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Per-class details */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(3, 1fr)',
                            gap: 'var(--sp-3)',
                        }}>
                            {result.class_distributions.map(d => (
                                <div key={d.risk_class} className="glass-card" style={{
                                    padding: 'var(--sp-3)',
                                    borderTop: `2px solid ${CLASS_COLORS[d.risk_class]}`,
                                }}>
                                    <div style={{
                                        fontSize: '1rem', fontWeight: 600,
                                        color: CLASS_COLORS[d.risk_class],
                                        marginBottom: 'var(--sp-2)',
                                    }}>
                                        {d.risk_class} Risk
                                    </div>
                                    <div style={{
                                        display: 'grid', gridTemplateColumns: '1fr 1fr',
                                        gap: 'var(--sp-1)',
                                        fontSize: '0.8rem',
                                    }}>
                                        <div>
                                            <span className="data-label" style={{ fontSize: '0.65rem' }}>Mean</span>
                                            <div style={{ fontFamily: 'var(--font-data)' }}>
                                                {(d.mean_probability * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                        <div>
                                            <span className="data-label" style={{ fontSize: '0.65rem' }}>Std</span>
                                            <div style={{ fontFamily: 'var(--font-data)' }}>
                                                ±{(d.std_probability * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                        <div>
                                            <span className="data-label" style={{ fontSize: '0.65rem' }}>Min</span>
                                            <div style={{ fontFamily: 'var(--font-data)' }}>
                                                {(d.min_probability * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                        <div>
                                            <span className="data-label" style={{ fontSize: '0.65rem' }}>Max</span>
                                            <div style={{ fontFamily: 'var(--font-data)' }}>
                                                {(d.max_probability * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Loading profile */}
            {!selectedId && !loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <Gauge size={48} color="var(--text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.3 }} />
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>Loading uncertainty analysis...</p>
                </div>
            )}
        </motion.div>
    );
}
