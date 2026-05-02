// import { useState, useEffect, useCallback } from 'react';
// import { useAuth } from '../../../contexts/AuthContext';
// import {
//     XMarkIcon,
//     ArrowLeftIcon,
//     ArrowRightIcon,
//     CheckIcon,
//     ExclamationTriangleIcon,
//     ChartBarIcon,
//     SparklesIcon,
// } from '@heroicons/react/24/outline';

// // ─── Question config: maps question_name → input type & options ───────────────
// const QUESTION_CONFIG = {
//     Age: {
//         label: 'How old are you?',
//         type: 'number',
//         min: 10,
//         max: 100,
//         placeholder: 'Enter your age (e.g. 28)',
//         unit: 'years',
//     },
//     Gender: {
//         label: 'What is your gender?',
//         type: 'radio',
//         options: ['Male', 'Female', 'Other'],
//     },
//     Education_Level: {
//         label: 'What is your highest education level?',
//         type: 'select',
//         options: ['High School', 'Bachelor', 'Master', 'PhD', 'Other'],
//     },
//     Employment_Status: {
//         label: 'What is your current employment status?',
//         type: 'radio',
//         options: ['Employed', 'Unemployed', 'Student', 'Self-employed', 'Retired'],
//     },
//     Sleep_Hours: {
//         label: 'How many hours do you sleep per night on average?',
//         type: 'slider',
//         min: 0,
//         max: 12,
//         step: 0.5,
//         unit: 'hrs',
//         defaultValue: 7,
//     },
//     Physical_Activity_Hrs: {
//         label: 'How many hours per day do you do physical activity?',
//         type: 'slider',
//         min: 0,
//         max: 8,
//         step: 0.5,
//         unit: 'hrs',
//         defaultValue: 1,
//     },
//     Social_Support_Score: {
//         label: 'How strong is your social support network?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
//     Family_History_Mental_Illness: {
//         label: 'Does your family have a history of mental illness?',
//         type: 'yesno',
//         yesValue: '1',
//         noValue: '0',
//     },
//     Chronic_Illnesses: {
//         label: 'Do you have any chronic illnesses?',
//         type: 'yesno',
//         yesValue: '1',
//         noValue: '0',
//     },
//     Therapy: {
//         label: 'Are you currently in therapy or counselling?',
//         type: 'yesno',
//         yesValue: '1',
//         noValue: '0',
//     },
//     Meditation: {
//         label: 'Do you practice meditation or mindfulness regularly?',
//         type: 'yesno',
//         yesValue: '1',
//         noValue: '0',
//     },
//     Financial_Stress: {
//         label: 'How much financial stress do you experience?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
//     Work_Stress: {
//         label: 'How much work-related stress do you experience?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
//     Self_Esteem_Score: {
//         label: 'How would you rate your self-esteem?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
//     Life_Satisfaction_Score: {
//         label: 'How satisfied are you with your life overall?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
//     Loneliness_Score: {
//         label: 'How often do you feel lonely or isolated?',
//         type: 'slider',
//         min: 0,
//         max: 10,
//         step: 1,
//         unit: '/ 10',
//         defaultValue: 5,
//     },
// };

// // ─── Risk level → color mapping ───────────────────────────────────────────────
// const RISK_COLOR = {
//     High:   { bg: 'rgba(239,68,68,0.12)',   border: '#ef4444', text: '#b91c1c',   label: 'High Risk',   dot: '#ef4444' },
//     high:   { bg: 'rgba(239,68,68,0.12)',   border: '#ef4444', text: '#b91c1c',   label: 'High Risk',   dot: '#ef4444' },
//     medium: { bg: 'rgba(234,179,8,0.12)',   border: '#eab308', text: '#92400e',   label: 'Medium Risk', dot: '#eab308' },
//     midum:  { bg: 'rgba(234,179,8,0.12)',   border: '#eab308', text: '#92400e',   label: 'Medium Risk', dot: '#eab308' },
//     Medium: { bg: 'rgba(234,179,8,0.12)',   border: '#eab308', text: '#92400e',   label: 'Medium Risk', dot: '#eab308' },
//     low:    { bg: 'rgba(34,197,94,0.12)',   border: '#22c55e', text: '#14532d',   label: 'Low Risk',    dot: '#22c55e' },
//     Low:    { bg: 'rgba(34,197,94,0.12)',   border: '#22c55e', text: '#14532d',   label: 'Low Risk',    dot: '#22c55e' },
// };

// const METRIC_META = {
//     stress:     { label: 'Stress',     icon: '🔥', max: 100, color: '#f97316' },
//     anxiety:    { label: 'Anxiety',    icon: '💭', max: 100, color: '#0ea5e9' },
//     depression: { label: 'Depression', icon: '🌧️', max: 100, color: '#8b5cf6' },
// };

// // ─── Mini animated score ring ─────────────────────────────────────────────────
// function ScoreRing({ value, max, color, size = 96 }) {
//     const r = (size - 12) / 2;
//     const circ = 2 * Math.PI * r;
//     const pct = Math.min(100, (value / max) * 100);
//     const dash = (pct / 100) * circ;

//     return (
//         <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
//             <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={10} />
//             <circle
//                 cx={size / 2} cy={size / 2} r={r} fill="none"
//                 stroke={color} strokeWidth={10}
//                 strokeDasharray={`${dash} ${circ}`}
//                 strokeLinecap="round"
//                 style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)' }}
//             />
//         </svg>
//     );
// }

// // ─── Individual question renderer ─────────────────────────────────────────────
// function QuestionInput({ config, value, onChange }) {
//     if (!config) return null;

//     if (config.type === 'radio') {
//         return (
//             <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
//                 {config.options.map((opt) => (
//                     <button
//                         key={opt}
//                         onClick={() => onChange(opt)}
//                         style={{
//                             padding: '13px 20px',
//                             borderRadius: 14,
//                             border: value === opt ? '2px solid #7c3aed' : '2px solid #e5e7eb',
//                             background: value === opt ? 'linear-gradient(135deg,#ede9fe,#ddd6fe)' : '#fff',
//                             color: value === opt ? '#5b21b6' : '#374151',
//                             fontWeight: value === opt ? 700 : 500,
//                             fontSize: 15,
//                             cursor: 'pointer',
//                             textAlign: 'left',
//                             transition: 'all .18s ease',
//                             boxShadow: value === opt ? '0 2px 12px rgba(124,58,237,.18)' : 'none',
//                         }}
//                     >
//                         {opt}
//                     </button>
//                 ))}
//             </div>
//         );
//     }

//     if (config.type === 'select') {
//         return (
//             <select
//                 value={value || ''}
//                 onChange={(e) => onChange(e.target.value)}
//                 style={{
//                     width: '100%',
//                     padding: '13px 16px',
//                     borderRadius: 14,
//                     border: value ? '2px solid #7c3aed' : '2px solid #e5e7eb',
//                     background: '#fff',
//                     fontSize: 15,
//                     color: value ? '#1f2937' : '#9ca3af',
//                     outline: 'none',
//                     cursor: 'pointer',
//                     appearance: 'none',
//                     backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
//                     backgroundRepeat: 'no-repeat',
//                     backgroundPosition: 'right 14px center',
//                 }}
//             >
//                 <option value="" disabled>Select an option…</option>
//                 {config.options.map((opt) => (
//                     <option key={opt} value={opt}>{opt}</option>
//                 ))}
//             </select>
//         );
//     }

