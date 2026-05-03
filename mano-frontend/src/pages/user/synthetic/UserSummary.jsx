/* ============================================================
   MANO AMISE — User Health Profile (My Profile)

   Landing page for the Predictions & Insights section.
   Shows the user's current risk level, 7-day lifestyle metrics,
   an inline vitals editor, and quick-access tool links.

   DATA FLOW:
     getPatient(patientId) → patient.latest_vitals (7-day array from DB)
     computeAverages()     → stat cards & chart
     handleSaveVitals()    → updatePatient(id, { latest_vitals }) → DB
                          → all C1 simulators/twins re-read from DB on next call

   STATIC DATA ROOT CAUSE (resolved here):
     The onboarding flow creates the patient with [day_vitals] * 7 (one seed
     row replicated 7 times) from the questionnaire. The display appeared
     "static" because users had no way to update it post-onboarding. This
     inline editor closes that gap.
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPatient, updatePatient } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import {
    User, ShieldAlert, ShieldCheck, Shield, Heart, Moon, Brain,
    Activity, SlidersHorizontal, ScanSearch, Zap, ListOrdered,
    Gauge, FileText, GitFork, RefreshCw, Pencil, Check, X, Loader,
    Info,
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
        sleep_hours:   Math.round(vitals.reduce((s, v) => s + v.sleep_hours, 0)   / n * 10) / 10,
        heart_rate:    Math.round(vitals.reduce((s, v) => s + v.heart_rate, 0)    / n),
        stress_level:  Math.round(vitals.reduce((s, v) => s + v.stress_level, 0)  / n * 100),
        sleep_quality: Math.round(vitals.reduce((s, v) => s + v.sleep_quality, 0) / n * 100),
    };
}

/* ── Build a uniform 7-day history from simple averages ─ */
function averagesToVitals(avg) {
    const day = {
        sleep_hours:   Math.max(0, Math.min(24,  parseFloat(avg.sleep_hours)  || 0)),
        sleep_quality: Math.max(0, Math.min(1,   parseFloat(avg.sleep_quality) / 100 || 0)),
        heart_rate:    Math.max(40, Math.min(200, parseFloat(avg.heart_rate)  || 40)),
        stress_level:  Math.max(0, Math.min(1,   parseFloat(avg.stress_level) / 100 || 0)),
    };
    return Array(7).fill(null).map(() => ({ ...day }));
}

/* ── Quick-action tool links ─────────────────────── */
const TOOLS = [
    { path: 'simulate',    label: 'Simulation Lab',      icon: Activity,          color: 'var(--predict)' },
    { path: 'compare',     label: 'Intervention Compare', icon: GitFork,           color: 'var(--safe)' },
    { path: 'prescribe',   label: 'AI Prescription',      icon: RefreshCw,         color: 'var(--caution)' },
    { path: 'what-if',     label: 'What-If Simulator',    icon: SlidersHorizontal, color: 'var(--predict)' },
    { path: 'explain',     label: 'XAI Explainer',        icon: ScanSearch,        color: 'var(--risk)' },
    { path: 'next-action', label: 'Next Best Action',     icon: Zap,               color: 'var(--caution)' },
    { path: 'sequencer',   label: 'Sequencer',            icon: ListOrdered,       color: 'var(--safe)' },
    { path: 'uncertainty', label: 'Uncertainty',          icon: Gauge,             color: 'var(--predict)' },
    { path: 'report',      label: 'Clinical Report',      icon: FileText,          color: 'var(--text-secondary)' },
    { path: 'twin',        label: 'Digital Twin',         icon: Brain,             color: 'var(--risk)' },
];

/* ── Vitals field config ─────────────────────────── */
const VITAL_FIELDS = [
    {
        key: 'sleep_hours',
        label: 'Avg Sleep',
        unit: 'hrs',
        icon: Moon,
        color: 'var(--safe)',
        min: 0, max: 12, step: 0.5,
        display: (v) => `${v} hrs`,
        hint: '0 – 12 hrs',
    },
    {
        key: 'heart_rate',
        label: 'Heart Rate',
        unit: 'bpm',
        icon: Heart,
        color: 'var(--caution)',
        min: 40, max: 200, step: 1,
        display: (v) => `${v} bpm`,
        hint: '40 – 200 bpm',
    },
    {
        key: 'stress_level',
        label: 'Stress Level',
        unit: '%',
        icon: Brain,
        color: 'var(--risk)',
        min: 0, max: 100, step: 1,
        display: (v) => `${v}%`,
        hint: '0 – 100 %',
    },
    {
        key: 'sleep_quality',
        label: 'Sleep Quality',
        unit: '%',
        icon: Activity,
        color: 'var(--predict)',
        min: 0, max: 100, step: 1,
        display: (v) => `${v}%`,
        hint: '0 – 100 %',
    },
];

