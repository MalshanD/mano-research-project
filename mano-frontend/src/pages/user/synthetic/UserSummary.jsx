/* ============================================================
   MANO AMISE — User Health Summary
   Landing page for the Predictions section. Automatically loads
   the logged-in user's patient profile and shows:
   - Current risk level
   - 7-day lifestyle metrics
   - Quick-access links to all analysis tools
   ============================================================ */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPatient } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer
} from 'recharts';
import { motion } from 'framer-motion';
import {
    User, ShieldAlert, ShieldCheck, Shield, Heart, Moon, Brain,
    Activity, SlidersHorizontal, ScanSearch, Zap, ListOrdered,
    Gauge, FileText, GitFork, RefreshCw
} from 'lucide-react';

/* ── Risk helpers ────────────────────────────────── */
const riskConfig = {
    Low:    { color: 'var(--safe)',    icon: ShieldCheck,  bg: 'rgba(45,212,191,0.1)' },
    Medium: { color: 'var(--caution)', icon: Shield,       bg: 'rgba(251,191,36,0.1)' },
    High:   { color: 'var(--risk)',    icon: ShieldAlert,  bg: 'rgba(255,76,76,0.1)'  },
};

/* ── Compute averages from 7-day history ─────────── */
function computeAverages(vitals) {
    if (!vitals || vitals.length === 0) return { sleep_hours: 0, heart_rate: 0, stress_level: 0, sleep_quality: 0 };
    const n = vitals.length;
    return {
        sleep_hours:   Math.round(vitals.reduce((s, v) => s + v.sleep_hours, 0) / n * 10) / 10,
        heart_rate:    Math.round(vitals.reduce((s, v) => s + v.heart_rate, 0) / n),
        stress_level:  Math.round(vitals.reduce((s, v) => s + v.stress_level, 0) / n * 100),
        sleep_quality: Math.round(vitals.reduce((s, v) => s + v.sleep_quality, 0) / n * 100),
    };
}

