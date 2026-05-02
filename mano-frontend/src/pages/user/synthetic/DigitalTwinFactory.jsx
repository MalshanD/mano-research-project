import { useState } from 'react';
import { generateTwin, personalTwin } from '../../../api/client';
import {
    Dna, CloudSun, Activity, Brain, Pill, TrendingDown,
    ChevronRight, Loader2, MapPin, User, Heart, Moon, Gauge,
    ToggleLeft, ToggleRight, AlertTriangle
} from 'lucide-react';

const PIPELINE_STAGES = [
    { label: 'Genesis', icon: Dna, desc: 'CTGAN Profile', color: '#a78bfa' },
    { label: 'Embody', icon: Activity, desc: 'TimeGAN Vitals', color: '#60a5fa' },
    { label: 'Context', icon: CloudSun, desc: 'Weather / SAD', color: '#fbbf24' },
    { label: 'Diagnose', icon: Brain, desc: 'LSTM Risk', color: '#f87171' },
    { label: 'Prescribe', icon: Pill, desc: 'PPO Agent', color: '#34d399' },
    { label: 'Simulate', icon: TrendingDown, desc: 'Seq2Seq', color: '#818cf8' },
    { label: 'Prognosis', icon: Gauge, desc: 'LSTM Re‑assess', color: '#fb923c' },
];

const PERSONAL_STAGES = [
    { label: 'Your Data', icon: User, desc: 'Questionnaire', color: '#a78bfa' },
    { label: 'Your Vitals', icon: Heart, desc: 'Self-Report', color: '#60a5fa' },
    { label: 'Context', icon: CloudSun, desc: 'Weather / SAD', color: '#fbbf24' },
    { label: 'Diagnose', icon: Brain, desc: 'LSTM Risk', color: '#f87171' },
    { label: 'Prescribe', icon: Pill, desc: 'PPO Agent', color: '#34d399' },
    { label: 'Simulate', icon: TrendingDown, desc: 'Seq2Seq', color: '#818cf8' },
    { label: 'Prognosis', icon: Gauge, desc: 'LSTM Re‑assess', color: '#fb923c' },
];

const CITIES = [
    'Colombo', 'Kandy', 'London', 'New York', 'Tokyo',
    'Sydney', 'Berlin', 'Toronto', 'Mumbai', 'Singapore',
    'Stockholm', 'Helsinki', 'Reykjavik',
];

const RISK_COLORS = { Low: '#34d399', Medium: '#fbbf24', High: '#f87171' };

const DAY_LABELS = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'];

const inputStyle = {
    width: '100%', padding: '8px 10px', borderRadius: 8,
    background: 'var(--glass-bg)', border: '1px solid var(--glass-border)',
    color: 'var(--text-primary)', fontSize: 13,
};
const labelStyle = { fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4, fontWeight: 600 };

// ── Reusable Components ──

function RiskBadge({ level, confidence }) {
    return (
        <span style={{
            background: RISK_COLORS[level] || '#666',
            color: '#000', padding: '4px 12px', borderRadius: 20,
            fontWeight: 700, fontSize: 13,
        }}>
            {level} ({(confidence * 100).toFixed(0)}%)
        </span>
    );
}

