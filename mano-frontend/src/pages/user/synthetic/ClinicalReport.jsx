/* ============================================================
   MANO AMISE — Clinical Report Generator
   
   Auto-generates structured clinical narratives from patient data,
   LSTM risk predictions, and PPO intervention recommendations.
   ============================================================ */
import { useState, useCallback, useEffect } from 'react';
import { getPatient, generateReport } from '../../../api/client';
import { usePatient } from '../../../contexts/PatientContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText, Loader, AlertTriangle, Copy, Check,
    ChevronDown, ChevronUp, AlertCircle, Info, ShieldAlert
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

/* ── Severity styling ────────────────────────────── */
const severityConfig = {
    critical: {
        bg: 'rgba(255, 76, 76, 0.08)',
        border: 'var(--risk)',
        icon: ShieldAlert,
        label: 'CRITICAL',
    },
    warning: {
        bg: 'rgba(251, 191, 36, 0.08)',
        border: 'var(--caution)',
        icon: AlertCircle,
        label: 'ATTENTION',
    },
    info: {
        bg: 'rgba(99, 102, 241, 0.05)',
        border: 'var(--border)',
        icon: Info,
        label: 'INFO',
    },
};

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function ClinicalReport() {
    const { patientId } = usePatient();
    const [selectedId, setSelectedId] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [copied, setCopied] = useState(false);
    const [showFullText, setShowFullText] = useState(false);

    /* ── Generate report ──────────────────────── */
    const handleSelectPatient = useCallback(async (id) => {
        setSelectedId(id);
        setResult(null);
        setError(null);
        setLoading(true);
        setCopied(false);
        setShowFullText(false);

        const { data: ptData, error: ptErr } = await getPatient(id);
        if (ptErr) { setError(ptErr); setLoading(false); return; }

        const state = buildPatientState(ptData);
        const { data, error: repErr } = await generateReport({
            patient_state: state,
            patient_name: ptData.name || `Patient #${id}`,
            patient_age: ptData.age,
            patient_gender: ptData.gender,
            include_recommendations: true,
        });
        setLoading(false);

        if (repErr) { setError(repErr); return; }
        setResult(data);
    }, []);

    /* ── Auto-load logged-in user's patient ───── */
    useEffect(() => {
        if (patientId) handleSelectPatient(patientId);
    }, [patientId]); // eslint-disable-line react-hooks/exhaustive-deps

    /* ── Copy full text ───────────────────────── */
    const handleCopy = useCallback(() => {
        if (result?.full_report_text) {
            navigator.clipboard.writeText(result.full_report_text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    }, [result]);

    /* ── Risk color ───────────────────────────── */
    const riskColor = {
        Low: 'var(--safe)', Medium: 'var(--caution)', High: 'var(--risk)',
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
                        <FileText size={28} />
                        Clinical Report
                    </h1>
                    <p className="data-label" style={{ marginTop: 'var(--sp-1)' }}>
                        AI-generated clinical narratives from patient data, risk predictions, and interventions
                    </p>
                </div>
            </header>



            {/* Loading */}
            {loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-6)' }}>
                    <Loader size={32} className="spin" color="var(--predict)" />
                    <p style={{ marginTop: 'var(--sp-2)', color: 'var(--text-secondary)' }}>
                        Analyzing vitals → Predicting risk → Generating report...
                    </p>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card" style={{
                    borderColor: 'var(--risk)', color: 'var(--risk)', marginBottom: 'var(--sp-5)',
                }}>
                    <AlertTriangle size={16} style={{ marginRight: 'var(--sp-2)', verticalAlign: 'middle' }} />
                    {typeof error === 'string' ? error : 'Report generation failed.'}
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
                        {/* Report Header */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-4)',
                            display: 'flex', justifyContent: 'space-between',
                            alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--sp-3)',
                        }}>
                            <div>
                                <div className="data-label" style={{ fontSize: '0.7rem' }}>Report ID</div>
                                <div style={{
                                    fontFamily: 'var(--font-data)', fontSize: '0.9rem',
                                    color: 'var(--text-secondary)',
                                }}>
                                    #{result.report_id}
                                </div>
                                <div style={{
                                    fontSize: '1.2rem', fontWeight: 600,
                                    marginTop: 'var(--sp-1)',
                                }}>
                                    {result.patient_identifier}
                                </div>
                                <div className="data-label" style={{ fontSize: '0.7rem', marginTop: 'var(--sp-1)' }}>
                                    {new Date(result.generated_at).toLocaleString()}
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div className="data-label" style={{ fontSize: '0.65rem' }}>Risk</div>
                                    <div style={{
                                        fontSize: '1.3rem', fontWeight: 700,
                                        color: riskColor[result.risk_classification],
                                        fontFamily: 'var(--font-data)',
                                    }}>
                                        {result.risk_classification}
                                    </div>
                                    <div className="data-label" style={{ fontSize: '0.65rem' }}>
                                        {(result.risk_confidence * 100).toFixed(0)}% conf
                                    </div>
                                </div>
                                <button
                                    onClick={handleCopy}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 4,
                                        padding: '8px 14px', borderRadius: 8,
                                        background: copied ? 'rgba(45,212,191,0.15)' : 'rgba(99,102,241,0.15)',
                                        border: 'none',
                                        color: copied ? 'var(--safe)' : 'var(--predict)',
                                        cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600,
                                    }}
                                >
                                    {copied ? <><Check size={14} /> Copied</> : <><Copy size={14} /> Copy Report</>}
                                </button>
                            </div>
                        </div>

                        {/* Executive Summary */}
                        <div className="glass-card" style={{
                            marginBottom: 'var(--sp-4)',
                            borderLeft: `3px solid ${riskColor[result.risk_classification]}`,
                        }}>
                            <div className="data-label" style={{ marginBottom: 'var(--sp-1)', fontSize: '0.7rem' }}>
                                Executive Summary
                            </div>
                            <p style={{ fontSize: '0.95rem', lineHeight: 1.7 }}>
                                {result.executive_summary}
                            </p>
                        </div>

                        {/* Report Sections */}
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--sp-3)' }}>
                            Report Sections
                        </h2>

                        {result.sections.map((section, i) => {
                            const cfg = severityConfig[section.severity] || severityConfig.info;
                            const SevIcon = cfg.icon;
                            return (
                                <motion.div
                                    key={i}
                                    className="glass-card"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.08 }}
                                    style={{
                                        marginBottom: 'var(--sp-3)',
                                        background: cfg.bg,
                                        borderLeft: `3px solid ${cfg.border}`,
                                    }}
                                >
                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
                                        marginBottom: 'var(--sp-2)',
                                    }}>
                                        <SevIcon size={16} color={cfg.border} />
                                        <span style={{
                                            fontWeight: 600, fontSize: '0.95rem',
                                        }}>
                                            {section.title}
                                        </span>
                                        {section.severity !== 'info' && (
                                            <span style={{
                                                fontSize: '0.6rem', fontWeight: 700,
                                                padding: '2px 6px', borderRadius: 4,
                                                background: `${cfg.border}20`,
                                                color: cfg.border,
                                            }}>
                                                {cfg.label}
                                            </span>
                                        )}
                                    </div>
                                    <p style={{ fontSize: '0.9rem', lineHeight: 1.7, color: 'var(--text-secondary)' }}>
                                        {section.content}
                                    </p>
                                </motion.div>
                            );
                        })}

                        {/* Intervention badge */}
                        {result.recommended_intervention && (
                            <div className="glass-card" style={{
                                marginBottom: 'var(--sp-4)', textAlign: 'center',
                                borderTop: '2px solid var(--predict)',
                            }}>
                                <div className="data-label" style={{ fontSize: '0.7rem', marginBottom: 'var(--sp-1)' }}>
                                    Recommended Intervention
                                </div>
                                <div style={{
                                    fontSize: '1.3rem', fontWeight: 700,
                                    color: 'var(--predict)',
                                }}>
                                    {result.recommended_intervention}
                                </div>
                            </div>
                        )}

                        {/* Full Text Toggle */}
                        <button
                            onClick={() => setShowFullText(!showFullText)}
                            style={{
                                width: '100%', padding: 'var(--sp-2)',
                                background: 'var(--surface)', border: '1px solid var(--border)',
                                borderRadius: 8, color: 'var(--text-secondary)',
                                cursor: 'pointer', fontSize: '0.85rem',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                marginBottom: 'var(--sp-3)',
                            }}
                        >
                            {showFullText ? <><ChevronUp size={14} /> Hide Full Text</> : <><ChevronDown size={14} /> Show Full Text</>}
                        </button>

                        <AnimatePresence>
                            {showFullText && (
                                <motion.pre
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    style={{
                                        background: 'var(--void)',
                                        padding: 'var(--sp-3)',
                                        borderRadius: 8,
                                        border: '1px solid var(--border)',
                                        fontSize: '0.75rem',
                                        lineHeight: 1.6,
                                        color: 'var(--text-secondary)',
                                        fontFamily: 'var(--font-data)',
                                        whiteSpace: 'pre-wrap',
                                        overflow: 'hidden',
                                    }}
                                >
                                    {result.full_report_text}
                                </motion.pre>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Loading profile */}
            {!selectedId && !loading && (
                <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
                    <FileText size={48} color="var(--text-muted)" style={{ marginBottom: 'var(--sp-3)', opacity: 0.3 }} />
                    <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>Generating your clinical report...</p>
                </div>
            )}
        </motion.div>
    );
}