//     if (config.type === 'yesno') {
//         return (
//             <div style={{ display: 'flex', gap: 12 }}>
//                 {[
//                     { label: '✅ Yes', val: config.yesValue },
//                     { label: '❌ No',  val: config.noValue  },
//                 ].map(({ label, val }) => (
//                     <button
//                         key={val}
//                         onClick={() => onChange(val)}
//                         style={{
//                             flex: 1,
//                             padding: '16px 20px',
//                             borderRadius: 16,
//                             border: value === val ? '2px solid #7c3aed' : '2px solid #e5e7eb',
//                             background: value === val ? 'linear-gradient(135deg,#ede9fe,#ddd6fe)' : '#f9fafb',
//                             color: value === val ? '#5b21b6' : '#374151',
//                             fontWeight: 700,
//                             fontSize: 16,
//                             cursor: 'pointer',
//                             transition: 'all .18s ease',
//                             boxShadow: value === val ? '0 2px 12px rgba(124,58,237,.18)' : 'none',
//                         }}
//                     >
//                         {label}
//                     </button>
//                 ))}
//             </div>
//         );
//     }

//     if (config.type === 'slider') {
//         const curr = value !== undefined && value !== '' ? parseFloat(value) : config.defaultValue;
//         const pct = ((curr - config.min) / (config.max - config.min)) * 100;
//         return (
//             <div>
//                 <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
//                     <span style={{
//                         fontSize: 42,
//                         fontWeight: 900,
//                         color: '#7c3aed',
//                         fontVariantNumeric: 'tabular-nums',
//                         letterSpacing: '-2px',
//                     }}>
//                         {curr}
//                         <span style={{ fontSize: 18, color: '#9ca3af', marginLeft: 4 }}>{config.unit}</span>
//                     </span>
//                 </div>
//                 <input
//                     type="range"
//                     min={config.min}
//                     max={config.max}
//                     step={config.step}
//                     value={curr}
//                     onChange={(e) => onChange(e.target.value)}
//                     style={{
//                         width: '100%',
//                         accentColor: '#7c3aed',
//                         height: 6,
//                         cursor: 'pointer',
//                     }}
//                 />
//                 <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, color: '#9ca3af', fontSize: 12 }}>
//                     <span>{config.min}</span>
//                     <span>{config.max}</span>
//                 </div>
//             </div>
//         );
//     }

//     if (config.type === 'number') {
//         const numVal = value !== '' && value !== undefined ? Number(value) : null;
//         const tooLow  = numVal !== null && numVal < config.min;
//         const tooHigh = numVal !== null && numVal > config.max;
//         const hasError = tooLow || tooHigh;
//         return (
//             <div>
//                 <input
//                     type="number"
//                     min={config.min}
//                     max={config.max}
//                     value={value || ''}
//                     placeholder={config.placeholder}
//                     onChange={(e) => onChange(e.target.value)}
//                     style={{
//                         width: '100%',
//                         padding: '14px 18px',
//                         borderRadius: 14,
//                         border: hasError
//                             ? '2px solid #ef4444'
//                             : value ? '2px solid #7c3aed' : '2px solid #e5e7eb',
//                         fontSize: 16,
//                         outline: 'none',
//                         boxSizing: 'border-box',
//                         transition: 'border-color .18s',
//                     }}
//                 />
//                 {hasError && (
//                     <p style={{ margin: '6px 0 0 4px', fontSize: 12, color: '#ef4444', fontWeight: 600 }}>
//                         {tooLow
//                             ? `Age must be at least ${config.min} years.`
//                             : `Age must be no more than ${config.max} years.`}
//                     </p>
//                 )}
//                 {!hasError && (
//                     <p style={{ margin: '6px 0 0 4px', fontSize: 12, color: '#9ca3af' }}>
//                         Valid range: {config.min} – {config.max} years
//                     </p>
//                 )}
//             </div>
//         );
//     }

//     return null;
// }

// // ─── Results screen ───────────────────────────────────────────────────────────
// function ResultsScreen({ results, onClose, onRetake }) {
//     const entries = Object.entries(results);

//     return (
//         <div style={{ padding: '0 4px' }}>
//             {/* Header */}
//             <div style={{ textAlign: 'center', marginBottom: 28 }}>
//                 <div style={{
//                     width: 64, height: 64, borderRadius: '50%',
//                     background: 'linear-gradient(135deg,#d1fae5,#a7f3d0)',
//                     display: 'flex', alignItems: 'center', justifyContent: 'center',
//                     margin: '0 auto 14px',
//                     fontSize: 30,
//                 }}>✅</div>
//                 <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#111827' }}>
//                     Assessment Complete!
//                 </h2>
//                 <p style={{ margin: '6px 0 0', color: '#6b7280', fontSize: 14 }}>
//                     Here are your mental health screening results
//                 </p>
//             </div>

//             {/* Score cards */}
//             <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
//                 {entries.map(([key, val]) => {
//                     const meta = METRIC_META[key] || { label: key, icon: '📊', max: 100, color: '#6b7280' };
//                     const risk = RISK_COLOR[val.risk_level] || RISK_COLOR.low;
//                     const score = Math.round(val.score);
//                     return (
//                         <div
//                             key={key}
//                             style={{
//                                 display: 'flex',
//                                 alignItems: 'center',
//                                 gap: 16,
//                                 padding: '16px 20px',
//                                 borderRadius: 18,
//                                 background: risk.bg,
//                                 border: `1.5px solid ${risk.border}`,
//                             }}
//                         >
//                             {/* Ring */}
//                             <div style={{ position: 'relative', flexShrink: 0 }}>
//                                 <ScoreRing value={score} max={meta.max} color={meta.color} size={72} />
//                                 <div style={{
//                                     position: 'absolute', inset: 0,
//                                     display: 'flex', flexDirection: 'column',
//                                     alignItems: 'center', justifyContent: 'center',
//                                     fontSize: 10, fontWeight: 700, color: '#374151',
//                                 }}>
//                                     <span style={{ fontSize: 17, fontWeight: 900, color: meta.color }}>{score}</span>
//                                     <span style={{ fontSize: 9, color: '#9ca3af' }}>/ 100</span>
//                                 </div>
//                             </div>

//                             {/* Info */}
//                             <div style={{ flex: 1 }}>
//                                 <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
//                                     <span style={{ fontSize: 18 }}>{meta.icon}</span>
//                                     <span style={{ fontSize: 16, fontWeight: 700, color: '#111827' }}>
//                                         {meta.label}
//                                     </span>
//                                 </div>
//                                 <div style={{
//                                     display: 'inline-flex', alignItems: 'center', gap: 5,
//                                     padding: '3px 10px', borderRadius: 99,
//                                     background: 'white',
//                                     border: `1px solid ${risk.border}`,
//                                 }}>
//                                     <span style={{
//                                         width: 7, height: 7, borderRadius: '50%',
//                                         background: risk.dot, flexShrink: 0,
//                                     }} />
//                                     <span style={{ fontSize: 12, fontWeight: 700, color: risk.text }}>
//                                         {risk.label}
//                                     </span>
//                                 </div>
//                             </div>
//                         </div>
//                     );
//                 })}
//             </div>

//             {/* Disclaimer */}
//             <p style={{
//                 fontSize: 11, color: '#9ca3af', textAlign: 'center',
//                 padding: '0 12px', marginBottom: 20, lineHeight: 1.5,
//             }}>
//                 These results are for screening purposes only and are not a clinical diagnosis.
//                 Please consult a mental health professional for proper evaluation.
//             </p>

//             {/* Actions */}
//             <div style={{ display: 'flex', gap: 10 }}>
//                 <button
//                     onClick={onRetake}
//                     style={{
//                         flex: 1,
//                         padding: '13px',
//                         borderRadius: 14,
//                         border: '2px solid #e5e7eb',
//                         background: '#fff',
//                         color: '#374151',
//                         fontWeight: 700,
//                         fontSize: 14,
//                         cursor: 'pointer',
//                     }}
//                 >
//                     Retake
//                 </button>
//                 <button
//                     onClick={onClose}
//                     style={{
//                         flex: 2,
//                         padding: '13px',
//                         borderRadius: 14,
//                         border: 'none',
//                         background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
//                         color: '#fff',
//                         fontWeight: 700,
//                         fontSize: 14,
//                         cursor: 'pointer',
//                         boxShadow: '0 4px 16px rgba(124,58,237,.35)',
//                     }}
//                 >
//                     View My Assessments
//                 </button>
//             </div>
//         </div>
//     );
// }