function VitalsChart({ vitals, label, color }) {
    if (!vitals?.length) return null;
    const maxHR = Math.max(...vitals.map(v => v.heart_rate));
    const minHR = Math.min(...vitals.map(v => v.heart_rate));
    const hrRange = maxHR - minHR || 1;
    return (
        <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>{label}</div>
            <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 80 }}>
                {vitals.map((v, i) => {
                    const h = 20 + ((v.heart_rate - minHR) / hrRange) * 56;
                    return (
                        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                            <div style={{
                                width: '100%', height: h, borderRadius: 4,
                                background: `linear-gradient(180deg, ${color}88, ${color}33)`,
                                border: `1px solid ${color}66`,
                            }} title={`HR: ${v.heart_rate.toFixed(0)} | Sleep: ${v.sleep_hours.toFixed(1)}h | Stress: ${(v.stress_level * 100).toFixed(0)}%`} />
                            <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>D{v.day}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function ScoreBar({ label, value, color }) {
    return (
        <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span style={{ color, fontWeight: 600 }}>{(value * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: 6, background: 'var(--glass-bg)', borderRadius: 3 }}>
                <div style={{ height: '100%', width: `${value * 100}%`, background: color, borderRadius: 3, transition: 'width 0.6s ease' }} />
            </div>
        </div>
    );
}

function SADPathwayBars({ pathways }) {
    if (!pathways) return null;
    return (
        <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6 }}>SAD Biological Pathways</div>
            <ScoreBar label="Serotonin Deficit (mood)" value={pathways.serotonin_deficit} color="#f87171" />
            <ScoreBar label="Melatonin Excess (sleep)" value={pathways.melatonin_excess} color="#818cf8" />
            <ScoreBar label="Circadian Disruption (rhythm)" value={pathways.circadian_disruption} color="#fbbf24" />
        </div>
    );
}

// ── Twin Card (shared between modes) ──

function TwinCard({ twin }) {
    const d = twin.demographics;
    const w = twin.weather;
    const b = twin.behavioral_scores;
    const reduction = twin.outcome.risk_reduction_pct;
    const isPersonal = twin.mode === 'personal';

    return (
        <div className="glass-card" style={{ padding: 24, marginBottom: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                        width: 44, height: 44, borderRadius: '50%',
                        background: isPersonal
                            ? 'linear-gradient(135deg, #34d399, #60a5fa)'
                            : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                        display: 'grid', placeItems: 'center',
                    }}>
                        <User size={22} color="#fff" />
                    </div>
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 16 }}>
                            {isPersonal ? 'Your Simulation' : `Twin #${twin.twin_id}`}
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                            {d.age}y {d.gender} · {d.country}
                            {isPersonal && <span style={{ marginLeft: 8, color: '#34d399', fontWeight: 600 }}>● Personal</span>}
                        </div>
                    </div>
                </div>
                <div style={{ textAlign: 'right', fontSize: 12, color: 'var(--text-dim)' }}>
                    {twin.pipeline_ms.toFixed(0)}ms pipeline
                </div>
            </div>

            {/* Risk Before → After */}
            <div style={{
                display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center',
                gap: 12, padding: 16, background: 'var(--glass-bg)', borderRadius: 12, marginBottom: 20,
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>BASELINE RISK</div>
                    <RiskBadge level={twin.baseline_diagnosis.risk_level} confidence={twin.baseline_diagnosis.confidence} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <ChevronRight size={20} color="var(--text-dim)" />
                    <div style={{
                        fontSize: 14, fontWeight: 700, marginTop: 4,
                        color: reduction > 0 ? '#34d399' : reduction < 0 ? '#f87171' : '#888',
                    }}>
                        {reduction > 0 ? '↓' : reduction < 0 ? '↑' : '→'}{Math.abs(reduction).toFixed(1)}%
                    </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>POST-TREATMENT</div>
                    <RiskBadge level={twin.outcome.post_risk.risk_level} confidence={twin.outcome.post_risk.confidence} />
                </div>
            </div>

            {/* Prescription */}
            <div style={{
                padding: 12, borderRadius: 10,
                border: '1px solid var(--accent-primary)',
                background: 'rgba(139,92,246,0.05)',
                marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12,
            }}>
                <Pill size={18} color="var(--accent-primary)" />
                <div>
                    <span style={{ fontWeight: 600 }}>{twin.prescription.intervention}</span>
                    <span style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>
                        at {(twin.prescription.intensity * 100).toFixed(0)}% intensity
                    </span>
                </div>
            </div>

            {/* Vitals Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                <VitalsChart vitals={twin.vitals.baseline} label={`${isPersonal ? 'Your' : 'Baseline'} Vitals (HR)`} color="#60a5fa" />
                <VitalsChart vitals={twin.outcome.projected_vitals} label="Post-Treatment (HR)" color="#34d399" />
            </div>

            {/* Weather Context + SAD Pathways */}
            {w && (
                <div style={{
                    padding: 12, background: 'var(--glass-bg)', borderRadius: 8, marginBottom: 16,
                }}>
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                        <span><MapPin size={13} style={{ marginRight: 4 }} />{w.city}</span>
                        <span>🌡️ {w.temperature_c}°C</span>
                        <span>☀️ UV {w.uv_index}</span>
                        <span>🌤️ {w.sunshine_hours.toFixed(1)}h sun</span>
                        <span>🌧️ {w.precipitation_hours?.toFixed(1) || '0'}h rain</span>
                        <span style={{ color: w.sad_intensity > 0.4 ? '#fbbf24' : '#34d399' }}>
                            SAD: {(w.sad_intensity * 100).toFixed(0)}%
                        </span>
                    </div>
                    <SADPathwayBars pathways={w.sad_pathways} />
                </div>
            )}

            {/* Behavioral Scores */}
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: 'var(--text-secondary)' }}>
                Behavioral Profile (C4-Compatible)
            </div>
            <ScoreBar label="Emotional Regulation" value={b.emotional_regulation} color="#a78bfa" />
            <ScoreBar label="Social Connectivity" value={b.social_connectivity} color="#60a5fa" />
            <ScoreBar label="Behavioral Stability" value={b.behavioral_stability} color="#34d399" />
            <ScoreBar label="Cognitive Flexibility" value={b.cognitive_flexibility} color="#fbbf24" />
            <ScoreBar label="Stress Coping" value={b.stress_coping} color="#f87171" />

            {/* Demographics Detail */}
            <details style={{ marginTop: 16, fontSize: 12, color: 'var(--text-dim)' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>Full Demographics</summary>
                <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
                    {Object.entries(d.all_fields).map(([k, v]) => (
                        <div key={k}><strong>{k}:</strong> {v}</div>
                    ))}
                </div>
            </details>
        </div>
    );
}

// ── Personal Mode Questionnaire ──

function PersonalForm({ onSubmit, loading }) {
    const [form, setForm] = useState({
        age: 25, gender: 'Male', family_history: false, seeking_treatment: false,
        work_interfere: 'Sometimes', city: 'Colombo', apply_weather: true,
        country: '', self_employed: false, remote_work: false, tech_industry: false,
        company_size: '', employer_benefits: '', leave_difficulty: '',
        coworker_comfort: '', supervisor_comfort: '',
    });

    const [vitals, setVitals] = useState(
        Array.from({ length: 7 }, () => ({ sleep_hours: 7, sleep_quality: 3, stress_level: 3, heart_rate: null }))
    );

    const updateVital = (day, field, value) => {
        setVitals(prev => prev.map((v, i) => i === day ? { ...v, [field]: value } : v));
    };

    const handleSubmit = () => {
        onSubmit({
            ...form,
            vitals_7d: vitals.map(v => ({
                ...v,
                heart_rate: v.heart_rate || null,
            })),
        });
    };

    return (
        <div>
            {/* Privacy Notice */}
            <div style={{
                display: 'flex', gap: 10, padding: 14, borderRadius: 10,
                background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.3)',
                marginBottom: 20, fontSize: 13, color: 'var(--text-secondary)',
            }}>
                <AlertTriangle size={18} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                    <strong style={{ color: '#34d399' }}>Privacy Notice:</strong> Your data is processed locally and used solely for this simulation.
                    It is not stored, shared, or transmitted to any third party. All computations happen in-memory on the server.
                </div>
            </div>

            {/* Core Demographics */}
            <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 14, color: 'var(--text-primary)' }}>
                    About You <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-dim)' }}>(required)</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    <div>
                        <label style={labelStyle}>Age</label>
                        <input type="number" min={14} max={90} value={form.age}
                            onChange={e => setForm(p => ({ ...p, age: +e.target.value }))} style={inputStyle} />
                    </div>
                    <div>
                        <label style={labelStyle}>Gender</label>
                        <select value={form.gender} onChange={e => setForm(p => ({ ...p, gender: e.target.value }))} style={inputStyle}>
                            {['Male', 'Female', 'Non-binary', 'Other'].map(g => <option key={g}>{g}</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={labelStyle}>Work Interference</label>
                        <select value={form.work_interfere} onChange={e => setForm(p => ({ ...p, work_interfere: e.target.value }))} style={inputStyle}>
                            {['Never', 'Rarely', 'Sometimes', 'Often'].map(w => <option key={w}>{w}</option>)}
                        </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 12 }}>
                        <input type="checkbox" checked={form.family_history}
                            onChange={e => setForm(p => ({ ...p, family_history: e.target.checked }))}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Family history</label>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 12 }}>
                        <input type="checkbox" checked={form.seeking_treatment}
                            onChange={e => setForm(p => ({ ...p, seeking_treatment: e.target.checked }))}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Seeking treatment</label>
                    </div>
                    <div>
                        <label style={labelStyle}>Location</label>
                        <select value={form.city} onChange={e => setForm(p => ({ ...p, city: e.target.value }))} style={inputStyle}>
                            {CITIES.map(c => <option key={c}>{c}</option>)}
                        </select>
                    </div>
                </div>
            </div>

            {/* 7-Day Vitals */}
            <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: 'var(--text-primary)' }}>
                    Your Last 7 Days <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-dim)' }}>(required)</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 14 }}>
                    Rate each day. Heart rate optional (from smartwatch or manual).
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px', fontSize: 12 }}>
                        <thead>
                            <tr style={{ color: 'var(--text-dim)' }}>
                                <th style={{ textAlign: 'left', fontWeight: 600, padding: '4px 6px' }}>Day</th>
                                <th style={{ fontWeight: 600, padding: '4px 6px' }}>Sleep (hrs)</th>
                                <th style={{ fontWeight: 600, padding: '4px 6px' }}>Quality (1-5)</th>
                                <th style={{ fontWeight: 600, padding: '4px 6px' }}>Stress (1-5)</th>
                                <th style={{ fontWeight: 600, padding: '4px 6px' }}>HR (opt)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {vitals.map((v, i) => (
                                <tr key={i}>
                                    <td style={{ color: 'var(--text-secondary)', fontWeight: 600, padding: '2px 6px' }}>{DAY_LABELS[i]}</td>
                                    <td style={{ padding: '2px 4px' }}>
                                        <input type="number" step="0.5" min={0} max={16} value={v.sleep_hours}
                                            onChange={e => updateVital(i, 'sleep_hours', +e.target.value)}
                                            style={{ ...inputStyle, textAlign: 'center' }} />
                                    </td>
                                    <td style={{ padding: '2px 4px' }}>
                                        <select value={v.sleep_quality} onChange={e => updateVital(i, 'sleep_quality', +e.target.value)} style={{ ...inputStyle, textAlign: 'center' }}>
                                            <option value={1}>1 - Terrible</option>
                                            <option value={2}>2 - Poor</option>
                                            <option value={3}>3 - Fair</option>
                                            <option value={4}>4 - Good</option>
                                            <option value={5}>5 - Excellent</option>
                                        </select>
                                    </td>
                                    <td style={{ padding: '2px 4px' }}>
                                        <select value={v.stress_level} onChange={e => updateVital(i, 'stress_level', +e.target.value)} style={{ ...inputStyle, textAlign: 'center' }}>
                                            <option value={1}>1 - None</option>
                                            <option value={2}>2 - Low</option>
                                            <option value={3}>3 - Medium</option>
                                            <option value={4}>4 - High</option>
                                            <option value={5}>5 - Extreme</option>
                                        </select>
                                    </td>
                                    <td style={{ padding: '2px 4px' }}>
                                        <input type="number" min={40} max={200} placeholder="—"
                                            value={v.heart_rate || ''}
                                            onChange={e => updateVital(i, 'heart_rate', e.target.value ? +e.target.value : null)}
                                            style={{ ...inputStyle, textAlign: 'center' }} />
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Optional Fields (collapsed) */}
            <details className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
                <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 14, color: 'var(--text-secondary)' }}>
                    Additional Context <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-dim)' }}>(optional, improves accuracy)</span>
                </summary>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 14 }}>
                    <div>
                        <label style={labelStyle}>Country</label>
                        <input value={form.country} onChange={e => setForm(p => ({ ...p, country: e.target.value }))}
                            placeholder="e.g. Sri Lanka" style={inputStyle} />
                    </div>
                    <div>
                        <label style={labelStyle}>Company Size</label>
                        <select value={form.company_size} onChange={e => setForm(p => ({ ...p, company_size: e.target.value }))} style={inputStyle}>
                            <option value="">— skip —</option>
                            {['1-5', '6-25', '26-100', '100-500', '500-1000', 'More than 1000'].map(s => <option key={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={labelStyle}>Coworker Comfort</label>
                        <select value={form.coworker_comfort} onChange={e => setForm(p => ({ ...p, coworker_comfort: e.target.value }))} style={inputStyle}>
                            <option value="">— skip —</option>
                            {['Yes', 'Some of them', 'No'].map(s => <option key={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={labelStyle}>Supervisor Comfort</label>
                        <select value={form.supervisor_comfort} onChange={e => setForm(p => ({ ...p, supervisor_comfort: e.target.value }))} style={inputStyle}>
                            <option value="">— skip —</option>
                            {['Yes', 'Some of them', 'No'].map(s => <option key={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={labelStyle}>Leave Difficulty</label>
                        <select value={form.leave_difficulty} onChange={e => setForm(p => ({ ...p, leave_difficulty: e.target.value }))} style={inputStyle}>
                            <option value="">— skip —</option>
                            {['Very easy', 'Somewhat easy', "Don't know", 'Somewhat difficult', 'Very difficult'].map(s => <option key={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label style={labelStyle}>Employer Benefits</label>
                        <select value={form.employer_benefits} onChange={e => setForm(p => ({ ...p, employer_benefits: e.target.value }))} style={inputStyle}>
                            <option value="">— skip —</option>
                            {['Yes', 'No', "Don't know"].map(s => <option key={s}>{s}</option>)}
                        </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 16 }}>
                        <input type="checkbox" checked={form.self_employed}
                            onChange={e => setForm(p => ({ ...p, self_employed: e.target.checked }))}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Self-employed</label>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 16 }}>
                        <input type="checkbox" checked={form.remote_work}
                            onChange={e => setForm(p => ({ ...p, remote_work: e.target.checked }))}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Remote work</label>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 16 }}>
                        <input type="checkbox" checked={form.tech_industry}
                            onChange={e => setForm(p => ({ ...p, tech_industry: e.target.checked }))}
                            style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Tech industry</label>
                    </div>
                </div>
            </details>

            {/* Submit */}
            <button onClick={handleSubmit} disabled={loading}
                style={{
                    width: '100%', padding: '12px 24px', borderRadius: 10, border: 'none', cursor: 'pointer',
                    background: 'linear-gradient(135deg, #34d399, #60a5fa)',
                    color: '#fff', fontWeight: 700, fontSize: 15,
                    opacity: loading ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
            >
                {loading ? <><Loader2 size={16} className="spin" />Running Simulation...</> : <><Brain size={16} />Run My Simulation</>}
            </button>
        </div>
    );
}

// ── Main Page ──

export default function DigitalTwinFactory() {
    const [mode, setMode] = useState('explorer'); // 'explorer' | 'personal'
    const [city, setCity] = useState('Colombo');
    const [numTwins, setNumTwins] = useState(1);
    const [applyWeather, setApplyWeather] = useState(true);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [activeStage, setActiveStage] = useState(-1);

    const stages = mode === 'personal' ? PERSONAL_STAGES : PIPELINE_STAGES;

    const animateAndRun = async (apiCall) => {
        setLoading(true);
        setError(null);
        setResult(null);
        setActiveStage(0);

        const stageInterval = setInterval(() => {
            setActiveStage(prev => {
                if (prev >= stages.length - 1) { clearInterval(stageInterval); return prev; }
                return prev + 1;
            });
        }, 300);

        const { data, error: err } = await apiCall();

        clearInterval(stageInterval);
        setActiveStage(stages.length);
        setLoading(false);

        if (err) setError(err);
        else setResult(data);
    };

    const handleExplorer = () => {
        animateAndRun(() => generateTwin({
            city: city.toLowerCase(), num_twins: numTwins, apply_weather: applyWeather,
        }));
    };

    const handlePersonal = (formData) => {
        animateAndRun(() => personalTwin(formData));
    };

    return (
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
            {/* Hero Header */}
            <div style={{ marginBottom: 24 }}>
                <h1 style={{
                    fontSize: 28, fontWeight: 800, marginBottom: 6,
                    background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                }}>
                    Digital Twin Factory
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0 }}>
                    {mode === 'personal'
                        ? 'Personalized simulation using your data — LSTM, PPO, and Seq2Seq models'
                        : 'Generate component1 patient lifecycles using all 5 models — CTGAN, TimeGAN, LSTM, PPO, Seq2Seq'
                    }
                </p>
            </div>

            {/* Mode Toggle */}
            <div className="glass-card" style={{
                padding: 12, marginBottom: 20, display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: 8,
            }}>
                <button onClick={() => { setMode('explorer'); setResult(null); }} style={{
                    padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: mode === 'explorer' ? 'var(--accent-primary)' : 'transparent',
                    color: mode === 'explorer' ? '#fff' : 'var(--text-secondary)',
                    fontWeight: 600, fontSize: 13, transition: 'all 0.2s',
                }}>
                    <Dna size={14} style={{ marginRight: 6 }} />Explorer Mode
                </button>
                <button onClick={() => { setMode('personal'); setResult(null); }} style={{
                    padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: mode === 'personal' ? '#34d399' : 'transparent',
                    color: mode === 'personal' ? '#fff' : 'var(--text-secondary)',
                    fontWeight: 600, fontSize: 13, transition: 'all 0.2s',
                }}>
                    <User size={14} style={{ marginRight: 6 }} />Personal Mode
                </button>
            </div>

            {/* Pipeline Visual */}
            <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, overflowX: 'auto' }}>
                    {stages.map((s, i) => {
                        const Icon = s.icon;
                        const isActive = i <= activeStage;
                        const isCurrent = i === activeStage && loading;
                        return (
                            <div key={i} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                                <div style={{
                                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                                    gap: 4, opacity: isActive ? 1 : 0.3, transition: 'all 0.3s ease',
                                    transform: isCurrent ? 'scale(1.1)' : 'scale(1)',
                                }}>
                                    <div style={{
                                        width: 36, height: 36, borderRadius: '50%',
                                        background: isActive ? s.color : 'var(--glass-bg)',
                                        display: 'grid', placeItems: 'center',
                                        boxShadow: isCurrent ? `0 0 12px ${s.color}88` : 'none',
                                    }}>
                                        {isCurrent ? <Loader2 size={16} color="#fff" className="spin" /> : <Icon size={16} color={isActive ? '#fff' : '#666'} />}
                                    </div>
                                    <span style={{ fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' }}>{s.label}</span>
                                    <span style={{ fontSize: 9, color: 'var(--text-dim)' }}>{s.desc}</span>
                                </div>
                                {i < stages.length - 1 && (
                                    <div style={{
                                        flex: 1, height: 2, minWidth: 12,
                                        background: i < activeStage ? s.color : 'var(--glass-border)',
                                        transition: 'background 0.3s',
                                    }} />
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Mode-specific controls */}
            {mode === 'explorer' ? (
                <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 16, alignItems: 'end' }}>
                        <div>
                            <label style={labelStyle}>Location</label>
                            <select value={city} onChange={e => setCity(e.target.value)} style={inputStyle}>
                                {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div>
                            <label style={labelStyle}>Twins</label>
                            <input type="number" min={1} max={50} value={numTwins}
                                onChange={e => setNumTwins(Math.min(50, Math.max(1, +e.target.value)))} style={inputStyle} />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingBottom: 4 }}>
                            <input type="checkbox" checked={applyWeather} onChange={e => setApplyWeather(e.target.checked)}
                                style={{ width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                            <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>SAD Modulation</label>
                        </div>
                        <button onClick={handleExplorer} disabled={loading} style={{
                            padding: '10px 24px', borderRadius: 10, border: 'none', cursor: 'pointer',
                            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                            color: '#fff', fontWeight: 700, fontSize: 14,
                            opacity: loading ? 0.7 : 1, display: 'flex', alignItems: 'center', gap: 8,
                        }}>
                            {loading ? <><Loader2 size={16} className="spin" />Generating...</> : <><Dna size={16} />Generate</>}
                        </button>
                    </div>
                </div>
            ) : (
                <PersonalForm onSubmit={handlePersonal} loading={loading} />
            )}

            {/* Error */}
            {error && (
                <div className="glass-card" style={{ padding: 16, marginBottom: 20, borderColor: '#f87171' }}>
                    <div style={{ color: '#f87171', fontWeight: 600 }}>Error: {error}</div>
                </div>
            )}

            {/* Results */}
            {result && (
                <div style={{ marginBottom: 20 }}>
                    <div style={{
                        display: 'flex', gap: 16, marginBottom: 20, fontSize: 13,
                        color: 'var(--text-secondary)',
                    }}>
                        <span>{mode === 'personal' ? '👤' : '🧬'} {result.twins.length} {mode === 'personal' ? 'simulation' : 'twin'}{result.twins.length > 1 ? 's' : ''}</span>
                        <span>⏱️ {result.total_ms.toFixed(0)}ms total</span>
                        <span>🤖 {result.models_used.join(' → ')}</span>
                    </div>
                    {result.twins.map(twin => (
                        <TwinCard key={twin.twin_id} twin={twin} />
                    ))}
                </div>
            )}
        </div>
    );
}
