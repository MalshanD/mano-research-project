/* ============================================================
   MANO AMISE — Next-Best-Action
   
   Closed-loop AI recommendation:
   PPO Agent recommends → Seq2Seq simulates ALL options →
   LSTM evaluates → interventions ranked with evidence.
   ============================================================ */
import { useState, useCallback, useEffect } from 'react';
import { getPatient, getNextBestAction } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Zap, Loader, CheckCircle2, AlertTriangle,
    Award, ArrowRight, ShieldCheck, ShieldAlert
} from 'lucide-react';

/* ── Build patient state (shared helper) ────────── */
function buildPatientState(patient) {
    if (!patient) return null;

    const dynamic_history = [];
    for (let i = 0; i < 7; i++) {
        dynamic_history.push({
            sleep_hours: patient.sleep_duration ?? 6.5 + (Math.random() - 0.5),
            sleep_quality: patient.sleep_quality ?? 0.6 + (Math.random() - 0.5) * 0.2,
            heart_rate: patient.heart_rate ?? 75 + (Math.random() - 0.5) * 10,
            stress_level: patient.stress_level ?? 0.5 + (Math.random() - 0.5) * 0.2,
        });
    }

    const static_features = Array(20).fill(0).map((_, i) => {
        if (i === 0) return (patient.age ?? 30) / 100;
        if (i === 1) return patient.gender === 'Female' ? 1.0 : 0.0;
        return Math.random() * 0.5;
    });

    return {
        static_data: { features: static_features },
        dynamic_history,
    };
}