// // ─── Main Modal Component ─────────────────────────────────────────────────────
// export default function MLAssessmentModal({ isOpen, onClose, onResultsReady }) {
//     const { user } = useAuth();

//     const [questions, setQuestions] = useState([]);
//     const [loadingQs, setLoadingQs] = useState(false);
//     const [loadError, setLoadError] = useState(null);

//     const [step, setStep] = useState(0);        // 0-indexed current question
//     const [answers, setAnswers] = useState({});  // { [question_id]: answer_string }

//     const [submitting, setSubmitting] = useState(false);
//     const [submitError, setSubmitError] = useState(null);
//     const [results, setResults] = useState(null);

//     // ── Fetch questions when modal opens ─────────────────────────────────────
//     useEffect(() => {
//         if (!isOpen) return;
//         setStep(0);
//         setAnswers({});
//         setResults(null);
//         setSubmitError(null);
//         setLoadError(null);
//         setLoadingQs(true);

//         fetch('http://127.0.0.1:8000/question/by-assessment/1')
//             .then((r) => {
//                 if (!r.ok) throw new Error(`HTTP ${r.status}`);
//                 return r.json();
//             })
//             .then((data) => setQuestions(data))
//             .catch((e) => setLoadError(e.message))
//             .finally(() => setLoadingQs(false));
//     }, [isOpen]);

//     // ── Helpers ────────────────────────────────────────────────────────────────
//     const currentQ = questions[step];
//     const config = currentQ ? QUESTION_CONFIG[currentQ.question_name] : null;
//     const currentAnswer = currentQ ? answers[currentQ.id] : undefined;

//     // For sliders: treat as answered if value is set; for others require non-empty
//     const isAnswered = useCallback(() => {
//         if (!currentQ) return false;
//         const cfg = QUESTION_CONFIG[currentQ.question_name];
//         if (!cfg) return currentAnswer !== undefined && currentAnswer !== '';
//         if (cfg.type === 'slider') return true; // always has a default
//         if (cfg.type === 'number') {
//             if (currentAnswer === undefined || currentAnswer === '') return false;
//             const n = Number(currentAnswer);
//             return !isNaN(n) && n >= cfg.min && n <= cfg.max;
//         }
//         return currentAnswer !== undefined && currentAnswer !== '';
//     }, [currentQ, currentAnswer]);

//     const setAnswer = useCallback((val) => {
//         setAnswers((prev) => ({ ...prev, [currentQ.id]: val }));
//     }, [currentQ]);

//     // Auto-set slider default when entering that step
//     useEffect(() => {
//         if (!currentQ) return;
//         const cfg = QUESTION_CONFIG[currentQ.question_name];
//         if (cfg?.type === 'slider' && answers[currentQ.id] === undefined) {
//             setAnswers((prev) => ({ ...prev, [currentQ.id]: String(cfg.defaultValue) }));
//         }
//     }, [step, currentQ]);

//     const handleNext = () => {
//         if (step < questions.length - 1) setStep((s) => s + 1);
//     };

//     const handlePrev = () => {
//         if (step > 0) setStep((s) => s - 1);
//     };

//     const handleSubmit = async () => {
//         setSubmitting(true);
//         setSubmitError(null);

//         const userId = user?.id;
//         if (!userId) {
//             setSubmitError('Cannot submit: user not logged in.');
//             setSubmitting(false);
//             return;
//         }

//         const payload = {
//             user_id: userId,
//             answers: questions.map((q) => ({
//                 question_id: q.id,
//                 answer: String(answers[q.id] ?? ''),
//             })),
//         };

//         try {

//             console.log("Submitting payload:", payload);


//             const res = await fetch('http://127.0.0.1:8000/answers/submit', {
//                 method: 'POST',
//                 headers: { 'Content-Type': 'application/json', accept: 'application/json' },
//                 body: JSON.stringify(payload),
//             });
//             if (!res.ok) {
//                 const txt = await res.text();
//                 throw new Error(`Server error ${res.status}: ${txt}`);
//             }
//             const data = await res.json();
//             const mlResults = data.results || data;
//             setResults(mlResults);

//             if (onResultsReady) onResultsReady(mlResults);
//         } catch (e) {
//             setSubmitError(e.message);
//         } finally {
//             setSubmitting(false);
//         }
//     };

//     const handleRetake = () => {
//         setStep(0);
//         setAnswers({});
//         setResults(null);
//         setSubmitError(null);
//     };

//     // ── Progress ───────────────────────────────────────────────────────────────
//     const progress = questions.length > 0 ? ((step + 1) / questions.length) * 100 : 0;
//     const isLast = step === questions.length - 1;

//     if (!isOpen) return null;

//     return (
//         <>
//             {/* Backdrop */}
//             <div
//                 style={{
//                     position: 'fixed', inset: 0, zIndex: 1000,
//                     background: 'rgba(0,0,0,0.55)',
//                     backdropFilter: 'blur(6px)',
//                     WebkitBackdropFilter: 'blur(6px)',
//                 }}
//             />

//             {/* Modal */}
//             <div style={{
//                 position: 'fixed', inset: 0, zIndex: 1001,
//                 display: 'flex', alignItems: 'center', justifyContent: 'center',
//                 padding: '16px',
//                 pointerEvents: 'none',
//             }}>
//                 <div style={{
//                     width: '100%',
//                     maxWidth: 520,
//                     maxHeight: '90vh',
//                     overflowY: 'auto',
//                     background: '#fff',
//                     borderRadius: 28,
//                     boxShadow: '0 32px 96px rgba(0,0,0,.25)',
//                     pointerEvents: 'all',
//                     position: 'relative',
//                     padding: '28px 28px 24px',
//                 }}>

//                     {/* ── Close button ── */}
//                     <button
//                         onClick={onClose}
//                         style={{
//                             position: 'absolute', top: 20, right: 20,
//                             width: 34, height: 34, borderRadius: '50%',
//                             border: 'none', background: '#f3f4f6', cursor: 'pointer',
//                             display: 'flex', alignItems: 'center', justifyContent: 'center',
//                         }}
//                     >
//                         <XMarkIcon style={{ width: 18, height: 18, color: '#6b7280' }} />
//                     </button>

//                     {/* ── Loading state ── */}
//                     {loadingQs && (
//                         <div style={{ textAlign: 'center', padding: '48px 0' }}>
//                             <div style={{
//                                 width: 48, height: 48,
//                                 border: '4px solid #ede9fe',
//                                 borderTopColor: '#7c3aed',
//                                 borderRadius: '50%',
//                                 animation: 'spin 0.9s linear infinite',
//                                 margin: '0 auto 16px',
//                             }} />
//                             <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
//                             <p style={{ color: '#6b7280', margin: 0 }}>Loading questions…</p>
//                         </div>
//                     )}