/* ══════════════════════════════════════════════════
   INLINE VITALS EDITOR
   ══════════════════════════════════════════════════ */
function VitalsEditor({ averages, onSave, onCancel, saving, saveError }) {
    const [draft, setDraft] = useState({ ...averages });

    const set = (key, val) => setDraft(prev => ({ ...prev, [key]: val }));

    return (
        <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            className="glass-card"
            style={{ marginBottom: 'var(--sp-6)', borderColor: 'var(--predict)', borderWidth: 1, borderStyle: 'solid' }}
        >
            {/* Editor header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-4)' }}>
                <div>
                    <h2 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                        <Pencil size={16} color="var(--predict)" />
                        Update My Health Baseline
                    </h2>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)', display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
                        <Info size={12} />
                        These values set your baseline for all C1 simulators, the Digital Twin, and AI Prescription.
                    </p>
                </div>
            </div>

            {/* Sliders */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: 'var(--sp-4)',
                marginBottom: 'var(--sp-5)',
            }}>
                {VITAL_FIELDS.map(({ key, label, unit, icon: Icon, color, min, max, step, display, hint }) => (
                    <div key={key} style={{
                        padding: 'var(--sp-3)',
                        background: 'var(--surface)',
                        borderRadius: 12,
                        border: '1px solid var(--border)',
                    }}>
                        {/* Label row */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--sp-2)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                                <Icon size={15} color={color} />
                                <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{label}</span>
                            </div>
                            <span style={{
                                fontFamily: 'var(--font-data)',
                                fontWeight: 700,
                                fontSize: '1rem',
                                color,
                            }}>
                                {display(draft[key])}
                            </span>
                        </div>

                        {/* Slider */}
                        <input
                            id={`vitals-slider-${key}`}
                            type="range"
                            min={min}
                            max={max}
                            step={step}
                            value={draft[key]}
                            onChange={e => set(key, parseFloat(e.target.value))}
                            style={{ width: '100%', accentColor: color, cursor: 'pointer' }}
                        />

                        {/* Min / max hint */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 'var(--sp-1)' }}>
                            <span>{min}{unit}</span>
                            <span className="data-label">{hint}</span>
                            <span>{max}{unit}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Error */}
            {saveError && (
                <div style={{ color: 'var(--risk)', fontSize: '0.85rem', marginBottom: 'var(--sp-3)' }}>
                    ⚠ {typeof saveError === 'string' ? saveError : 'Save failed. Please try again.'}
                </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 'var(--sp-3)', justifyContent: 'flex-end' }}>
                <button
                    onClick={onCancel}
                    disabled={saving}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 'var(--sp-1)',
                        padding: 'var(--sp-2) var(--sp-4)',
                        background: 'transparent',
                        border: '1px solid var(--border)',
                        borderRadius: 8, color: 'var(--text-secondary)',
                        cursor: 'pointer', fontSize: '0.875rem',
                    }}
                >
                    <X size={14} /> Cancel
                </button>
                <button
                    onClick={() => onSave(draft)}
                    disabled={saving}
                    className="btn-primary"
                    style={{
                        display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-2)',
                        padding: 'var(--sp-2) var(--sp-5)',
                        minWidth: 140,
                    }}
                >
                    {saving ? (
                        <><Loader size={14} className="spin" /> Saving…</>
                    ) : (
                        <><Check size={14} /> Save Baseline</>
                    )}
                </button>
            </div>
        </motion.div>
    );
}

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function UserSummary() {
    const navigate = useNavigate();
    const { patientId, patientName, isChecking } = usePatient();

    const [patient, setPatient]       = useState(null);
    const [loading, setLoading]       = useState(false);
    const [fetchError, setFetchError] = useState(null);

    const [editing, setEditing]       = useState(false);
    const [saving, setSaving]         = useState(false);
    const [saveError, setSaveError]   = useState(null);
    const [saveSuccess, setSaveSuccess] = useState(false);

    /* ── Fetch patient ──────────────────────────── */
    const fetchPatient = useCallback(() => {
        if (!patientId) return;
        setLoading(true);
        setFetchError(null);
        getPatient(patientId).then(({ data, error: err }) => {
            if (err) setFetchError(err);
            else setPatient(data);
            setLoading(false);
        });
    }, [patientId]);

    useEffect(() => { fetchPatient(); }, [fetchPatient]);

    /* ── Derived values ─────────────────────────── */
    const averages  = computeAverages(patient?.latest_vitals);
    const risk      = patient?.current_risk_level || null;
    const RiskIcon  = risk ? (riskConfig[risk]?.icon || Shield) : Shield;
    const riskColor = risk ? (riskConfig[risk]?.color || 'var(--text-muted)') : 'var(--text-muted)';
    const riskBg    = risk ? (riskConfig[risk]?.bg    || 'transparent') : 'transparent';
    const confidence = patient?.risk_confidence ? (patient.risk_confidence * 100).toFixed(0) : null;

    /* ── Chart series ───────────────────────────── */
    const chartData = (patient?.latest_vitals || []).map((v, i) => ({
        day: `Day ${i + 1}`,
        'Sleep (hrs)': Math.round(v.sleep_hours * 10) / 10,
        'Heart Rate':  Math.round(v.heart_rate),
        'Stress %':    Math.round(v.stress_level * 100),
    }));

    /* ── Save handler ───────────────────────────── */
    const handleSaveVitals = async (draftAverages) => {
        if (!patientId) return;
        setSaving(true);
        setSaveError(null);

        // Convert simple averages → 7-day array (uniform baseline)
        const latest_vitals = averagesToVitals(draftAverages);
        const { error: err } = await updatePatient(patientId, { latest_vitals });

        setSaving(false);
        if (err) {
            setSaveError(err);
        } else {
            setEditing(false);
            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 3000);
            fetchPatient(); // Refresh display with new values
        }
    };

    /* ── Render: loading / error states ─────────── */
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

    if (fetchError) {
        return (
            <div className="page">
                <div className="glass-card" style={{ borderColor: 'var(--risk)', color: 'var(--risk)', padding: 'var(--sp-5)' }}>
                    <ShieldAlert size={20} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof fetchError === 'string' ? fetchError : 'Failed to load your health profile.'}
                </div>
            </div>
        );
    }

    if (!patient) {
        return (
            <div className="page">
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <User size={48} color="var(--text-muted)" style={{ opacity: 0.3, marginBottom: 'var(--sp-3)' }} />
                    <p style={{ color: 'var(--text-secondary)' }}>Your health profile is being set up…</p>
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
            {/* ── Header ─────────────────────────────────── */}
            <header className="page-header" style={{ marginBottom: 'var(--sp-6)' }}>
                <div>
                    <h1 style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                        <User size={28} />
                        My Profile
                    </h1>
                    {patientName && (
                        <p style={{ marginTop: 'var(--sp-1)', fontSize: '1rem', color: 'var(--text-secondary)' }}>
                            {patientName}
                        </p>
                    )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                    {/* Risk badge */}
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

                    {/* Edit toggle button */}
                    {!editing && (
                        <button
                            id="edit-vitals-btn"
                            onClick={() => { setEditing(true); setSaveError(null); }}
                            className="btn-primary"
                            style={{
                                display: 'inline-flex', alignItems: 'center', gap: 'var(--sp-2)',
                                padding: 'var(--sp-2) var(--sp-4)', fontSize: '0.875rem',
                            }}
                        >
                            <Pencil size={15} />
                            Update Vitals
                        </button>
                    )}
                </div>
            </header>

            {/* ── Save success toast ──────────────────────── */}
            <AnimatePresence>
                {saveSuccess && (
                    <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
                            padding: 'var(--sp-3) var(--sp-4)',
                            background: 'rgba(45,212,191,0.12)',
                            border: '1px solid var(--safe)',
                            borderRadius: 10,
                            color: 'var(--safe)',
                            fontSize: '0.875rem',
                            marginBottom: 'var(--sp-5)',
                        }}
                    >
                        <Check size={16} />
                        Baseline updated — all C1 tools will use your new values.
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Inline vitals editor ────────────────────── */}
            <AnimatePresence>
                {editing && (
                    <VitalsEditor
                        averages={averages}
                        onSave={handleSaveVitals}
                        onCancel={() => { setEditing(false); setSaveError(null); }}
                        saving={saving}
                        saveError={saveError}
                    />
                )}
            </AnimatePresence>

            {/* ── Stat cards ──────────────────────────────── */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 'var(--sp-4)',
                marginBottom: 'var(--sp-6)',
            }}>
                {VITAL_FIELDS.map(({ key, label, icon: Icon, color, display, unit }) => {
                    const raw = averages[key];
                    return (
                        <div key={key} className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-4)' }}>
                            <Icon size={24} color={color} style={{ marginBottom: 'var(--sp-2)' }} />
                            <div style={{
                                fontSize: '1.5rem', fontWeight: 700,
                                fontFamily: 'var(--font-data)', color,
                            }}>
                                {display(raw)}
                            </div>
                            <div className="data-label" style={{ marginTop: 'var(--sp-1)' }}>{label}</div>
                        </div>
                    );
                })}
            </div>

            {/* ── 7-Day Vitals Trend ──────────────────────── */}
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

            {/* ── Analysis Tools grid ─────────────────────── */}
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
