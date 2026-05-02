import { useState } from 'react';
import { motion } from 'framer-motion';
import { Stethoscope, Play, Brain, Shield, MessageCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import { prescribeAI } from '../../../api/client';

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

const INTERVENTION_DETAILS = {
    'Control': {
        icon: Shield,
        description: 'No active intervention — monitor and observe natural progression.',
        color: 'var(--text-muted)',
    },
    'Wellness App': {
        icon: MessageCircle,
        description: 'Digital wellness platform with guided mindfulness, mood tracking, and psychoeducation modules.',
        color: 'var(--predict)',
    },
    'CBT': {
        icon: Brain,
        description: 'Cognitive Behavioral Therapy — structured sessions targeting maladaptive thought patterns and behavioral activation.',
        color: 'var(--safe)',
    },
    'Exercise': {
        icon: CheckCircle2,
        description: 'Structured physical activity program — aerobic and resistance training with progressive intensity.',
        color: 'var(--success)',
    },
    'Medication': {
        icon: Sparkles,
        description: 'Pharmacological intervention — SSRI/SNRI class medications with dosage optimization.',
        color: 'var(--caution)',
    },
};

export default function Prescription() {
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handlePrescribe = async () => {
        setRunning(true);
        setError(null);
        setResult(null);

        const payload = {
            static_data: { features: DEFAULT_STATIC },
            dynamic_history: DEFAULT_VITALS,
        };

        const res = await prescribeAI(payload);
        setRunning(false);

        if (res.error) {
            setError(typeof res.error === 'string' ? res.error : 'Prescription generation failed');
        } else {
            setResult(res.data);
        }
    };

    const recommended = result?.recommended_intervention;
    const details = INTERVENTION_DETAILS[recommended] || INTERVENTION_DETAILS['Control'];
    const RecommendedIcon = details?.icon || Shield;

    const riskBadge = { Low: 'badge-safe', Medium: 'badge-caution', High: 'badge-risk' };

    return (
        <div className="fade-in">
            <div className="page-header">
                <h1 className="page-title">AI Prescription</h1>
                <p className="page-subtitle">Intelligence Layer — agent reasoning and intervention recommendation</p>
            </div>

            {/* Run Button */}
            <div className="mb-lg">
                <button className="btn btn-primary" onClick={handlePrescribe} disabled={running}
                    style={{ padding: 'var(--space-md) var(--space-xl)' }}>
                    {running ? (
                        <><div className="pulse-dot" style={{ width: 10, height: 10 }} /> Analyzing...</>
                    ) : (
                        <><Stethoscope size={18} /> Generate AI Prescription</>
                    )}
                </button>
            </div>

            {error && (
                <div className="glass-card mb-lg" style={{ borderColor: 'var(--risk-dim)', background: 'var(--risk-dim)' }}>
                    <span className="text-risk">{error}</span>
                </div>
            )}

            {/* Shimmer Loading */}
            {running && (
                <div className="grid-2">
                    <div className="shimmer" style={{ height: 300, borderRadius: 'var(--radius-lg)' }} />
                    <div className="shimmer" style={{ height: 300, borderRadius: 'var(--radius-lg)' }} />
                </div>
            )}

            {/* Results */}
            {result && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
                    <div className="grid-2 mb-lg">
                        {/* Recommendation Card — Intelligence Layer */}
                        <motion.div
                            className="glass-card"
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                            style={{
                                background: `linear-gradient(135deg, rgba(6,182,212,0.05), rgba(139,92,246,0.05))`,
                                borderColor: 'rgba(6,182,212,0.2)',
                            }}
                        >
                            <div className="flex items-center gap-sm mb-lg">
                                <Brain size={18} className="text-predict" />
                                <span className="data-label">AI Agent Recommendation</span>
                            </div>

                            <div className="flex items-center gap-lg mb-lg">
                                <div style={{
                                    width: 64, height: 64, borderRadius: 'var(--radius-lg)',
                                    background: details.color ? `${details.color}22` : 'var(--elevated)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    border: `1px solid ${details.color || 'var(--glass-border)'}`,
                                }}>
                                    <RecommendedIcon size={28} style={{ color: details.color }} />
                                </div>
                                <div>
                                    <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: details.color }}>
                                        {recommended || 'Unknown'}
                                    </div>
                                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                        Recommended Intervention
                                    </div>
                                </div>
                            </div>

                            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                {details.description}
                            </p>

                            {result.confidence != null && (
                                <div className="mt-lg">
                                    <div className="flex items-center justify-between mb-sm">
                                        <span className="data-label">Agent Confidence</span>
                                        <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-sm)', color: 'var(--safe)' }}>
                                            {(result.confidence * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <div style={{
                                        height: 6, borderRadius: 'var(--radius-full)', background: 'var(--elevated)',
                                        overflow: 'hidden'
                                    }}>
                                        <motion.div
                                            style={{ height: '100%', borderRadius: 'var(--radius-full)', background: 'var(--safe)' }}
                                            initial={{ width: 0 }}
                                            animate={{ width: `${result.confidence * 100}%` }}
                                            transition={{ duration: 0.8, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
                                        />
                                    </div>
                                </div>
                            )}
                        </motion.div>

                        {/* Reasoning & Risk Context */}
                        <motion.div
                            className="glass-card"
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
                        >
                            <div className="flex items-center gap-sm mb-lg">
                                <Shield size={18} className="text-safe" />
                                <span className="data-label">Risk Context</span>
                            </div>

                            {/* Current Assessment */}
                            <div className="mb-lg">
                                <div className="data-label mb-sm">Current Risk Assessment</div>
                                <div className="flex items-center gap-md">
                                    <span className={`badge ${riskBadge[result.current_risk?.current_risk_class] || 'badge-predict'}`}
                                        style={{ fontSize: 'var(--text-sm)', padding: '4px 12px' }}>
                                        {result.current_risk?.current_risk_class || '—'}
                                    </span>
                                    {result.current_risk?.confidence != null && (
                                        <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                            Confidence: {(result.current_risk.confidence * 100).toFixed(0)}%
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Risk Probabilities */}
                            {result.current_risk?.probabilities && (
                                <div className="mb-lg">
                                    <div className="data-label mb-md">Risk Distribution</div>
                                    {['Low', 'Medium', 'High'].map((level, i) => (
                                        <div key={level} className="flex items-center gap-md mb-sm">
                                            <span style={{ width: 60, fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{level}</span>
                                            <div style={{ flex: 1, height: 6, borderRadius: 'var(--radius-full)', background: 'var(--elevated)', overflow: 'hidden' }}>
                                                <motion.div
                                                    style={{
                                                        height: '100%', borderRadius: 'var(--radius-full)',
                                                        background: i === 0 ? 'var(--success)' : i === 1 ? 'var(--caution)' : 'var(--risk)',
                                                    }}
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${result.current_risk.probabilities[i] * 100}%` }}
                                                    transition={{ duration: 0.6, delay: 0.3 + i * 0.1 }}
                                                />
                                            </div>
                                            <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)', width: 40, textAlign: 'right' }}>
                                                {(result.current_risk.probabilities[i] * 100).toFixed(1)}%
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Reasoning */}
                            {result.reasoning && (
                                <div>
                                    <div className="data-label mb-sm">Agent Reasoning</div>
                                    <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7, fontStyle: 'italic' }}>
                                        "{result.reasoning}"
                                    </p>
                                </div>
                            )}
                        </motion.div>
                    </div>
                </motion.div>
            )}

            {/* Empty State */}
            {!result && !running && !error && (
                <div className="glass-card no-hover" style={{ textAlign: 'center', padding: 'var(--space-3xl)' }}>
                    <Stethoscope size={48} style={{ color: 'var(--text-muted)', opacity: 0.2, marginBottom: 'var(--space-md)' }} />
                    <p className="text-muted">Generate an AI prescription to see the recommended intervention and reasoning.</p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', opacity: 0.6, marginTop: 'var(--space-sm)' }}>
                        The Intelligence Layer reveals agent intent and optimization decisions
                    </p>
                </div>
            )}
        </div>
    );
}