//                     {/* ── Load error ── */}
//                     {!loadingQs && loadError && (
//                         <div style={{ textAlign: 'center', padding: '40px 0' }}>
//                             <ExclamationTriangleIcon style={{ width: 40, height: 40, color: '#ef4444', margin: '0 auto 12px' }} />
//                             <p style={{ color: '#374151', fontWeight: 600, margin: '0 0 4px' }}>Failed to load questions</p>
//                             <p style={{ color: '#9ca3af', fontSize: 13 }}>{loadError}</p>
//                             <button
//                                 onClick={() => { setLoadError(null); setLoadingQs(true); fetch('http://127.0.0.1:8000/question/by-assessment/1').then(r=>r.json()).then(setQuestions).catch(e=>setLoadError(e.message)).finally(()=>setLoadingQs(false)); }}
//                                 style={{ marginTop: 16, padding: '10px 24px', borderRadius: 12, border: 'none', background: '#7c3aed', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
//                             >
//                                 Retry
//                             </button>
//                         </div>
//                     )}

//                     {/* ── Results screen ── */}
//                     {!loadingQs && !loadError && results && (
//                         <ResultsScreen results={results} onClose={onClose} onRetake={handleRetake} />
//                     )}

//                     {/* ── Question flow ── */}
//                     {!loadingQs && !loadError && !results && questions.length > 0 && (
//                         <>
//                             {/* Header */}
//                             <div style={{ marginBottom: 22 }}>
//                                 <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
//                                     <div style={{
//                                         width: 36, height: 36, borderRadius: 10,
//                                         background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
//                                         display: 'flex', alignItems: 'center', justifyContent: 'center',
//                                     }}>
//                                         <SparklesIcon style={{ width: 18, height: 18, color: '#fff' }} />
//                                     </div>
//                                     <div>
//                                         <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
//                                             Mental Health Assessment
//                                         </h2>
//                                         <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
//                                             Question {step + 1} of {questions.length}
//                                         </p>
//                                     </div>
//                                 </div>

//                                 {/* Progress bar */}
//                                 <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
//                                     <div style={{
//                                         height: '100%',
//                                         width: `${progress}%`,
//                                         background: 'linear-gradient(90deg,#7c3aed,#a78bfa)',
//                                         borderRadius: 99,
//                                         transition: 'width .35s ease',
//                                     }} />
//                                 </div>
//                             </div>

//                             {/* Dot navigator */}
//                             <div style={{ display: 'flex', gap: 4, marginBottom: 24, flexWrap: 'nowrap' }}>
//                                 {questions.map((q, i) => (
//                                     <button
//                                         key={q.id}
//                                         onClick={() => setStep(i)}
//                                         style={{
//                                             width: 24, height: 24, borderRadius: '50%',
//                                             border: 'none', flexShrink: 0,
//                                             background: i === step
//                                                 ? '#7c3aed'
//                                                 : answers[q.id] !== undefined
//                                                     ? '#ddd6fe'
//                                                     : '#f3f4f6',
//                                             cursor: 'pointer',
//                                             fontSize: 9,
//                                             fontWeight: 700,
//                                             color: i === step ? '#fff' : answers[q.id] !== undefined ? '#5b21b6' : '#9ca3af',
//                                             transition: 'all .15s',
//                                         }}
//                                     >
//                                         {i + 1}
//                                     </button>
//                                 ))}
//                             </div>

//                             {/* Question */}
//                             <div style={{ marginBottom: 24 }}>
//                                 <p style={{ margin: '0 0 18px', fontSize: 18, fontWeight: 700, color: '#1f2937', lineHeight: 1.4 }}>
//                                     {config?.label || currentQ?.question_name.replace(/_/g, ' ')}
//                                 </p>
//                                 <QuestionInput
//                                     config={config}
//                                     value={currentAnswer}
//                                     onChange={setAnswer}
//                                 />
//                             </div>

//                             {/* Submit error */}
//                             {submitError && (
//                                 <div style={{
//                                     padding: '10px 14px', borderRadius: 12,
//                                     background: '#fef2f2', border: '1px solid #fecaca',
//                                     color: '#b91c1c', fontSize: 13, marginBottom: 14,
//                                 }}>
//                                     ⚠️ {submitError}
//                                 </div>
//                             )}

//                             {/* Navigation */}
//                             <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
//                                 <button
//                                     onClick={handlePrev}
//                                     disabled={step === 0}
//                                     style={{
//                                         display: 'flex', alignItems: 'center', gap: 6,
//                                         padding: '11px 18px',
//                                         borderRadius: 14,
//                                         border: '2px solid #e5e7eb',
//                                         background: '#fff',
//                                         color: '#374151',
//                                         fontWeight: 600,
//                                         fontSize: 14,
//                                         cursor: step === 0 ? 'not-allowed' : 'pointer',
//                                         opacity: step === 0 ? 0.4 : 1,
//                                         transition: 'all .15s',
//                                     }}
//                                 >
//                                     <ArrowLeftIcon style={{ width: 16, height: 16 }} />
//                                     Back
//                                 </button>

//                                 {isLast ? (
//                                     <button
//                                         onClick={handleSubmit}
//                                         disabled={!isAnswered() || submitting}
//                                         style={{
//                                             display: 'flex', alignItems: 'center', gap: 7,
//                                             padding: '12px 28px',
//                                             borderRadius: 14,
//                                             border: 'none',
//                                             background: (!isAnswered() || submitting)
//                                                 ? '#e5e7eb'
//                                                 : 'linear-gradient(135deg,#7c3aed,#6d28d9)',
//                                             color: (!isAnswered() || submitting) ? '#9ca3af' : '#fff',
//                                             fontWeight: 700,
//                                             fontSize: 15,
//                                             cursor: (!isAnswered() || submitting) ? 'not-allowed' : 'pointer',
//                                             boxShadow: isAnswered() && !submitting ? '0 4px 16px rgba(124,58,237,.35)' : 'none',
//                                             transition: 'all .18s',
//                                         }}
//                                     >
//                                         {submitting ? (
//                                             <>
//                                                 <span style={{
//                                                     width: 16, height: 16,
//                                                     border: '2px solid rgba(255,255,255,.4)',
//                                                     borderTopColor: '#fff',
//                                                     borderRadius: '50%',
//                                                     animation: 'spin 0.9s linear infinite',
//                                                     display: 'inline-block',
//                                                 }} />
//                                                 Analysing…
//                                             </>
//                                         ) : (
//                                             <>
//                                                 <CheckIcon style={{ width: 17, height: 17 }} />
//                                                 Submit & Get Results
//                                             </>
//                                         )}
//                                     </button>
//                                 ) : (
//                                     <button
//                                         onClick={handleNext}
//                                         disabled={!isAnswered()}
//                                         style={{
//                                             display: 'flex', alignItems: 'center', gap: 7,
//                                             padding: '12px 24px',
//                                             borderRadius: 14,
//                                             border: 'none',
//                                             background: isAnswered()
//                                                 ? 'linear-gradient(135deg,#7c3aed,#6d28d9)'
//                                                 : '#e5e7eb',
//                                             color: isAnswered() ? '#fff' : '#9ca3af',
//                                             fontWeight: 700,
//                                             fontSize: 15,
//                                             cursor: isAnswered() ? 'pointer' : 'not-allowed',
//                                             boxShadow: isAnswered() ? '0 4px 16px rgba(124,58,237,.3)' : 'none',
//                                             transition: 'all .18s',
//                                         }}
//                                     >
//                                         Next
//                                         <ArrowRightIcon style={{ width: 16, height: 16 }} />
//                                     </button>
//                                 )}
//                             </div>
//                         </>
//                     )}
//                 </div>
//             </div>
//         </>
//     );
// }