/* ── Risk badge ──────────────────────────────────── */
function RiskBadge({ risk, size = 'normal' }) {
    if (!risk) return null;
    const colorMap = { Low: 'var(--safe)', Medium: 'var(--caution)', High: 'var(--risk)' };
    const color = colorMap[risk.current_risk_class] || 'var(--text-muted)';
    const fontSize = size === 'small' ? '0.85rem' : '1.2rem';

    return (
        <span style={{
            fontSize,
            fontWeight: 700,
            color,
            fontFamily: 'var(--font-data)',
        }}>
            {risk.current_risk_class}
        </span>
    );
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function NextBestAction() {
    const { patientId } = usePatient();
    const [selectedId, setSelectedId] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /* ── Load patient + get recommendation ─────── */
    const handleSelectPatient = useCallback(async (id) => {
        setSelectedId(id);
        setResult(null);
        setError(null);
        setLoading(true);

        const { data: ptData, error: ptErr } = await getPatient(id);
        if (ptErr) { setError(ptErr); setLoading(false); return; }

        const state = buildPatientState(ptData);
        const { data, error: nbaErr } = await getNextBestAction(state);
        setLoading(false);

        if (nbaErr) { setError(nbaErr); return; }
        setResult(data);
    }, []);

    /* ── Auto-load logged-in user's patient ───── */
    useEffect(() => {
        if (patientId) handleSelectPatient(patientId);
    }, [patientId]); // eslint-disable-line react-hooks/exhaustive-deps

    /* ── Chart data ────────────────────────────── */
    const chartData = result?.candidates?.map(c => ({
        name: c.intervention_name,
        reduction: parseFloat((c.risk_reduction * 100).toFixed(1)),
        isRecommended: c.intervention_name === result.recommended_intervention,
    })) || [];

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
                        <Zap size={28} />
                        Next Best Action
                    </h1>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                        Closed-loop AI: PPO recommends → Seq2Seq simulates → LSTM evaluates → ranked evidence
                    </p>
                </div>
            </header>



            {/* Loading */}
            {loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-6)' }}>
                    <Loader size={32} className="spin" color="var(--predict)" />
                    <p style={{ marginTop: 'var(--sp-2)', color: 'var(--text-secondary)' }}>
                        PPO reasoning → simulating 5 interventions → evaluating outcomes...
                    </p>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card" style={{
                    borderColor: 'var(--risk)', color: 'var(--risk)', marginBottom: 'var(--sp-5)',
                }}>
                    <AlertTriangle size={16} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof error === 'string' ? error : 'Recommendation failed.'}
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
                        {/* PPO Recommendation Hero Card */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-5)',
                            borderLeft: '3px solid var(--predict)',
                            position: 'relative',
                            overflow: 'hidden',
                        }}>
                            <div style={{
                                position: 'absolute',
                                top: 12,
                                right: 12,
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--sp-1)',
                                padding: '4px 10px',
                                background: result.is_ppo_top_ranked
                                    ? 'rgba(45, 212, 191, 0.15)'
                                    : 'rgba(251, 191, 36, 0.15)',
                                borderRadius: 20,
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                color: result.is_ppo_top_ranked ? 'var(--safe)' : 'var(--caution)',
                            }}>
                                {result.is_ppo_top_ranked ? (
                                    <><CheckCircle2 size={12} /> PPO + Sim Agree</>
                                ) : (
                                    <><AlertTriangle size={12} /> Mixed Signals</>
                                )}
                            </div>

                            <div className="data-label" style={{ marginBottom: 'var(--sp-1)' }}>
                                PPO Agent Recommends
                            </div>
                            <div style={{
                                fontSize: '1.8rem',
                                fontWeight: 700,
                                color: 'var(--text-primary)',
                                marginBottom: 'var(--sp-1)',
                            }}>
                                {result.recommended_intervention}
                            </div>
                            <div style={{
                                fontSize: '0.9rem',
                                color: 'var(--text-secondary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--sp-3)',
                            }}>
                                <span>
                                    Intensity: <strong style={{ color: 'var(--predict)', fontFamily: 'var(--font-data)' }}>
                                        {(result.recommended_intensity * 100).toFixed(0)}%
                                    </strong>
                                </span>
                                <span style={{ color: 'var(--border)' }}>|</span>
                                <span>
                                    Baseline: <RiskBadge risk={result.baseline_risk} size="small" />
                                </span>
                            </div>
                        </div>

                        {/* Reasoning */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-5)',
                            borderLeft: `3px solid ${result.is_ppo_top_ranked ? 'var(--safe)' : 'var(--caution)'}`,
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.7, marginBottom: 'var(--sp-2)' }}>
                                {result.reasoning}
                            </p>
                            <p className="data-label" style={{ fontSize: '0.8rem', fontStyle: 'italic' }}>
                                {result.confidence_note}
                            </p>
                        </div>

                        {/* Intervention Comparison Chart */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            All Interventions — Risk Reduction Comparison
                        </h2>

                        <div className="glass-card" style={{ marginBottom: 'var(--sp-5)', padding: 'var(--sp-3)' }}>
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis
                                        dataKey="name"
                                        tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                    />
                                    <YAxis
                                        tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                                        axisLine={{ stroke: 'var(--border)' }}
                                        label={{
                                            value: 'Risk Reduction %',
                                            angle: -90,
                                            position: 'insideLeft',
                                            fill: 'var(--text-muted)',
                                            fontSize: 10,
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: 'var(--card)',
                                            border: '1px solid var(--border)',
                                            borderRadius: 8,
                                            color: 'var(--text-primary)',
                                            fontSize: '0.8rem',
                                        }}
                                        formatter={(val) => [`${val}%`, 'Risk Reduction']}
                                    />
                                    <Bar dataKey="reduction" radius={[4, 4, 0, 0]}>
                                        {chartData.map((entry, i) => (
                                            <Cell
                                                key={i}
                                                fill={entry.isRecommended ? 'var(--predict)' : 'var(--text-muted)'}
                                                fillOpacity={entry.isRecommended ? 0.85 : 0.4}
                                            />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Ranked Candidate Cards */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Detailed Ranking
                        </h2>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                            gap: 'var(--sp-3)',
                        }}>
                            {result.candidates.map((c, i) => {
                                const isPPO = c.intervention_name === result.recommended_intervention;
                                const isTop = c.rank === 1;
                                const borderColor = isPPO ? 'var(--predict)' : isTop ? 'var(--safe)' : 'var(--border)';

                                return (
                                    <motion.div
                                        key={c.intervention_id}
                                        className="glass-card"
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.08 }}
                                        style={{
                                            borderColor,
                                            borderWidth: isPPO || isTop ? 1 : undefined,
                                            position: 'relative',
                                        }}
                                    >
                                        {/* Badges */}
                                        <div style={{ display: 'flex', gap: 'var(--sp-1)', marginBottom: 'var(--sp-2)', flexWrap: 'wrap' }}>
                                            <span style={{
                                                fontSize: '0.65rem',
                                                fontWeight: 600,
                                                padding: '2px 8px',
                                                borderRadius: 10,
                                                background: 'rgba(255,255,255,0.06)',
                                                color: 'var(--text-muted)',
                                            }}>
                                                #{c.rank}
                                            </span>
                                            {isPPO && (
                                                <span style={{
                                                    fontSize: '0.65rem',
                                                    fontWeight: 600,
                                                    padding: '2px 8px',
                                                    borderRadius: 10,
                                                    background: 'rgba(99, 102, 241, 0.15)',
                                                    color: 'var(--predict)',
                                                }}>
                                                    <Zap size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                                                    PPO Pick
                                                </span>
                                            )}
                                            {isTop && (
                                                <span style={{
                                                    fontSize: '0.65rem',
                                                    fontWeight: 600,
                                                    padding: '2px 8px',
                                                    borderRadius: 10,
                                                    background: 'rgba(45, 212, 191, 0.15)',
                                                    color: 'var(--safe)',
                                                }}>
                                                    <Award size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                                                    Best Outcome
                                                </span>
                                            )}
                                        </div>

                                        <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-2)' }}>
                                            {c.intervention_name}
                                        </div>

                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                        }}>
                                            <div>
                                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Projected Risk</div>
                                                <RiskBadge risk={c.projected_risk} size="small" />
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Risk Reduction</div>
                                                <span style={{
                                                    fontFamily: 'var(--font-data)',
                                                    fontSize: '1rem',
                                                    fontWeight: 700,
                                                    color: c.risk_reduction > 0 ? 'var(--safe)' : c.risk_reduction < 0 ? 'var(--risk)' : 'var(--text-muted)',
                                                }}>
                                                    {c.risk_reduction > 0 ? '+' : ''}{(c.risk_reduction * 100).toFixed(1)}%
                                                </span>
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
            {!selectedId && !loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <Zap size={48} color="var(--text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.3 }} />
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>Loading your AI recommendation...</p>
                </div>
            )}
        </motion.div>
    );
}