/* ── Quick-action tool links ─────────────────────── */
const TOOLS = [
    { path: 'simulate',   label: 'Simulation Lab',       icon: Activity,           color: 'var(--predict)' },
    { path: 'compare',    label: 'Intervention Compare',  icon: GitFork,            color: 'var(--safe)' },
    { path: 'prescribe',  label: 'AI Prescription',       icon: RefreshCw,          color: 'var(--caution)' },
    { path: 'what-if',    label: 'What-If Simulator',     icon: SlidersHorizontal,  color: 'var(--predict)' },
    { path: 'explain',    label: 'XAI Explainer',         icon: ScanSearch,         color: 'var(--risk)' },
    { path: 'next-action',label: 'Next Best Action',      icon: Zap,                color: 'var(--caution)' },
    { path: 'sequencer',  label: 'Sequencer',             icon: ListOrdered,        color: 'var(--safe)' },
    { path: 'uncertainty',label: 'Uncertainty',           icon: Gauge,              color: 'var(--predict)' },
    { path: 'report',     label: 'Clinical Report',       icon: FileText,           color: 'var(--text-secondary)' },
    { path: 'twin',       label: 'Digital Twin',          icon: Brain,              color: 'var(--risk)' },
];

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function UserSummary() {
    const navigate = useNavigate();
    const { patientId, patientName, isChecking } = usePatient();

    const [patient, setPatient] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!patientId) return;
        setLoading(true);
        setError(null);
        getPatient(patientId).then(({ data, error: err }) => {
            if (err) setError(err);
            else setPatient(data);
            setLoading(false);
        });
    }, [patientId]);

    /* ── Derived values ─────────────────────────── */
    const averages = computeAverages(patient?.latest_vitals);
    const risk = patient?.current_risk_level || null;
    const RiskIcon = risk ? (riskConfig[risk]?.icon || Shield) : Shield;
    const riskColor = risk ? (riskConfig[risk]?.color || 'var(--text-muted)') : 'var(--text-muted)';
    const riskBg = risk ? (riskConfig[risk]?.bg || 'transparent') : 'transparent';
    const confidence = patient?.risk_confidence ? (patient.risk_confidence * 100).toFixed(0) : null;

    /* ── Chart series ───────────────────────────── */
    const chartData = (patient?.latest_vitals || []).map((v, i) => ({
        day: `Day ${i + 1}`,
        'Sleep (hrs)': Math.round(v.sleep_hours * 10) / 10,
        'Heart Rate':  Math.round(v.heart_rate),
        'Stress %':    Math.round(v.stress_level * 100),
    }));

    /* ── Render ─────────────────────────────────── */
    if (isChecking || loading) {
        return (
            <div className="page">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
                    {[1, 2, 3].map(i => (
                        <div key={i} className="shimmer" style={{ height: 80, borderRadius: 16 }} />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page">
                <div className="glass-card" style={{ borderColor: 'var(--risk)', color: 'var(--risk)', padding: 'var(--sp-5)' }}>
                    <ShieldAlert size={20} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof error === 'string' ? error : 'Failed to load your health profile.'}
                </div>
            </div>
        );
    }

    if (!patient) {
        return (
            <div className="page">
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <User size={48} color="var(--text-muted)" style={{ opacity: 0.3, marginBottom: 'var(--sp-3)' }} />
                    <p style={{ color: 'var(--text-secondary)' }}>Your health profile is being set up...</p>
                </div>
            </div>
        );
    }

    return (
        <motion.div
            className="page"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
        >
            {/* Header */}
            <header className="page-header" style={{ marginBottom: 'var(--sp-6)' }}>
                <div>
                    <h1 style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                        <User size={28} />
                        Your Health Profile
                    </h1>
                    {patientName && (
                        <p style={{ marginTop: 'var(--sp-1)', fontSize: '1rem', color: 'var(--text-secondary)' }}>
                            {patientName}
                        </p>
                    )}
                </div>

                {/* Risk Badge */}
                {risk && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
                        padding: 'var(--sp-2) var(--sp-4)',
                        background: riskBg,
                        border: `1px solid ${riskColor}`,
                        borderRadius: 12,
                    }}>
                        <RiskIcon size={20} color={riskColor} />
                        <div>
                            <div style={{ fontWeight: 700, color: riskColor, fontFamily: 'var(--font-data)' }}>
                                {risk} Risk
                            </div>
                            {confidence && (
                                <div className="data-label" style={{ fontSize: '0.7rem' }}>
                                    {confidence}% confidence
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </header>

            {/* Stat Cards */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 'var(--sp-4)',
                marginBottom: 'var(--sp-6)',
            }}>
                {[
                    { label: 'Avg Sleep',    value: `${averages.sleep_hours} hrs`,  icon: Moon,     color: 'var(--safe)' },
                    { label: 'Heart Rate',   value: `${averages.heart_rate} bpm`,   icon: Heart,    color: 'var(--caution)' },
                    { label: 'Stress Level', value: `${averages.stress_level}%`,    icon: Brain,    color: 'var(--risk)' },
                    { label: 'Sleep Quality',value: `${averages.sleep_quality}%`,   icon: Activity, color: 'var(--predict)' },
                ].map(({ label, value, icon: Icon, color }) => (
                    <div key={label} className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-4)' }}>
                        <Icon size={24} color={color} style={{ marginBottom: 'var(--sp-2)' }} />
                        <div style={{
                            fontSize: '1.5rem', fontWeight: 700,
                            fontFamily: 'var(--font-data)', color,
                        }}>
                            {value}
                        </div>
                        <div className="data-label" style={{ marginTop: 'var(--sp-1)' }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* 7-Day Vitals Trend */}
            {chartData.length > 0 && (
                <>
                    <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                        7-Day Lifestyle History
                    </h2>
                    <div className="glass-card" style={{ marginBottom: 'var(--sp-6)', padding: 'var(--sp-3)' }}>
                        <ResponsiveContainer width="100%" height={200}>
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="sleep" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%"  stopColor="var(--safe)"    stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="var(--safe)"    stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="hr" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%"  stopColor="var(--caution)" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="var(--caution)" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="stress" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%"  stopColor="var(--risk)"    stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="var(--risk)"    stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
                                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--border)' }} />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--card)', border: '1px solid var(--border)',
                                        borderRadius: 8, color: 'var(--text-primary)', fontSize: '0.8rem',
                                    }}
                                />
                                <Legend wrapperStyle={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} />
                                <Area type="monotone" dataKey="Sleep (hrs)" stroke="var(--safe)"    fill="url(#sleep)"  strokeWidth={2} dot={false} />
                                <Area type="monotone" dataKey="Heart Rate"  stroke="var(--caution)" fill="url(#hr)"     strokeWidth={2} dot={false} />
                                <Area type="monotone" dataKey="Stress %"    stroke="var(--risk)"    fill="url(#stress)" strokeWidth={2} dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}

            {/* Quick Actions */}
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                Analysis Tools
            </h2>
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 'var(--sp-3)',
            }}>
                {TOOLS.map(({ path, label, icon: Icon, color }) => (
                    <motion.button
                        key={path}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => navigate(`/predictions/${path}`)}
                        style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center',
                            gap: 'var(--sp-2)', padding: 'var(--sp-4)',
                            background: 'var(--card)', border: '1px solid var(--border)',
                            borderRadius: 12, cursor: 'pointer',
                            transition: 'border-color var(--duration-normal) var(--ease-out)',
                            textAlign: 'center',
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = color}
                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                    >
                        <Icon size={24} color={color} />
                        <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                            {label}
                        </span>
                    </motion.button>
                ))}
            </div>
        </motion.div>
    );
}