/**
 * MLAssessmentModal.jsx
 *
 * CHANGES MADE (question input UI only):
 * ─────────────────────────────────────────────────────────────────────────────
 * 1. QUESTION_CONFIG — input types updated:
 *    • Sleep_Hours, Physical_Activity_Hrs  : 'slider' → 'number'  (decimal-aware text input)
 *    • Social_Support_Score, Financial_Stress, Work_Stress,
 *      Self_Esteem_Score, Life_Satisfaction_Score, Loneliness_Score
 *                                           : 'slider' → 'scale'  (new horizontal 0–10 button row)
 *    Each 'scale' entry gains lowLabel / highLabel for semantic anchors.
 *
 * 2. QuestionInput component:
 *    • Added 'scale' renderer  — 11 pill-buttons (0–10) in a flex row with
 *      low/high anchor labels; matches existing purple selection palette exactly.
 *    • Updated 'number' renderer — honours config.step (decimal support) and
 *      shows a unit badge inline beside the input field.
 *    • 'radio', 'select', 'yesno' — UNCHANGED (pixel-identical).
 *    • Removed 'slider' renderer — no longer referenced.
 *
 * 3. Main component — question flow section:
 *    • Replaced the step-by-step wizard (step state, handleNext, handlePrev,
 *      dot navigator) with a single-page vertical questionnaire (Google Forms style).
 *    • Each question is wrapped in a Google Forms–style card that highlights
 *      in purple when the question is answered.
 *    • Progress bar now shows answered-count / total instead of current-step / total.
 *    • 'isAnswered' per-step callback → 'allAnswered' boolean computed across
 *      all questions; gates the Submit button identically to before.
 *    • Auto-default useEffect updated: applies 'scale' defaults for all
 *      questions at once when the question list loads, and on retake.
 *    • Removed: step, handleNext, handlePrev, isAnswered callback, setAnswer
 *      callback, dot navigator JSX, Back/Next navigation buttons.
 *    • Added: answeredCount, allAnswered; single Submit button at page bottom.
 *
 * UNCHANGED:
 *    • All colours, font sizes, border radii, shadows, gradients.
 *    • ScoreRing component (pixel-identical).
 *    • ResultsScreen component (pixel-identical).
 *    • Modal backdrop, container, close button, header brand bar.
 *    • Loading state, load-error state, retry button.
 *    • All fetch URLs, payload structure, handleSubmit, handleRetake core logic.
 *    • RISK_COLOR, METRIC_META constants.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import {
    XMarkIcon,
    CheckIcon,
    ExclamationTriangleIcon,
    SparklesIcon,
} from '@heroicons/react/24/outline';

// ─── Question config ──────────────────────────────────────────────────────────
// CHANGED: 'slider' types replaced with 'number' or 'scale' (see file header).
const QUESTION_CONFIG = {
    Age: {
        label: 'How old are you?',
        type: 'number',
        min: 10,
        max: 100,
        placeholder: 'Enter your age (e.g. 28)',
        unit: 'years',
    },
    Gender: {
        label: 'What is your gender?',
        type: 'radio',
        options: ['Male', 'Female', 'Other'],
    },
    Education_Level: {
        label: 'What is your highest education level?',
        type: 'select',
        options: ['High School', 'Bachelor', 'Master', 'PhD', 'Other'],
    },
    Employment_Status: {
        label: 'What is your current employment status?',
        type: 'radio',
        options: ['Employed', 'Unemployed', 'Student', 'Self-employed', 'Retired'],
    },

    // CHANGED: was 'slider' (0–12, step 0.5) → 'number' with decimal step
    Sleep_Hours: {
        label: 'How many hours do you sleep per night on average?',
        type: 'number',
        min: 0,
        max: 12,
        step: 0.5,
        placeholder: 'e.g. 7',
        unit: 'hours',
    },

    // CHANGED: was 'slider' (0–8, step 0.5) → 'number' with decimal step
    Physical_Activity_Hrs: {
        label: 'How many hours per day do you do physical activity?',
        type: 'number',
        min: 0,
        max: 8,
        step: 0.5,
        placeholder: 'e.g. 1',
        unit: 'hours',
    },

    // CHANGED: was 'slider' → 'scale' (horizontal 0–10 button row)
    Social_Support_Score: {
        label: 'How strong is your social support network?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'Very Weak',
        highLabel: 'Very Strong',
    },

    Family_History_Mental_Illness: {
        label: 'Does your family have a history of mental illness?',
        type: 'yesno',
        yesValue: '1',
        noValue: '0',
    },
    Chronic_Illnesses: {
        label: 'Do you have any chronic illnesses?',
        type: 'yesno',
        yesValue: '1',
        noValue: '0',
    },
    Therapy: {
        label: 'Are you currently in therapy or counselling?',
        type: 'yesno',
        yesValue: '1',
        noValue: '0',
    },
    Meditation: {
        label: 'Do you practice meditation or mindfulness regularly?',
        type: 'yesno',
        yesValue: '1',
        noValue: '0',
    },

    // CHANGED: was 'slider' → 'scale'
    Financial_Stress: {
        label: 'How much financial stress do you experience?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'No Stress',
        highLabel: 'Extreme Stress',
    },

    // CHANGED: was 'slider' → 'scale'
    Work_Stress: {
        label: 'How much work-related stress do you experience?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'No Stress',
        highLabel: 'Extreme Stress',
    },

    // CHANGED: was 'slider' → 'scale'
    Self_Esteem_Score: {
        label: 'How would you rate your self-esteem?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'Very Low',
        highLabel: 'Very High',
    },

    // CHANGED: was 'slider' → 'scale'
    Life_Satisfaction_Score: {
        label: 'How satisfied are you with your life overall?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'Very Dissatisfied',
        highLabel: 'Very Satisfied',
    },

    // CHANGED: was 'slider' → 'scale'
    Loneliness_Score: {
        label: 'How often do you feel lonely or isolated?',
        type: 'scale',
        min: 0,
        max: 10,
        defaultValue: 5,
        lowLabel: 'Never',
        highLabel: 'Always',
    },
};

// ─── Risk level → color mapping (UNCHANGED) ───────────────────────────────────
const RISK_COLOR = {
    High: { bg: 'rgba(239,68,68,0.12)', border: '#ef4444', text: '#b91c1c', label: 'High Risk', dot: '#ef4444' },
    high: { bg: 'rgba(239,68,68,0.12)', border: '#ef4444', text: '#b91c1c', label: 'High Risk', dot: '#ef4444' },
    medium: { bg: 'rgba(234,179,8,0.12)', border: '#eab308', text: '#92400e', label: 'Medium Risk', dot: '#eab308' },
    midum: { bg: 'rgba(234,179,8,0.12)', border: '#eab308', text: '#92400e', label: 'Medium Risk', dot: '#eab308' },
    Medium: { bg: 'rgba(234,179,8,0.12)', border: '#eab308', text: '#92400e', label: 'Medium Risk', dot: '#eab308' },
    low: { bg: 'rgba(34,197,94,0.12)', border: '#22c55e', text: '#14532d', label: 'Low Risk', dot: '#22c55e' },
    Low: { bg: 'rgba(34,197,94,0.12)', border: '#22c55e', text: '#14532d', label: 'Low Risk', dot: '#22c55e' },
};

// ─── METRIC_META (UNCHANGED) ──────────────────────────────────────────────────
const METRIC_META = {
    stress: { label: 'Stress', icon: '🔥', max: 100, color: '#f97316' },
    anxiety: { label: 'Anxiety', icon: '💭', max: 100, color: '#0ea5e9' },
    depression: { label: 'Depression', icon: '🌧️', max: 100, color: '#8b5cf6' },
};

// ─── ScoreRing (UNCHANGED) ────────────────────────────────────────────────────
function ScoreRing({ value, max, color, size = 96 }) {
    const r = (size - 12) / 2;
    const circ = 2 * Math.PI * r;
    const pct = Math.min(100, (value / max) * 100);
    const dash = (pct / 100) * circ;

    return (
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={10} />
            <circle
                cx={size / 2} cy={size / 2} r={r} fill="none"
                stroke={color} strokeWidth={10}
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)' }}
            />
        </svg>
    );
}

// ─── Individual question renderer ─────────────────────────────────────────────
// CHANGED: Added 'scale' type. Updated 'number' to honour decimal step + unit badge.
// 'radio', 'select', 'yesno' are pixel-identical to the original.
function QuestionInput({ config, value, onChange }) {
    if (!config) return null;

    // ── radio (UNCHANGED) ─────────────────────────────────────────────────────
    if (config.type === 'radio') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {config.options.map((opt) => (
                    <button
                        key={opt}
                        onClick={() => onChange(opt)}
                        style={{
                            padding: '13px 20px',
                            borderRadius: 14,
                            border: value === opt ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                            background: value === opt ? 'linear-gradient(135deg,#ede9fe,#ddd6fe)' : '#fff',
                            color: value === opt ? '#5b21b6' : '#374151',
                            fontWeight: value === opt ? 700 : 500,
                            fontSize: 15,
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all .18s ease',
                            boxShadow: value === opt ? '0 2px 12px rgba(124,58,237,.18)' : 'none',
                        }}
                    >
                        {opt}
                    </button>
                ))}
            </div>
        );
    }

    // ── select (UNCHANGED) ────────────────────────────────────────────────────
    if (config.type === 'select') {
        return (
            <select
                value={value || ''}
                onChange={(e) => onChange(e.target.value)}
                style={{
                    width: '100%',
                    padding: '13px 16px',
                    borderRadius: 14,
                    border: value ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                    background: '#fff',
                    fontSize: 15,
                    color: value ? '#1f2937' : '#9ca3af',
                    outline: 'none',
                    cursor: 'pointer',
                    appearance: 'none',
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'right 14px center',
                }}
            >
                <option value="" disabled>Select an option…</option>
                {config.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
        );
    }

    // ── yesno (UNCHANGED) ─────────────────────────────────────────────────────
    if (config.type === 'yesno') {
        return (
            <div style={{ display: 'flex', gap: 12 }}>
                {[
                    { label: '✅ Yes', val: config.yesValue },
                    { label: '❌ No', val: config.noValue },
                ].map(({ label, val }) => (
                    <button
                        key={val}
                        onClick={() => onChange(val)}
                        style={{
                            flex: 1,
                            padding: '16px 20px',
                            borderRadius: 16,
                            border: value === val ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                            background: value === val ? 'linear-gradient(135deg,#ede9fe,#ddd6fe)' : '#f9fafb',
                            color: value === val ? '#5b21b6' : '#374151',
                            fontWeight: 700,
                            fontSize: 16,
                            cursor: 'pointer',
                            transition: 'all .18s ease',
                            boxShadow: value === val ? '0 2px 12px rgba(124,58,237,.18)' : 'none',
                        }}
                    >
                        {label}
                    </button>
                ))}
            </div>
        );
    }

    // ── NEW: scale — horizontal 0–10 button row ───────────────────────────────
    // Replaces the 0–10 slider. Renders numbered pill-buttons in a flex row
    // with low/high semantic anchor labels beneath. Uses the existing purple
    // selection palette (identical border, background, colour values to radio).
    if (config.type === 'scale') {
        const steps = [];
        for (let i = config.min; i <= config.max; i++) steps.push(i);
        const selected = value !== undefined && value !== '' ? String(value) : null;

        return (
            <div>
                {/* Numbered buttons */}
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                    {steps.map((s) => {
                        const isSelected = selected === String(s);
                        return (
                            <button
                                key={s}
                                onClick={() => onChange(String(s))}
                                style={{
                                    width: 38,
                                    height: 38,
                                    borderRadius: 10,
                                    border: isSelected ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                                    background: isSelected
                                        ? 'linear-gradient(135deg,#ede9fe,#ddd6fe)'
                                        : '#f9fafb',
                                    color: isSelected ? '#5b21b6' : '#374151',
                                    fontWeight: isSelected ? 700 : 500,
                                    fontSize: 14,
                                    cursor: 'pointer',
                                    transition: 'all .18s ease',
                                    boxShadow: isSelected ? '0 2px 8px rgba(124,58,237,.18)' : 'none',
                                    flexShrink: 0,
                                }}
                            >
                                {s}
                            </button>
                        );
                    })}
                </div>

                {/* Semantic anchor labels */}
                {config.lowLabel && config.highLabel && (
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginTop: 8,
                        fontSize: 11,
                        color: '#9ca3af',
                        fontWeight: 500,
                    }}>
                        <span>← {config.lowLabel}</span>
                        <span>{config.highLabel} →</span>
                    </div>
                )}
            </div>
        );
    }

    // ── number — UPDATED: honours decimal step; shows inline unit badge ───────
    // Previously only used for Age (integer). Now also used for Sleep_Hours
    // and Physical_Activity_Hrs (step = 0.5). Validation and error text are
    // preserved; error colours are identical to the original.
    if (config.type === 'number') {
        const numVal = value !== '' && value !== undefined ? Number(value) : null;
        const tooLow = numVal !== null && numVal < config.min;
        const tooHigh = numVal !== null && numVal > config.max;
        const hasError = tooLow || tooHigh;

        return (
            <div>
                {/* Input + unit badge row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <input
                        type="number"
                        min={config.min}
                        max={config.max}
                        step={config.step || 1}          // CHANGED: decimal step support
                        value={value || ''}
                        placeholder={config.placeholder}
                        onChange={(e) => onChange(e.target.value)}
                        style={{
                            flex: 1,
                            padding: '14px 18px',
                            borderRadius: 14,
                            border: hasError
                                ? '2px solid #ef4444'
                                : value ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                            fontSize: 16,
                            outline: 'none',
                            boxSizing: 'border-box',
                            transition: 'border-color .18s',
                        }}
                    />
                    {/* CHANGED: unit shown as an inline badge instead of inside the slider */}
                    {config.unit && (
                        <span style={{
                            fontSize: 13,
                            color: '#9ca3af',
                            fontWeight: 500,
                            whiteSpace: 'nowrap',
                        }}>
                            {config.unit}
                        </span>
                    )}
                </div>

                {/* Validation messages (colours identical to original) */}
                {hasError && (
                    <p style={{ margin: '6px 0 0 4px', fontSize: 12, color: '#ef4444', fontWeight: 600 }}>
                        {tooLow
                            ? `Must be at least ${config.min}${config.unit ? ' ' + config.unit : ''}.`
                            : `Must be no more than ${config.max}${config.unit ? ' ' + config.unit : ''}.`}
                    </p>
                )}
                {!hasError && (
                    <p style={{ margin: '6px 0 0 4px', fontSize: 12, color: '#9ca3af' }}>
                        Valid range: {config.min} – {config.max}{config.unit ? ' ' + config.unit : ''}
                    </p>
                )}
            </div>
        );
    }

    return null;
}

// ─── ResultsScreen (UNCHANGED) ────────────────────────────────────────────────
function ResultsScreen({ results, onClose, onRetake }) {
    const entries = Object.entries(results);

    return (
        <div style={{ padding: '0 4px' }}>
            {/* Header */}
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
                <div style={{
                    width: 64, height: 64, borderRadius: '50%',
                    background: 'linear-gradient(135deg,#d1fae5,#a7f3d0)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 14px',
                    fontSize: 30,
                }}>✅</div>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#111827' }}>
                    Assessment Complete!
                </h2>
                <p style={{ margin: '6px 0 0', color: '#6b7280', fontSize: 14 }}>
                    Here are your mental health screening results
                </p>
            </div>

            {/* Score cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
                {entries.map(([key, val]) => {
                    const meta = METRIC_META[key] || { label: key, icon: '📊', max: 100, color: '#6b7280' };
                    const risk = RISK_COLOR[val.risk_level] || RISK_COLOR.low;
                    const score = Math.round(val.score);
                    return (
                        <div
                            key={key}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 16,
                                padding: '16px 20px',
                                borderRadius: 18,
                                background: risk.bg,
                                border: `1.5px solid ${risk.border}`,
                            }}
                        >
                            <div style={{ position: 'relative', flexShrink: 0 }}>
                                <ScoreRing value={score} max={meta.max} color={meta.color} size={72} />
                                <div style={{
                                    position: 'absolute', inset: 0,
                                    display: 'flex', flexDirection: 'column',
                                    alignItems: 'center', justifyContent: 'center',
                                    fontSize: 10, fontWeight: 700, color: '#374151',
                                }}>
                                    <span style={{ fontSize: 17, fontWeight: 900, color: meta.color }}>{score}</span>
                                    <span style={{ fontSize: 9, color: '#9ca3af' }}>/ 100</span>
                                </div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                                    <span style={{ fontSize: 18 }}>{meta.icon}</span>
                                    <span style={{ fontSize: 16, fontWeight: 700, color: '#111827' }}>
                                        {meta.label}
                                    </span>
                                </div>
                                <div style={{
                                    display: 'inline-flex', alignItems: 'center', gap: 5,
                                    padding: '3px 10px', borderRadius: 99,
                                    background: 'white',
                                    border: `1px solid ${risk.border}`,
                                }}>
                                    <span style={{
                                        width: 7, height: 7, borderRadius: '50%',
                                        background: risk.dot, flexShrink: 0,
                                    }} />
                                    <span style={{ fontSize: 12, fontWeight: 700, color: risk.text }}>
                                        {risk.label}
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Disclaimer */}
            <p style={{
                fontSize: 11, color: '#9ca3af', textAlign: 'center',
                padding: '0 12px', marginBottom: 20, lineHeight: 1.5,
            }}>
                These results are for screening purposes only and are not a clinical diagnosis.
                Please consult a mental health professional for proper evaluation.
            </p>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10 }}>
                <button
                    onClick={onRetake}
                    style={{
                        flex: 1,
                        padding: '13px',
                        borderRadius: 14,
                        border: '2px solid #e5e7eb',
                        background: '#fff',
                        color: '#374151',
                        fontWeight: 700,
                        fontSize: 14,
                        cursor: 'pointer',
                    }}
                >
                    Retake
                </button>
                <button
                    onClick={onClose}
                    style={{
                        flex: 2,
                        padding: '13px',
                        borderRadius: 14,
                        border: 'none',
                        background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: 14,
                        cursor: 'pointer',
                        boxShadow: '0 4px 16px rgba(124,58,237,.35)',
                    }}
                >
                    View My Assessments
                </button>
            </div>
        </div>
    );
}

// ─── Helper: is a single question answered? ───────────────────────────────────
// Extracted as a pure function so it can be reused for per-card highlight and
// the overall allAnswered gate without duplicating logic.
function isQuestionAnswered(cfg, ans) {
    if (!cfg) return ans !== undefined && ans !== '';
    if (cfg.type === 'scale') return true; // always has a defaultValue pre-filled
    if (cfg.type === 'number') {
        if (ans === undefined || ans === '') return false;
        const n = Number(ans);
        return !isNaN(n) && n >= cfg.min && n <= cfg.max;
    }
    return ans !== undefined && ans !== '';
}

// ─── Main Modal Component ─────────────────────────────────────────────────────
export default function MLAssessmentModal({ isOpen, onClose, onResultsReady }) {
    const { user } = useAuth();

    const [questions, setQuestions] = useState([]);
    const [loadingQs, setLoadingQs] = useState(false);
    const [loadError, setLoadError] = useState(null);

    // CHANGED: 'step' state removed; all questions shown at once.
    const [answers, setAnswers] = useState({});   // { [question_id]: answer_string }

    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const [results, setResults] = useState(null);

    // ── Fetch questions when modal opens (UNCHANGED logic) ────────────────────
    useEffect(() => {
        if (!isOpen) return;
        setAnswers({});
        setResults(null);
        setSubmitError(null);
        setLoadError(null);
        setLoadingQs(true);

        fetch('http://127.0.0.1:8000/question/by-assessment/1')
            .then((r) => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then((data) => setQuestions(data))
            .catch((e) => setLoadError(e.message))
            .finally(() => setLoadingQs(false));
    }, [isOpen]);

    // ── CHANGED: Pre-fill 'scale' defaults for all questions at load time ─────
    // Previously this ran on each step change; now it runs once when the full
    // question list arrives, setting defaultValue for every scale question.
    useEffect(() => {
        if (questions.length === 0) return;
        const defaults = {};
        questions.forEach((q) => {
            const cfg = QUESTION_CONFIG[q.question_name];
            if (cfg?.type === 'scale' && answers[q.id] === undefined) {
                defaults[q.id] = String(cfg.defaultValue);
            }
        });
        if (Object.keys(defaults).length > 0) {
            setAnswers((prev) => ({ ...prev, ...defaults }));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [questions]);

    // ── CHANGED: allAnswered — replaces the per-step isAnswered callback ──────
    // Gates the Submit button. Scale questions count as answered immediately
    // because their defaultValue is pre-filled above.
    const allAnswered = questions.length > 0 && questions.every((q) => {
        const cfg = QUESTION_CONFIG[q.question_name];
        return isQuestionAnswered(cfg, answers[q.id]);
    });

    // ── CHANGED: answeredCount — drives the progress bar ─────────────────────
    const answeredCount = questions.filter((q) =>
        isQuestionAnswered(QUESTION_CONFIG[q.question_name], answers[q.id])
    ).length;

    const progress = questions.length > 0 ? (answeredCount / questions.length) * 100 : 0;

    // ── Submit (UNCHANGED logic) ──────────────────────────────────────────────
    const handleSubmit = async () => {
        setSubmitting(true);
        setSubmitError(null);

        const userId = user?.id;
        if (!userId) {
            setSubmitError('Cannot submit: user not logged in.');
            setSubmitting(false);
            return;
        }

        const payload = {
            user_id: userId,
            answers: questions.map((q) => ({
                question_id: q.id,
                answer: String(answers[q.id] ?? ''),
            })),
        };

        try {
            console.log('Submitting payload:', payload);

            const res = await fetch('http://127.0.0.1:8000/answers/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', accept: 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                const txt = await res.text();
                throw new Error(`Server error ${res.status}: ${txt}`);
            }
            const data = await res.json();
            const mlResults = data.results || data;
            setResults(mlResults);
            if (onResultsReady) onResultsReady(mlResults);
        } catch (e) {
            setSubmitError(e.message);
        } finally {
            setSubmitting(false);
        }
    };

    // ── CHANGED: handleRetake also re-seeds scale defaults ───────────────────
    const handleRetake = () => {
        const defaults = {};
        questions.forEach((q) => {
            const cfg = QUESTION_CONFIG[q.question_name];
            if (cfg?.type === 'scale') defaults[q.id] = String(cfg.defaultValue);
        });
        setAnswers(defaults);
        setResults(null);
        setSubmitError(null);
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop (UNCHANGED) */}
            <div
                style={{
                    position: 'fixed', inset: 0, zIndex: 1000,
                    background: 'rgba(0,0,0,0.55)',
                    backdropFilter: 'blur(6px)',
                    WebkitBackdropFilter: 'blur(6px)',
                }}
            />

            {/* Modal container (UNCHANGED) */}
            <div style={{
                position: 'fixed', inset: 0, zIndex: 1001,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: '16px',
                pointerEvents: 'none',
            }}>
                <div style={{
                    width: '100%',
                    maxWidth: 520,
                    maxHeight: '90vh',
                    overflowY: 'auto',
                    background: '#fff',
                    borderRadius: 28,
                    boxShadow: '0 32px 96px rgba(0,0,0,.25)',
                    pointerEvents: 'all',
                    position: 'relative',
                    padding: '28px 28px 24px',
                }}>

                    {/* Close button (UNCHANGED) */}
                    <button
                        onClick={onClose}
                        style={{
                            position: 'absolute', top: 20, right: 20,
                            width: 34, height: 34, borderRadius: '50%',
                            border: 'none', background: '#f3f4f6', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}
                    >
                        <XMarkIcon style={{ width: 18, height: 18, color: '#6b7280' }} />
                    </button>

                    {/* Loading state (UNCHANGED) */}
                    {loadingQs && (
                        <div style={{ textAlign: 'center', padding: '48px 0' }}>
                            <div style={{
                                width: 48, height: 48,
                                border: '4px solid #ede9fe',
                                borderTopColor: '#7c3aed',
                                borderRadius: '50%',
                                animation: 'spin 0.9s linear infinite',
                                margin: '0 auto 16px',
                            }} />
                            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                            <p style={{ color: '#6b7280', margin: 0 }}>Loading questions…</p>
                        </div>
                    )}

                    {/* Load error (UNCHANGED) */}
                    {!loadingQs && loadError && (
                        <div style={{ textAlign: 'center', padding: '40px 0' }}>
                            <ExclamationTriangleIcon style={{ width: 40, height: 40, color: '#ef4444', margin: '0 auto 12px' }} />
                            <p style={{ color: '#374151', fontWeight: 600, margin: '0 0 4px' }}>Failed to load questions</p>
                            <p style={{ color: '#9ca3af', fontSize: 13 }}>{loadError}</p>
                            <button
                                onClick={() => {
                                    setLoadError(null);
                                    setLoadingQs(true);
                                    fetch('http://127.0.0.1:8000/question/by-assessment/1')
                                        .then(r => r.json())
                                        .then(setQuestions)
                                        .catch(e => setLoadError(e.message))
                                        .finally(() => setLoadingQs(false));
                                }}
                                style={{
                                    marginTop: 16, padding: '10px 24px', borderRadius: 12,
                                    border: 'none', background: '#7c3aed', color: '#fff',
                                    fontWeight: 700, cursor: 'pointer',
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {/* Results screen (UNCHANGED) */}
                    {!loadingQs && !loadError && results && (
                        <ResultsScreen results={results} onClose={onClose} onRetake={handleRetake} />
                    )}

                    {/* ── CHANGED: Single-page questionnaire (replaces step wizard) ── */}
                    {!loadingQs && !loadError && !results && questions.length > 0 && (
                        <>
                            {/* Header brand bar — layout unchanged; subtitle updated */}
                            <div style={{ marginBottom: 22 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                                    <div style={{
                                        width: 36, height: 36, borderRadius: 10,
                                        background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    }}>
                                        <SparklesIcon style={{ width: 18, height: 18, color: '#fff' }} />
                                    </div>
                                    <div>
                                        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
                                            Mental Health Assessment
                                        </h2>
                                        {/* CHANGED: shows answered count instead of current step */}
                                        <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
                                            {answeredCount} of {questions.length} questions answered
                                        </p>
                                    </div>
                                </div>

                                {/* Progress bar — identical styles; now tracks answered count */}
                                <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${progress}%`,
                                        background: 'linear-gradient(90deg,#7c3aed,#a78bfa)',
                                        borderRadius: 99,
                                        transition: 'width .35s ease',
                                    }} />
                                </div>
                            </div>

                            {/*
                             * CHANGED: All questions rendered in a vertical stack.
                             * Each question lives inside a Google Forms–style card:
                             *   • White background with a subtle border
                             *   • Border shifts to purple (#ddd6fe) when answered
                             *   • A "Q{n}" chip precedes the question label
                             * The dot navigator and Back / Next buttons are removed.
                             */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
                                {questions.map((q, index) => {
                                    const cfg = QUESTION_CONFIG[q.question_name];
                                    const ans = answers[q.id];
                                    const answered = isQuestionAnswered(cfg, ans);

                                    return (
                                        <div
                                            key={q.id}
                                            style={{
                                                padding: '20px',
                                                borderRadius: 16,
                                                // Subtle purple tint on answered cards — signals completion
                                                border: `1.5px solid ${answered ? '#ddd6fe' : '#e5e7eb'}`,
                                                background: '#fff',
                                                boxShadow: answered
                                                    ? '0 2px 8px rgba(124,58,237,.06)'
                                                    : '0 1px 4px rgba(0,0,0,.04)',
                                                transition: 'border-color .2s ease, box-shadow .2s ease',
                                            }}
                                        >
                                            {/* Question label with "Q{n}" chip */}
                                            <p style={{
                                                margin: '0 0 16px',
                                                fontSize: 15,
                                                fontWeight: 700,
                                                color: '#1f2937',
                                                lineHeight: 1.4,
                                                display: 'flex',
                                                gap: 8,
                                                alignItems: 'flex-start',
                                            }}>
                                                {/* Numbered chip — matches brand colour */}
                                                <span style={{
                                                    flexShrink: 0,
                                                    fontSize: 11,
                                                    fontWeight: 700,
                                                    color: '#7c3aed',
                                                    background: '#ede9fe',
                                                    borderRadius: 6,
                                                    padding: '2px 7px',
                                                    marginTop: 1,
                                                    lineHeight: 1.6,
                                                }}>
                                                    Q{index + 1}
                                                </span>
                                                {cfg?.label || q.question_name.replace(/_/g, ' ')}
                                            </p>

                                            {/* Input — each question manages its own answer */}
                                            <QuestionInput
                                                config={cfg}
                                                value={ans}
                                                onChange={(val) =>
                                                    setAnswers((prev) => ({ ...prev, [q.id]: val }))
                                                }
                                            />
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Submit error (UNCHANGED styles) */}
                            {submitError && (
                                <div style={{
                                    padding: '10px 14px', borderRadius: 12,
                                    background: '#fef2f2', border: '1px solid #fecaca',
                                    color: '#b91c1c', fontSize: 13, marginBottom: 14,
                                }}>
                                    ⚠️ {submitError}
                                </div>
                            )}

                            {/*
                             * CHANGED: Single Submit button at the bottom of the form.
                             * Replaces the Back / Next / Submit navigation row.
                             * Button styles (gradient, border-radius, shadow, disabled state)
                             * are pixel-identical to the original Submit button.
                             */}
                            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                <button
                                    onClick={handleSubmit}
                                    disabled={!allAnswered || submitting}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 7,
                                        padding: '12px 28px',
                                        borderRadius: 14,
                                        border: 'none',
                                        background: (!allAnswered || submitting)
                                            ? '#e5e7eb'
                                            : 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                                        color: (!allAnswered || submitting) ? '#9ca3af' : '#fff',
                                        fontWeight: 700,
                                        fontSize: 15,
                                        cursor: (!allAnswered || submitting) ? 'not-allowed' : 'pointer',
                                        boxShadow: allAnswered && !submitting
                                            ? '0 4px 16px rgba(124,58,237,.35)'
                                            : 'none',
                                        transition: 'all .18s',
                                    }}
                                >
                                    {submitting ? (
                                        <>
                                            <span style={{
                                                width: 16, height: 16,
                                                border: '2px solid rgba(255,255,255,.4)',
                                                borderTopColor: '#fff',
                                                borderRadius: '50%',
                                                animation: 'spin 0.9s linear infinite',
                                                display: 'inline-block',
                                            }} />
                                            Analysing…
                                        </>
                                    ) : (
                                        <>
                                            <CheckIcon style={{ width: 17, height: 17 }} />
                                            Submit &amp; Get Results
                                        </>
                                    )}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </>
    );
}
