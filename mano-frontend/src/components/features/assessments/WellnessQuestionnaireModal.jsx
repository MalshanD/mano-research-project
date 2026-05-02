// import { useState, useCallback, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
// import { useAuth } from '../../../contexts/AuthContext';
// import { getActivityCategories } from '../../../api/client';
// import {
//     XMarkIcon,
//     ArrowLeftIcon,
//     ArrowRightIcon,
//     CheckIcon,
//     SparklesIcon,
//     ExclamationTriangleIcon,
// } from '@heroicons/react/24/outline';

// // ─── 20 Wellbeing Questions ──────────────────────────────────────────────────
// const SECTIONS = [
//     {
//         id: 'body',
//         label: 'Body',
//         emoji: '🧘',
//         color: '#7c3aed',
//         lightColor: '#ede9fe',
//         title: 'Physical Wellbeing',
//         subtitle: 'Questions about physical symptoms related to stress or mental health',
//         questions: [
//             'How often do you feel tired or low on energy during the day?',
//             'How often do you have difficulty sleeping or poor sleep quality?',
//             'Do you experience frequent headaches, stomach pain, or body tension?',
//             'How often do you feel physically restless or unable to relax?',
//             'How often do you feel changes in appetite (eating too much or too little)?',
//         ],
//     },
//     {
//         id: 'behavior',
//         label: 'Behavior',
//         emoji: '⚙️',
//         color: '#0ea5e9',
//         lightColor: '#e0f2fe',
//         title: 'Behavioral Patterns',
//         subtitle: 'Questions about behavior changes due to stress or emotional issues',
//         questions: [
//             'How often do you procrastinate or avoid important tasks?',
//             'How often do you lose focus while studying or working?',
//             'How often do you spend excessive time on social media or distractions?',
//             'How often do you skip responsibilities or commitments?',
//             'How often do you feel unmotivated to complete daily activities?',
//         ],
//     },
//     {
//         id: 'emotional',
//         label: 'Emotional',
//         emoji: '💛',
//         color: '#f59e0b',
//         lightColor: '#fef3c7',
//         title: 'Emotional Wellbeing',
//         subtitle: 'Questions that measure your emotional state',
//         questions: [
//             'How often do you feel overwhelmed or stressed?',
//             'How often do you feel sad or down without a clear reason?',
//             'How often do you feel irritable or easily frustrated?',
//             'How often do you feel anxious or worried about the future?',
//             'How often do you feel hopeless or discouraged?',
//         ],
//     },
//     {
//         id: 'social',
//         label: 'Social',
//         emoji: '👥',
//         color: '#10b981',
//         lightColor: '#d1fae5',
//         title: 'Social Connection',
//         subtitle: 'Questions that measure social connections and relationships',
//         questions: [
//             'How often do you feel lonely or isolated?',
//             'How often do you avoid meeting friends or family?',
//             'How often do you feel unsupported by people around you?',
//             'How comfortable are you talking about your problems with others?',
//             'How often do you feel disconnected from your social circle?',
//         ],
//     },
// ];

// const ANSWER_OPTIONS = [
//     { label: 'Never',     value: 1, color: '#10b981', bg: '#d1fae5' },
//     { label: 'Rarely',    value: 2, color: '#84cc16', bg: '#ecfccb' },
//     { label: 'Sometimes', value: 3, color: '#f59e0b', bg: '#fef3c7' },
//     { label: 'Often',     value: 4, color: '#f97316', bg: '#ffedd5' },
//     { label: 'Always',    value: 5, color: '#ef4444', bg: '#fee2e2' },
// ];

// // All 20 flat questions with their section index
// const ALL_QUESTIONS = SECTIONS.flatMap((sec, si) =>
//     sec.questions.map((q, qi) => ({ id: si * 5 + qi, sectionIndex: si, text: q }))
// );

// // Compute level 1–5 from 20 answers
// function computeLevel(answers) {
//     const values = Object.values(answers);
//     if (!values.length) return 1;
//     const avg = values.reduce((s, v) => s + Number(v), 0) / values.length;
//     return Math.max(1, Math.min(5, Math.round(avg)));
// }

// // ─── Type → endpoint segment mapping ────────────────────────────────────────
// const TYPE_MAP = {
//     PHQ9:  'depression',
//     GAD7:  'anxiety',
//     PSS10: 'stress',
// };

// const TYPE_LABELS = {
//     PHQ9:  'Depression (PHQ-9)',
//     GAD7:  'Anxiety (GAD-7)',
//     PSS10: 'Stress (PSS-10)',
// };

// // ─── Available categories for exclude filter ─────────────────────────────────
// // Loaded dynamically from GET /activity/categories
// const CATEGORY_META = {
//     anxiety_relief:    { emoji: '😮‍💨', label: 'Anxiety Relief'    },
//     depression_relief: { emoji: '💛',       label: 'Depression Relief' },
//     emotional:         { emoji: '❤️',       label: 'Emotional'         },
//     mindfulness:       { emoji: '🌸',       label: 'Mindfulness'       },
//     physical:          { emoji: '🏃',       label: 'Physical'          },
//     professional:      { emoji: '💼',       label: 'Professional'      },
//     routine:           { emoji: '📅',       label: 'Routine'           },
//     sleep:             { emoji: '😴',       label: 'Sleep'             },
//     social:            { emoji: '👥',       label: 'Social'            },
//     stress_relief:     { emoji: '🧘',       label: 'Stress Relief'     },
// };

// const DEFAULT_PREFS = {
//     num_recommendations: 3,
//     difficulty_preference: 'easy',
//     max_duration_minutes: 0,
//     exclude_categories: [],
// };

// // ─── Main Component ──────────────────────────────────────────────────────────
// export default function WellnessQuestionnaireModal({ isOpen, onClose, assessmentType }) {
//     const navigate = useNavigate();
//     const { user } = useAuth();
//     const [section, setSection] = useState(0);
//     const [questionIdx, setQuestionIdx] = useState(0);
//     const [answers, setAnswers] = useState({});
//     const [showPrefs, setShowPrefs] = useState(false);
//     const [prefs, setPrefs] = useState(DEFAULT_PREFS);
//     const [submitting, setSubmitting] = useState(false);
//     const [submitError, setSubmitError] = useState(null);
//     const [availableCategories, setAvailableCategories] = useState([]);
//     const [categoriesLoading, setCategoriesLoading] = useState(false);

//     // Fetch real categories from API when prefs step opens
//     useEffect(() => {
//         if (!showPrefs || availableCategories.length > 0) return;
//         setCategoriesLoading(true);
//         getActivityCategories().then(({ data }) => {
//             const cats = (data?.categories || []).map((id) => ({
//                 id,
//                 emoji: CATEGORY_META[id]?.emoji || '📌',
//                 label: CATEGORY_META[id]?.label || id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
//             }));
//             setAvailableCategories(cats);
//             setCategoriesLoading(false);
//         });
//     }, [showPrefs, availableCategories.length]);

//     const currentSection = SECTIONS[section];
//     const globalIdx = section * 5 + questionIdx;
//     const totalQuestions = 20;
//     const progress = ((globalIdx + 1) / totalQuestions) * 100;

//     const currentAnswer = answers[globalIdx];
//     const isLastQuestion = section === 3 && questionIdx === 4;

//     const handleAnswer = useCallback((val) => {
//         setAnswers((prev) => ({ ...prev, [globalIdx]: val }));
//     }, [globalIdx]);

//     const handleNext = () => {
//         if (isLastQuestion) {
//             setShowPrefs(true);
//         } else if (questionIdx < 4) {
//             setQuestionIdx((q) => q + 1);
//         } else if (section < 3) {
//             setSection((s) => s + 1);
//             setQuestionIdx(0);
//         }
//     };

//     const handlePrev = () => {
//         if (showPrefs) {
//             setShowPrefs(false);
//         } else if (questionIdx > 0) {
//             setQuestionIdx((q) => q - 1);
//         } else if (section > 0) {
//             setSection((s) => s - 1);
//             setQuestionIdx(4);
//         }
//     };

//     const handleReset = () => {
//         setSection(0);
//         setQuestionIdx(0);
//         setAnswers({});
//         setShowPrefs(false);
//         setPrefs(DEFAULT_PREFS);
//         setSubmitError(null);
//     };

//     const toggleCategory = (catId) => {
//         setPrefs((p) => ({
//             ...p,
//             exclude_categories: p.exclude_categories.includes(catId)
//                 ? p.exclude_categories.filter((c) => c !== catId)
//                 : [...p.exclude_categories, catId],
//         }));
//     };

//     const handleSubmit = async () => {
//         const userId = user?.id;
//         if (!userId) {
//             setSubmitError('Cannot submit: user not logged in.');
//             return;
//         }

//         const segment = TYPE_MAP[assessmentType] || 'stress';
//         const level = computeLevel(answers);
//         const answersArray = ALL_QUESTIONS.map((q) => Number(answers[q.id] ?? 3));

//         const payload = {
//             answers: answersArray,
//             num_recommendations: prefs.num_recommendations,
//             difficulty_preference: prefs.difficulty_preference,
//             max_duration_minutes: prefs.max_duration_minutes,
//             exclude_categories: prefs.exclude_categories,
//         };

//         setSubmitting(true);
//         setSubmitError(null);

//         try {
//             const res = await fetch(
//                 `http://127.0.0.1:8000/activity/${segment}/${userId}/${level}`,
//                 {
//                     method: 'POST',
//                     headers: { 'Content-Type': 'application/json', accept: 'application/json' },
//                     body: JSON.stringify(payload),
//                 }
//             );
//             if (!res.ok) {
//                 const txt = await res.text();
//                 throw new Error(`Server error ${res.status}: ${txt}`);
//             }
//             const data = await res.json();
//             onClose();
//             handleReset();
//             navigate('/activities', {
//                 state: {
//                     recommendations: data.recommendations || [],
//                     conditionsDetected: data.conditions_detected || [],
//                     assessmentType,
//                     assessmentLabel: TYPE_LABELS[assessmentType] || assessmentType,
//                     generatedAt: data.generated_at,
//                 },
//             });
//         } catch (e) {
//             setSubmitError(e.message);
//         } finally {
//             setSubmitting(false);
//         }
//     };

//     if (!isOpen) return null;

//     const sec = currentSection;

//     return (
//         <>
//             {/* Backdrop */}
//             <div style={{
//                 position: 'fixed', inset: 0, zIndex: 1200,
//                 background: 'rgba(0,0,0,0.55)',
//                 backdropFilter: 'blur(6px)',
//                 WebkitBackdropFilter: 'blur(6px)',
//             }} />

//             {/* Modal */}
//             <div style={{
//                 position: 'fixed', inset: 0, zIndex: 1201,
//                 display: 'flex', alignItems: 'center', justifyContent: 'center',
//                 padding: 16,
//                 pointerEvents: 'none',
//             }}>
//                 <div style={{
//                     width: '100%',
//                     maxWidth: 540,
//                     maxHeight: '92vh',
//                     overflowY: 'auto',
//                     background: '#fff',
//                     borderRadius: 28,
//                     boxShadow: '0 32px 96px rgba(0,0,0,.25)',
//                     pointerEvents: 'all',
//                     position: 'relative',
//                     padding: '28px 28px 24px',
//                 }}>

//                     {/* Close */}
//                     <button
//                         onClick={() => { onClose(); handleReset(); }}
//                         style={{
//                             position: 'absolute', top: 20, right: 20,
//                             width: 34, height: 34, borderRadius: '50%',
//                             border: 'none', background: '#f3f4f6', cursor: 'pointer',
//                             display: 'flex', alignItems: 'center', justifyContent: 'center',
//                         }}
//                     >
//                         <XMarkIcon style={{ width: 18, height: 18, color: '#6b7280' }} />
//                     </button>

//                     {/* ── PREFERENCES STEP ── */}
//                     {showPrefs ? (
//                         <>
//                             {/* Prefs Header */}
//                             <div style={{ marginBottom: 22 }}>
//                                 <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
//                                     <div style={{
//                                         width: 38, height: 38, borderRadius: 12,
//                                         background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
//                                         display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
//                                     }}>⚙️</div>
//                                     <div>
//                                         <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
//                                             Personalise Your Activities
//                                         </h2>
//                                         <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
//                                             Almost done! Customise your recommendations.
//                                         </p>
//                                     </div>
//                                 </div>
//                                 {/* Full bar */}
//                                 <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
//                                     <div style={{ height: '100%', width: '100%', background: 'linear-gradient(90deg,#7c3aed,#a78bfa)', borderRadius: 99 }} />
//                                 </div>
//                             </div>

//                             {/* ── How many recommendations ── */}
//                             <div style={{ marginBottom: 22 }}>
//                                 <p style={{ margin: '0 0 10px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
//                                     How many activity suggestions do you want?
//                                 </p>
//                                 <div style={{ display: 'flex', gap: 8 }}>
//                                     {[1, 2, 3, 4, 5].map((n) => (
//                                         <button
//                                             key={n}
//                                             onClick={() => setPrefs((p) => ({ ...p, num_recommendations: n }))}
//                                             style={{
//                                                 flex: 1, padding: '10px 0', borderRadius: 12,
//                                                 border: prefs.num_recommendations === n ? '2px solid #7c3aed' : '2px solid #e5e7eb',
//                                                 background: prefs.num_recommendations === n ? '#ede9fe' : '#fafafa',
//                                                 color: prefs.num_recommendations === n ? '#7c3aed' : '#6b7280',
//                                                 fontSize: 16, fontWeight: 700, cursor: 'pointer',
//                                                 transition: 'all .15s',
//                                             }}
//                                         >{n}</button>
//                                     ))}
//                                 </div>
//                             </div>

//                             {/* ── Difficulty preference ── */}
//                             <div style={{ marginBottom: 22 }}>
//                                 <p style={{ margin: '0 0 10px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
//                                     Preferred activity difficulty
//                                 </p>
//                                 <div style={{ display: 'flex', gap: 8 }}>
//                                     {[
//                                         { value: 'easy',        label: 'Easy',        emoji: '🌱', color: '#10b981', bg: '#d1fae5' },
//                                         { value: 'moderate',    label: 'Moderate',    emoji: '🔥', color: '#f59e0b', bg: '#fef3c7' },
//                                         { value: 'challenging', label: 'Challenging', emoji: '💪', color: '#ef4444', bg: '#fee2e2' },
//                                     ].map((d) => {
//                                         const sel = prefs.difficulty_preference === d.value;
//                                         return (
//                                             <button
//                                                 key={d.value}
//                                                 onClick={() => setPrefs((p) => ({ ...p, difficulty_preference: d.value }))}
//                                                 style={{
//                                                     flex: 1, padding: '12px 6px', borderRadius: 14,
//                                                     border: sel ? `2px solid ${d.color}` : '2px solid #e5e7eb',
//                                                     background: sel ? d.bg : '#fafafa',
//                                                     cursor: 'pointer', textAlign: 'center',
//                                                     transition: 'all .15s',
//                                                 }}
//                                             >
//                                                 <div style={{ fontSize: 20, marginBottom: 4 }}>{d.emoji}</div>
//                                                 <div style={{ fontSize: 12, fontWeight: 700, color: sel ? d.color : '#6b7280' }}>{d.label}</div>
//                                             </button>
//                                         );
//                                     })}
//                                 </div>
//                             </div>

//                             {/* ── Max duration ── */}
//                             <div style={{ marginBottom: 22 }}>
//                                 <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
//                                     Maximum activity duration
//                                 </p>
//                                 <p style={{ margin: '0 0 10px', fontSize: 12, color: '#9ca3af' }}>
//                                     Set to 0 for no time limit
//                                 </p>
//                                 <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
//                                     <input
//                                         type="range"
//                                         min={0} max={60} step={5}
//                                         value={prefs.max_duration_minutes}
//                                         onChange={(e) => setPrefs((p) => ({ ...p, max_duration_minutes: Number(e.target.value) }))}
//                                         style={{ flex: 1, accentColor: '#7c3aed' }}
//                                     />
//                                     <span style={{
//                                         minWidth: 64, textAlign: 'center',
//                                         padding: '6px 10px', borderRadius: 10,
//                                         background: '#ede9fe', color: '#7c3aed',
//                                         fontSize: 13, fontWeight: 700,
//                                     }}>
//                                         {prefs.max_duration_minutes === 0 ? 'No limit' : `${prefs.max_duration_minutes} min`}
//                                     </span>
//                                 </div>
//                             </div>

//                             {/* ── Exclude categories ── */}
//                             <div style={{ marginBottom: 24 }}>
//                                 <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
//                                     Exclude activity categories
//                                 </p>
//                                 <p style={{ margin: '0 0 10px', fontSize: 12, color: '#9ca3af' }}>
//                                     Tap to exclude categories you'd prefer to avoid
//                                 </p>
//                                 {categoriesLoading ? (
//                                     <p style={{ fontSize: 12, color: '#9ca3af' }}>Loading categories…</p>
//                                 ) : (
//                                 <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
//                                     {availableCategories.map((cat) => {
//                                         const excluded = prefs.exclude_categories.includes(cat.id);
//                                         return (
//                                             <button
//                                                 key={cat.id}
//                                                 onClick={() => toggleCategory(cat.id)}
//                                                 style={{
//                                                     display: 'flex', alignItems: 'center', gap: 5,
//                                                     padding: '7px 13px', borderRadius: 99,
//                                                     border: excluded ? '2px solid #ef4444' : '2px solid #e5e7eb',
//                                                     background: excluded ? '#fee2e2' : '#f9fafb',
//                                                     color: excluded ? '#ef4444' : '#4b5563',
//                                                     fontSize: 12, fontWeight: 600, cursor: 'pointer',
//                                                     textDecoration: excluded ? 'line-through' : 'none',
//                                                     transition: 'all .15s',
//                                                 }}
//                                             >
//                                                 <span>{cat.emoji}</span> {cat.label}
//                                             </button>
//                                         );
//                                     })}
//                                 </div>
//                                 )}
//                             </div>

//                             {/* Error */}
//                             {submitError && (
//                                 <div style={{
//                                     display: 'flex', alignItems: 'flex-start', gap: 8,
//                                     padding: '12px 14px', borderRadius: 12, marginBottom: 16,
//                                     background: '#fef2f2', border: '1px solid #fecaca',
//                                 }}>
//                                     <ExclamationTriangleIcon style={{ width: 16, height: 16, color: '#ef4444', flexShrink: 0, marginTop: 1 }} />
//                                     <p style={{ margin: 0, fontSize: 13, color: '#ef4444' }}>{submitError}</p>
//                                 </div>
//                             )}

//                             {/* Prefs Navigation */}
//                             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
//                                 <button
//                                     onClick={handlePrev}
//                                     style={{
//                                         display: 'flex', alignItems: 'center', gap: 6,
//                                         padding: '11px 20px', borderRadius: 14,
//                                         border: '2px solid #e5e7eb', background: '#fff',
//                                         fontSize: 14, fontWeight: 600, color: '#374151', cursor: 'pointer',
//                                     }}
//                                 >
//                                     <ArrowLeftIcon style={{ width: 16, height: 16 }} />
//                                     Back
//                                 </button>
//                                 <button
//                                     onClick={handleSubmit}
//                                     disabled={submitting}
//                                     style={{
//                                         display: 'flex', alignItems: 'center', gap: 8,
//                                         padding: '12px 28px', borderRadius: 14, border: 'none',
//                                         background: submitting ? '#e5e7eb' : 'linear-gradient(135deg,#7c3aed,#6d28d9)',
//                                         color: submitting ? '#9ca3af' : '#fff',
//                                         fontSize: 15, fontWeight: 700,
//                                         cursor: submitting ? 'not-allowed' : 'pointer',
//                                         boxShadow: !submitting ? '0 4px 16px rgba(124,58,237,.35)' : 'none',
//                                         transition: 'all .18s',
//                                     }}
//                                 >
//                                     {submitting ? (
//                                         <>
//                                             <span style={{
//                                                 width: 16, height: 16,
//                                                 border: '2px solid rgba(255,255,255,.4)',
//                                                 borderTopColor: '#fff',
//                                                 borderRadius: '50%',
//                                                 animation: 'wq-spin 0.9s linear infinite',
//                                                 display: 'inline-block',
//                                             }} />
//                                             Getting Activities…
//                                         </>
//                                     ) : (
//                                         <>
//                                             <SparklesIcon style={{ width: 17, height: 17 }} />
//                                             Get My Activities
//                                         </>
//                                     )}
//                                 </button>
//                             </div>
//                         </>
//                     ) : (
//                         <>
//                             {/* ── QUESTION STEP ── */}
//                             {/* Header */}
//                     <div style={{ marginBottom: 20 }}>
//                         <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
//                             <div style={{
//                                 width: 38, height: 38, borderRadius: 12,
//                                 background: `linear-gradient(135deg, ${sec.color}, ${sec.color}cc)`,
//                                 display: 'flex', alignItems: 'center', justifyContent: 'center',
//                                 fontSize: 18,
//                             }}>
//                                 {sec.emoji}
//                             </div>
//                             <div>
//                                 <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
//                                     Wellness Check — {TYPE_LABELS[assessmentType] || assessmentType}
//                                 </h2>
//                                 <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
//                                     Question {globalIdx + 1} of {totalQuestions}
//                                 </p>
//                             </div>
//                         </div>

//                         {/* Progress bar */}
//                         <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden', marginBottom: 14 }}>
//                             <div style={{
//                                 height: '100%',
//                                 width: `${progress}%`,
//                                 background: `linear-gradient(90deg, ${sec.color}, ${sec.color}bb)`,
//                                 borderRadius: 99,
//                                 transition: 'width .35s ease',
//                             }} />
//                         </div>

//                         {/* Section tabs */}
//                         <div style={{ display: 'flex', gap: 6 }}>
//                             {SECTIONS.map((s, i) => (
//                                 <div
//                                     key={s.id}
//                                     style={{
//                                         flex: 1,
//                                         height: 4,
//                                         borderRadius: 99,
//                                         background: i < section
//                                             ? s.color
//                                             : i === section
//                                                 ? s.color + '88'
//                                                 : '#e5e7eb',
//                                         transition: 'background .3s',
//                                     }}
//                                 />
//                             ))}
//                         </div>

//                         {/* Section label */}
//                         <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
//                             <span style={{
//                                 display: 'inline-flex', alignItems: 'center', gap: 4,
//                                 padding: '3px 10px', borderRadius: 99,
//                                 background: sec.lightColor, color: sec.color,
//                                 fontSize: 11, fontWeight: 700,
//                             }}>
//                                 {sec.emoji} {sec.title}
//                             </span>
//                             <span style={{ fontSize: 11, color: '#9ca3af' }}>{sec.subtitle}</span>
//                         </div>
//                     </div>

//                     {/* Question */}
//                     <div style={{ marginBottom: 24 }}>
//                         <p style={{ margin: '0 0 20px', fontSize: 17, fontWeight: 700, color: '#1f2937', lineHeight: 1.45 }}>
//                             {sec.questions[questionIdx]}
//                         </p>

//                         {/* Answer options */}
//                         <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
//                             {ANSWER_OPTIONS.map((opt) => {
//                                 const selected = currentAnswer === opt.value;
//                                 return (
//                                     <button
//                                         key={opt.value}
//                                         onClick={() => handleAnswer(opt.value)}
//                                         style={{
//                                             display: 'flex', alignItems: 'center', gap: 12,
//                                             padding: '12px 16px',
//                                             borderRadius: 14,
//                                             border: selected ? `2px solid ${opt.color}` : '2px solid #e5e7eb',
//                                             background: selected ? opt.bg : '#fafafa',
//                                             cursor: 'pointer',
//                                             textAlign: 'left',
//                                             transition: 'all .15s',
//                                         }}
//                                     >
//                                         <div style={{
//                                             width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
//                                             border: selected ? `2.5px solid ${opt.color}` : '2px solid #d1d5db',
//                                             background: selected ? opt.color : '#fff',
//                                             display: 'flex', alignItems: 'center', justifyContent: 'center',
//                                         }}>
//                                             {selected && <CheckIcon style={{ width: 14, height: 14, color: '#fff' }} />}
//                                         </div>
//                                         <div style={{ flex: 1 }}>
//                                             <span style={{
//                                                 fontSize: 14, fontWeight: 600,
//                                                 color: selected ? opt.color : '#374151',
//                                             }}>
//                                                 {opt.label}
//                                             </span>
//                                         </div>
//                                         <span style={{
//                                             fontSize: 11, fontWeight: 700,
//                                             color: selected ? opt.color : '#d1d5db',
//                                             background: selected ? opt.bg : '#f3f4f6',
//                                             padding: '2px 7px', borderRadius: 99,
//                                         }}>
//                                             {opt.value}
//                                         </span>
//                                     </button>
//                                 );
//                             })}
//                         </div>
//                     </div>

//                     {/* Error */}
//                     {submitError && (
//                         <div style={{
//                             display: 'flex', alignItems: 'flex-start', gap: 8,
//                             padding: '12px 14px', borderRadius: 12, marginBottom: 16,
//                             background: '#fef2f2', border: '1px solid #fecaca',
//                         }}>
//                             <ExclamationTriangleIcon style={{ width: 16, height: 16, color: '#ef4444', flexShrink: 0, marginTop: 1 }} />
//                             <p style={{ margin: 0, fontSize: 13, color: '#ef4444' }}>{submitError}</p>
//                         </div>
//                     )}

//                     {/* Navigation */}
//                     <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
//                         <button
//                             onClick={handlePrev}
//                             disabled={section === 0 && questionIdx === 0}
//                             style={{
//                                 display: 'flex', alignItems: 'center', gap: 6,
//                                 padding: '11px 20px', borderRadius: 14,
//                                 border: '2px solid #e5e7eb', background: '#fff',
//                                 fontSize: 14, fontWeight: 600, color: '#374151',
//                                 cursor: (section === 0 && questionIdx === 0) ? 'not-allowed' : 'pointer',
//                                 opacity: (section === 0 && questionIdx === 0) ? 0.4 : 1,
//                             }}
//                         >
//                             <ArrowLeftIcon style={{ width: 16, height: 16 }} />
//                             Back
//                         </button>

//                         {isLastQuestion ? (
//                             <button
//                                 onClick={handleNext}
//                                 disabled={currentAnswer === undefined}
//                                 style={{
//                                     display: 'flex', alignItems: 'center', gap: 8,
//                                     padding: '12px 28px', borderRadius: 14,
//                                     border: 'none',
//                                     background: currentAnswer === undefined
//                                         ? '#e5e7eb'
//                                         : `linear-gradient(135deg, ${sec.color}, ${sec.color}cc)`,
//                                     color: currentAnswer === undefined ? '#9ca3af' : '#fff',
//                                     fontSize: 15, fontWeight: 700,
//                                     cursor: currentAnswer === undefined ? 'not-allowed' : 'pointer',
//                                     boxShadow: currentAnswer !== undefined ? `0 4px 16px ${sec.color}55` : 'none',
//                                     transition: 'all .18s',
//                                 }}
//                             >
//                                 Next
//                                 <ArrowRightIcon style={{ width: 16, height: 16 }} />
//                             </button>
//                         ) : (
//                             <button
//                                 onClick={handleNext}
//                                 disabled={currentAnswer === undefined}
//                                 style={{
//                                     display: 'flex', alignItems: 'center', gap: 7,
//                                     padding: '12px 24px', borderRadius: 14,
//                                     border: 'none',
//                                     background: currentAnswer !== undefined
//                                         ? `linear-gradient(135deg, ${sec.color}, ${sec.color}cc)`
//                                         : '#e5e7eb',
//                                     color: currentAnswer !== undefined ? '#fff' : '#9ca3af',
//                                     fontSize: 15, fontWeight: 700,
//                                     cursor: currentAnswer !== undefined ? 'pointer' : 'not-allowed',
//                                     boxShadow: currentAnswer !== undefined
//                                         ? `0 4px 16px ${sec.color}44` : 'none',
//                                     transition: 'all .18s',
//                                 }}
//                             >
//                                 Next
//                                 <ArrowRightIcon style={{ width: 16, height: 16 }} />
//                             </button>
//                         )}
//                     </div>
//                     {/* end question step */}
//                 </>
//                 )} {/* end showPrefs ternary */}

//                     <style>{`@keyframes wq-spin{to{transform:rotate(360deg)}}`}</style>
//                 </div>
//             </div>
//         </>
//     );
// }


import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { getActivityCategories } from '../../../api/client';
import {
    XMarkIcon,
    ArrowLeftIcon,
    ArrowRightIcon,
    CheckIcon,
    SparklesIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

// ─── 20 Wellbeing Questions ──────────────────────────────────────────────────
const SECTIONS = [
    {
        id: 'body',
        label: 'Body',
        emoji: '🧘',
        color: '#7c3aed',
        lightColor: '#ede9fe',
        title: 'Physical Wellbeing',
        subtitle: 'Questions about physical symptoms related to stress or mental health',
        questions: [
            'How often do you feel tired or low on energy during the day?',
            'How often do you have difficulty sleeping or poor sleep quality?',
            'Do you experience frequent headaches, stomach pain, or body tension?',
            'How often do you feel physically restless or unable to relax?',
            'How often do you feel changes in appetite (eating too much or too little)?',
        ],
    },
    {
        id: 'behavior',
        label: 'Behavior',
        emoji: '⚙️',
        color: '#0ea5e9',
        lightColor: '#e0f2fe',
        title: 'Behavioral Patterns',
        subtitle: 'Questions about behavior changes due to stress or emotional issues',
        questions: [
            'How often do you procrastinate or avoid important tasks?',
            'How often do you lose focus while studying or working?',
            'How often do you spend excessive time on social media or distractions?',
            'How often do you skip responsibilities or commitments?',
            'How often do you feel unmotivated to complete daily activities?',
        ],
    },
    {
        id: 'emotional',
        label: 'Emotional',
        emoji: '💛',
        color: '#f59e0b',
        lightColor: '#fef3c7',
        title: 'Emotional Wellbeing',
        subtitle: 'Questions that measure your emotional state',
        questions: [
            'How often do you feel overwhelmed or stressed?',
            'How often do you feel sad or down without a clear reason?',
            'How often do you feel irritable or easily frustrated?',
            'How often do you feel anxious or worried about the future?',
            'How often do you feel hopeless or discouraged?',
        ],
    },
    {
        id: 'social',
        label: 'Social',
        emoji: '👥',
        color: '#10b981',
        lightColor: '#d1fae5',
        title: 'Social Connection',
        subtitle: 'Questions that measure social connections and relationships',
        questions: [
            'How often do you feel lonely or isolated?',
            'How often do you avoid meeting friends or family?',
            'How often do you feel unsupported by people around you?',
            'How comfortable are you talking about your problems with others?',
            'How often do you feel disconnected from your social circle?',
        ],
    },
];

const ANSWER_OPTIONS = [
    { label: 'Never', value: 1, color: '#10b981', bg: '#d1fae5' },
    { label: 'Rarely', value: 2, color: '#84cc16', bg: '#ecfccb' },
    { label: 'Sometimes', value: 3, color: '#f59e0b', bg: '#fef3c7' },
    { label: 'Often', value: 4, color: '#f97316', bg: '#ffedd5' },
    { label: 'Always', value: 5, color: '#ef4444', bg: '#fee2e2' },
];

// All 20 flat questions with their section index
const ALL_QUESTIONS = SECTIONS.flatMap((sec, si) =>
    sec.questions.map((q, qi) => ({ id: si * 5 + qi, sectionIndex: si, text: q }))
);

// Compute level 1–5 from 20 answers
function computeLevel(answers) {
    const values = Object.values(answers);
    if (!values.length) return 1;
    const avg = values.reduce((s, v) => s + Number(v), 0) / values.length;
    return Math.max(1, Math.min(5, Math.round(avg)));
}

// ─── Type → endpoint segment mapping ────────────────────────────────────────
const TYPE_MAP = {
    PHQ9: 'depression',
    GAD7: 'anxiety',
    PSS10: 'stress',
};

const TYPE_LABELS = {
    PHQ9: 'Depression (PHQ-9)',
    GAD7: 'Anxiety (GAD-7)',
    PSS10: 'Stress (PSS-10)',
};

// ─── Available categories for exclude filter ─────────────────────────────────
// Loaded dynamically from GET /activity/categories
const CATEGORY_META = {
    anxiety_relief: { emoji: '😮‍💨', label: 'Anxiety Relief' },
    depression_relief: { emoji: '💛', label: 'Depression Relief' },
    emotional: { emoji: '❤️', label: 'Emotional' },
    mindfulness: { emoji: '🌸', label: 'Mindfulness' },
    physical: { emoji: '🏃', label: 'Physical' },
    professional: { emoji: '💼', label: 'Professional' },
    routine: { emoji: '📅', label: 'Routine' },
    sleep: { emoji: '😴', label: 'Sleep' },
    social: { emoji: '👥', label: 'Social' },
    stress_relief: { emoji: '🧘', label: 'Stress Relief' },
};

const DEFAULT_PREFS = {
    num_recommendations: 3,
    difficulty_preference: 'easy',
    max_duration_minutes: 0,
    exclude_categories: [],
};

// ─── Main Component ──────────────────────────────────────────────────────────
export default function WellnessQuestionnaireModal({ isOpen, onClose, assessmentType, latestScore }) {
    const navigate = useNavigate();
    const { user } = useAuth();

    // ── Kept as-is: section & questionIdx preserved for handleReset compatibility ──
    const [section, setSection] = useState(0);
    const [questionIdx, setQuestionIdx] = useState(0);

    const [answers, setAnswers] = useState({});
    const [showPrefs, setShowPrefs] = useState(false);
    const [prefs, setPrefs] = useState(DEFAULT_PREFS);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const [availableCategories, setAvailableCategories] = useState([]);
    const [categoriesLoading, setCategoriesLoading] = useState(false);

    // Fetch real categories from API when prefs step opens
    useEffect(() => {
        if (!showPrefs || availableCategories.length > 0) return;
        setCategoriesLoading(true);
        getActivityCategories().then(({ data }) => {
            const cats = (data?.categories || []).map((id) => ({
                id,
                emoji: CATEGORY_META[id]?.emoji || '📌',
                label: CATEGORY_META[id]?.label || id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
            }));
            setAvailableCategories(cats);
            setCategoriesLoading(false);
        });
    }, [showPrefs, availableCategories.length]);

    // ── CHANGED: answeredCount replaces per-question progress calculation ──
    // Previously: progress = ((globalIdx + 1) / totalQuestions) * 100
    // Now: progress = answered questions out of 20, shown across the full form
    const totalQuestions = 20;
    const answeredCount = Object.keys(answers).length;
    const allAnswered = answeredCount === totalQuestions;
    const formProgress = (answeredCount / totalQuestions) * 100;

    // ── Unchanged: handleAnswer logic preserved exactly ──
    // CHANGED: no longer needs useCallback with globalIdx dependency;
    // gIdx is now passed directly from the render loop below.
    const handleAnswer = (gIdx, val) => {
        setAnswers((prev) => ({ ...prev, [gIdx]: val }));
    };

    // ── Unchanged: handlePrev used by prefs "Back" button ──
    const handlePrev = () => {
        if (showPrefs) {
            setShowPrefs(false);
        }
        // Per-question Back logic removed — no longer needed in single-page layout
    };

    // ── Unchanged ──
    const handleReset = () => {
        setSection(0);
        setQuestionIdx(0);
        setAnswers({});
        setShowPrefs(false);
        setPrefs(DEFAULT_PREFS);
        setSubmitError(null);
    };

    // ── Unchanged ──
    const toggleCategory = (catId) => {
        setPrefs((p) => ({
            ...p,
            exclude_categories: p.exclude_categories.includes(catId)
                ? p.exclude_categories.filter((c) => c !== catId)
                : [...p.exclude_categories, catId],
        }));
    };

    // ── Unchanged: full submit logic preserved exactly ──
    const handleSubmit = async () => {
        const userId = user?.id;
        if (!userId) {
            setSubmitError('Cannot submit: user not logged in.');
            return;
        }

        const segment = TYPE_MAP[assessmentType] || 'stress';

        // Use the actual clinical score (0-100 scale) if available. 
        // Otherwise, scale the 1-5 answers level to a 0-100 scale.
        const level = latestScore !== undefined ? latestScore : (computeLevel(answers) * 20);

        const answersArray = ALL_QUESTIONS.map((q) => Number(answers[q.id] ?? 3));

        const payload = {
            answers: answersArray,
            num_recommendations: prefs.num_recommendations,
            difficulty_preference: prefs.difficulty_preference,
            max_duration_minutes: prefs.max_duration_minutes,
            exclude_categories: prefs.exclude_categories,
        };

        setSubmitting(true);
        setSubmitError(null);

        try {
            const res = await fetch(
                `http://127.0.0.1:8000/activity/${segment}/${userId}/${level}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
                    body: JSON.stringify(payload),
                }
            );
            if (!res.ok) {
                const txt = await res.text();
                throw new Error(`Server error ${res.status}: ${txt}`);
            }
            const data = await res.json();
            onClose();
            handleReset();
            navigate('/activities', {
                state: {
                    recommendations: data.recommendations || [],
                    conditionsDetected: data.conditions_detected || [],
                    assessmentType,
                    assessmentLabel: TYPE_LABELS[assessmentType] || assessmentType,
                    generatedAt: data.generated_at,
                },
            });
        } catch (e) {
            setSubmitError(e.message);
        } finally {
            setSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop — unchanged */}
            <div style={{
                position: 'fixed', inset: 0, zIndex: 1200,
                background: 'rgba(0,0,0,0.55)',
                backdropFilter: 'blur(6px)',
                WebkitBackdropFilter: 'blur(6px)',
            }} />

            {/* Modal shell — unchanged */}
            <div style={{
                position: 'fixed', inset: 0, zIndex: 1201,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: 16,
                pointerEvents: 'none',
            }}>
                <div style={{
                    width: '100%',
                    maxWidth: 540,
                    maxHeight: '92vh',
                    overflowY: 'auto',
                    background: '#fff',
                    borderRadius: 28,
                    boxShadow: '0 32px 96px rgba(0,0,0,.25)',
                    pointerEvents: 'all',
                    position: 'relative',
                    padding: '28px 28px 24px',
                }}>

                    {/* Close — unchanged */}
                    <button
                        onClick={() => { onClose(); handleReset(); }}
                        style={{
                            position: 'absolute', top: 20, right: 20,
                            width: 34, height: 34, borderRadius: '50%',
                            border: 'none', background: '#f3f4f6', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}
                    >
                        <XMarkIcon style={{ width: 18, height: 18, color: '#6b7280' }} />
                    </button>

                    {/* ── PREFERENCES STEP — entirely unchanged ── */}
                    {showPrefs ? (
                        <>
                            {/* Prefs Header */}
                            <div style={{ marginBottom: 22 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                                    <div style={{
                                        width: 38, height: 38, borderRadius: 12,
                                        background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
                                    }}>⚙️</div>
                                    <div>
                                        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
                                            Personalise Your Activities
                                        </h2>
                                        <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
                                            Almost done! Customise your recommendations.
                                        </p>
                                    </div>
                                </div>
                                {/* Full bar */}
                                <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: '100%', background: 'linear-gradient(90deg,#7c3aed,#a78bfa)', borderRadius: 99 }} />
                                </div>
                            </div>

                            {/* ── How many recommendations ── */}
                            <div style={{ marginBottom: 22 }}>
                                <p style={{ margin: '0 0 10px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
                                    How many activity suggestions do you want?
                                </p>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    {[1, 2, 3, 4, 5].map((n) => (
                                        <button
                                            key={n}
                                            onClick={() => setPrefs((p) => ({ ...p, num_recommendations: n }))}
                                            style={{
                                                flex: 1, padding: '10px 0', borderRadius: 12,
                                                border: prefs.num_recommendations === n ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                                                background: prefs.num_recommendations === n ? '#ede9fe' : '#fafafa',
                                                color: prefs.num_recommendations === n ? '#7c3aed' : '#6b7280',
                                                fontSize: 16, fontWeight: 700, cursor: 'pointer',
                                                transition: 'all .15s',
                                            }}
                                        >{n}</button>
                                    ))}
                                </div>
                            </div>

                            {/* ── Difficulty preference ── */}
                            <div style={{ marginBottom: 22 }}>
                                <p style={{ margin: '0 0 10px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
                                    Preferred activity difficulty
                                </p>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    {[
                                        { value: 'easy', label: 'Easy', emoji: '🌱', color: '#10b981', bg: '#d1fae5' },
                                        { value: 'moderate', label: 'Moderate', emoji: '🔥', color: '#f59e0b', bg: '#fef3c7' },
                                        { value: 'challenging', label: 'Challenging', emoji: '💪', color: '#ef4444', bg: '#fee2e2' },
                                    ].map((d) => {
                                        const sel = prefs.difficulty_preference === d.value;
                                        return (
                                            <button
                                                key={d.value}
                                                onClick={() => setPrefs((p) => ({ ...p, difficulty_preference: d.value }))}
                                                style={{
                                                    flex: 1, padding: '12px 6px', borderRadius: 14,
                                                    border: sel ? `2px solid ${d.color}` : '2px solid #e5e7eb',
                                                    background: sel ? d.bg : '#fafafa',
                                                    cursor: 'pointer', textAlign: 'center',
                                                    transition: 'all .15s',
                                                }}
                                            >
                                                <div style={{ fontSize: 20, marginBottom: 4 }}>{d.emoji}</div>
                                                <div style={{ fontSize: 12, fontWeight: 700, color: sel ? d.color : '#6b7280' }}>{d.label}</div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* ── Max duration ── */}
                            <div style={{ marginBottom: 22 }}>
                                <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
                                    Maximum activity duration
                                </p>
                                <p style={{ margin: '0 0 10px', fontSize: 12, color: '#9ca3af' }}>
                                    Set to 0 for no time limit
                                </p>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <input
                                        type="range"
                                        min={0} max={60} step={5}
                                        value={prefs.max_duration_minutes}
                                        onChange={(e) => setPrefs((p) => ({ ...p, max_duration_minutes: Number(e.target.value) }))}
                                        style={{ flex: 1, accentColor: '#7c3aed' }}
                                    />
                                    <span style={{
                                        minWidth: 64, textAlign: 'center',
                                        padding: '6px 10px', borderRadius: 10,
                                        background: '#ede9fe', color: '#7c3aed',
                                        fontSize: 13, fontWeight: 700,
                                    }}>
                                        {prefs.max_duration_minutes === 0 ? 'No limit' : `${prefs.max_duration_minutes} min`}
                                    </span>
                                </div>
                            </div>

                            {/* ── Exclude categories ── */}
                            <div style={{ marginBottom: 24 }}>
                                <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700, color: '#374151' }}>
                                    Exclude activity categories
                                </p>
                                <p style={{ margin: '0 0 10px', fontSize: 12, color: '#9ca3af' }}>
                                    Tap to exclude categories you'd prefer to avoid
                                </p>
                                {categoriesLoading ? (
                                    <p style={{ fontSize: 12, color: '#9ca3af' }}>Loading categories…</p>
                                ) : (
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                        {availableCategories.map((cat) => {
                                            const excluded = prefs.exclude_categories.includes(cat.id);
                                            return (
                                                <button
                                                    key={cat.id}
                                                    onClick={() => toggleCategory(cat.id)}
                                                    style={{
                                                        display: 'flex', alignItems: 'center', gap: 5,
                                                        padding: '7px 13px', borderRadius: 99,
                                                        border: excluded ? '2px solid #ef4444' : '2px solid #e5e7eb',
                                                        background: excluded ? '#fee2e2' : '#f9fafb',
                                                        color: excluded ? '#ef4444' : '#4b5563',
                                                        fontSize: 12, fontWeight: 600, cursor: 'pointer',
                                                        textDecoration: excluded ? 'line-through' : 'none',
                                                        transition: 'all .15s',
                                                    }}
                                                >
                                                    <span>{cat.emoji}</span> {cat.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Error */}
                            {submitError && (
                                <div style={{
                                    display: 'flex', alignItems: 'flex-start', gap: 8,
                                    padding: '12px 14px', borderRadius: 12, marginBottom: 16,
                                    background: '#fef2f2', border: '1px solid #fecaca',
                                }}>
                                    <ExclamationTriangleIcon style={{ width: 16, height: 16, color: '#ef4444', flexShrink: 0, marginTop: 1 }} />
                                    <p style={{ margin: 0, fontSize: 13, color: '#ef4444' }}>{submitError}</p>
                                </div>
                            )}

                            {/* Prefs Navigation — unchanged */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <button
                                    onClick={handlePrev}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 6,
                                        padding: '11px 20px', borderRadius: 14,
                                        border: '2px solid #e5e7eb', background: '#fff',
                                        fontSize: 14, fontWeight: 600, color: '#374151', cursor: 'pointer',
                                    }}
                                >
                                    <ArrowLeftIcon style={{ width: 16, height: 16 }} />
                                    Back
                                </button>
                                <button
                                    onClick={handleSubmit}
                                    disabled={submitting}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 8,
                                        padding: '12px 28px', borderRadius: 14, border: 'none',
                                        background: submitting ? '#e5e7eb' : 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                                        color: submitting ? '#9ca3af' : '#fff',
                                        fontSize: 15, fontWeight: 700,
                                        cursor: submitting ? 'not-allowed' : 'pointer',
                                        boxShadow: !submitting ? '0 4px 16px rgba(124,58,237,.35)' : 'none',
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
                                                animation: 'wq-spin 0.9s linear infinite',
                                                display: 'inline-block',
                                            }} />
                                            Getting Activities…
                                        </>
                                    ) : (
                                        <>
                                            <SparklesIcon style={{ width: 17, height: 17 }} />
                                            Get My Activities
                                        </>
                                    )}
                                </button>
                            </div>
                        </>

                    ) : (

                        // ════════════════════════════════════════════════════════════════
                        // ── CHANGED: QUESTION STEP — redesigned as single-page layout ──
                        // ════════════════════════════════════════════════════════════════
                        //
                        // BEFORE: One question at a time with Back/Next navigation arrows,
                        //         section-scoped progress bar, and large stacked answer
                        //         buttons (each consuming ~50px height).
                        //
                        // AFTER:  All 20 questions visible in a scrollable vertical flow,
                        //         grouped by section — similar to Google Forms.
                        //         Each question shows a compact horizontal row of pill
                        //         radio buttons (Never → Always) using the exact same
                        //         ANSWER_OPTIONS colors and values as before.
                        //         Per-question Back/Next arrows removed; a single
                        //         "Continue to Preferences" button at the bottom
                        //         is enabled only when all 20 questions are answered.
                        // ════════════════════════════════════════════════════════════════
                        <>
                            {/* ── Form Header ── */}
                            <div style={{ marginBottom: 24 }}>

                                {/* Title row — font sizes and colors preserved */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                                    {/*
                                     * CHANGED: Icon now uses a neutral purple background
                                     * (matches the first section color) because there is no
                                     * single "active section" in a single-page layout.
                                     * Previously it reflected the current section's color.
                                     */}
                                    <div style={{
                                        width: 38, height: 38, borderRadius: 12,
                                        background: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: 18,
                                    }}>
                                        📋
                                    </div>
                                    <div>
                                        {/* Unchanged: fontSize 16, fontWeight 800, color #111827 */}
                                        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#111827' }}>
                                            Wellness Check — {TYPE_LABELS[assessmentType] || assessmentType}
                                        </h2>
                                        {/*
                                         * CHANGED: Sub-label now shows answered count instead of
                                         * "Question X of 20" — meaningful for a full-page view.
                                         * Font size 12 and color #9ca3af preserved.
                                         */}
                                        <p style={{ margin: 0, fontSize: 12, color: '#9ca3af' }}>
                                            {answeredCount} of {totalQuestions} questions answered
                                        </p>
                                    </div>
                                </div>

                                {/*
                                 * CHANGED: Progress bar now reflects total answered / 20.
                                 * Previously it tracked the current question index.
                                 * Bar style (height 6, #f3f4f6 bg, border-radius 99) preserved.
                                 * Colour uses purple gradient (neutral) instead of
                                 * per-section colour since all sections are visible.
                                 */}
                                <div style={{ height: 6, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden', marginBottom: 14 }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${formProgress}%`,
                                        background: 'linear-gradient(90deg,#7c3aed,#a78bfa)',
                                        borderRadius: 99,
                                        transition: 'width .3s ease',
                                    }} />
                                </div>

                                {/*
                                 * CHANGED: Section indicator pills shown as a static legend row
                                 * instead of interactive tab dots.
                                 * Previously the four dots changed colour as the user progressed
                                 * through sections one-by-one.
                                 */}
                                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                    {SECTIONS.map((s) => (
                                        <span
                                            key={s.id}
                                            style={{
                                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                                padding: '3px 10px', borderRadius: 99,
                                                background: s.lightColor, color: s.color,
                                                fontSize: 11, fontWeight: 700,
                                            }}
                                        >
                                            {s.emoji} {s.label}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/*
                             * ── Single-page question body ──
                             *
                             * CHANGED: Replaced single-question render with a full section
                             * loop. Each section renders a coloured header card followed by
                             * its 5 questions, each with a horizontal pill radio row.
                             *
                             * Google Forms design cues applied:
                             *   • Clear visual section grouping with coloured band
                             *   • Question number prefix for scannability
                             *   • Answers sit inline below each question (not in a modal)
                             *   • Subtle card background separates each question row
                             */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
                                {SECTIONS.map((sec, si) => (
                                    <div key={sec.id}>

                                        {/* ── Section header band ── */}
                                        <div style={{
                                            display: 'flex', alignItems: 'flex-start', gap: 10,
                                            padding: '12px 16px', borderRadius: 14,
                                            background: sec.lightColor,
                                            borderLeft: `4px solid ${sec.color}`,
                                            marginBottom: 12,
                                        }}>
                                            <span style={{ fontSize: 20, lineHeight: 1.3 }}>{sec.emoji}</span>
                                            <div>
                                                {/* font sizes and colors match original section label block */}
                                                <div style={{ fontSize: 14, fontWeight: 800, color: sec.color }}>
                                                    {sec.title}
                                                </div>
                                                <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                                                    {sec.subtitle}
                                                </div>
                                            </div>
                                        </div>

                                        {/* ── Questions in this section ── */}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                            {sec.questions.map((questionText, qi) => {
                                                /*
                                                 * gIdx mirrors the original globalIdx calculation
                                                 * (section * 5 + questionIdx) so answers{} keying
                                                 * is 100% compatible with handleSubmit / computeLevel.
                                                 */
                                                const gIdx = si * 5 + qi;
                                                const selectedVal = answers[gIdx];
                                                const isAnswered = selectedVal !== undefined;

                                                return (
                                                    <div
                                                        key={gIdx}
                                                        style={{
                                                            padding: '14px 16px',
                                                            borderRadius: 14,
                                                            /*
                                                             * CHANGED: background tints to the answered
                                                             * option's colour when selected, otherwise
                                                             * neutral #fafafa — gives instant visual
                                                             * feedback like a Google Form selection.
                                                             */
                                                            background: isAnswered
                                                                ? ANSWER_OPTIONS.find(o => o.value === selectedVal)?.bg || '#fafafa'
                                                                : '#fafafa',
                                                            border: isAnswered
                                                                ? `1.5px solid ${ANSWER_OPTIONS.find(o => o.value === selectedVal)?.color || '#e5e7eb'}`
                                                                : '1.5px solid #f3f4f6',
                                                            transition: 'background .2s, border-color .2s',
                                                        }}
                                                    >
                                                        {/* Question text — fontSize 14, fontWeight 600, color #1f2937 preserved */}
                                                        <p style={{
                                                            margin: '0 0 12px',
                                                            fontSize: 14, fontWeight: 600, color: '#1f2937',
                                                            lineHeight: 1.45,
                                                        }}>
                                                            {/* Question number prefix, coloured to section */}
                                                            <span style={{
                                                                fontWeight: 800, color: sec.color,
                                                                marginRight: 4,
                                                            }}>
                                                                {gIdx + 1}.
                                                            </span>
                                                            {questionText}
                                                        </p>

                                                        {/*
                                                         * ── CHANGED: Answer options ──
                                                         *
                                                         * BEFORE: Stacked full-width buttons (~50 px each,
                                                         *   ~250 px total per question) with a large radio
                                                         *   circle on the left and value badge on the right.
                                                         *
                                                         * AFTER: Compact horizontal pill buttons in a single
                                                         *   row. Same ANSWER_OPTIONS array, same colors/values,
                                                         *   same CheckIcon on selection — just laid out
                                                         *   horizontally and scaled down to fit 5 options
                                                         *   side-by-side (Google Forms linear-scale style).
                                                         *
                                                         * handleAnswer now receives gIdx explicitly
                                                         * (previously captured via closure on globalIdx).
                                                         */}
                                                        <div style={{
                                                            display: 'flex',
                                                            gap: 6,
                                                            flexWrap: 'wrap',   /* wraps on very narrow screens */
                                                        }}>
                                                            {ANSWER_OPTIONS.map((opt) => {
                                                                const selected = selectedVal === opt.value;
                                                                return (
                                                                    <button
                                                                        key={opt.value}
                                                                        onClick={() => handleAnswer(gIdx, opt.value)}
                                                                        style={{
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: 5,
                                                                            /* CHANGED: padding reduced from '12px 16px'
                                                                             * to '7px 12px' to keep all 5 options in
                                                                             * one compact horizontal row. */
                                                                            padding: '7px 12px',
                                                                            borderRadius: 99,
                                                                            /* Border and background colours
                                                                             * preserved from original ANSWER_OPTIONS */
                                                                            border: selected
                                                                                ? `2px solid ${opt.color}`
                                                                                : '2px solid #e5e7eb',
                                                                            background: selected ? opt.color : '#fff',
                                                                            color: selected ? '#fff' : '#6b7280',
                                                                            /* CHANGED: fontSize 12 (was 14) to
                                                                             * accommodate horizontal layout */
                                                                            fontSize: 12,
                                                                            fontWeight: 600,
                                                                            cursor: 'pointer',
                                                                            transition: 'all .15s',
                                                                            whiteSpace: 'nowrap',
                                                                        }}
                                                                    >
                                                                        {/*
                                                                         * CheckIcon preserved on selection.
                                                                         * CHANGED: icon is now inline-left of label
                                                                         * instead of inside a separate radio circle.
                                                                         */}
                                                                        {selected && (
                                                                            <CheckIcon style={{ width: 12, height: 12, color: '#fff', flexShrink: 0 }} />
                                                                        )}
                                                                        {opt.label}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* ── Bottom CTA ── */}
                            {/*
                             * CHANGED: Replaced per-question Back/Next navigation with a
                             * single "Continue to Preferences" button.
                             *
                             * • Button style (gradient, border-radius 14, fontSize 15,
                             *   fontWeight 700, disabled states) matches the original Next
                             *   button exactly — only the label and positioning differ.
                             * • Button is right-aligned (no Back button needed — users can
                             *   scroll freely in the single-page layout).
                             * • Disabled until all 20 questions are answered.
                             */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginTop: 28,
                                paddingTop: 20,
                                borderTop: '1.5px solid #f3f4f6',
                            }}>
                                {/* Answered counter — helpful affordance replacing per-step progress */}
                                <span style={{ fontSize: 12, color: '#9ca3af', fontWeight: 600 }}>
                                    {allAnswered
                                        ? '✅ All questions answered'
                                        : `${totalQuestions - answeredCount} remaining`}
                                </span>

                                <button
                                    onClick={() => setShowPrefs(true)}
                                    disabled={!allAnswered}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 8,
                                        padding: '12px 24px', borderRadius: 14, border: 'none',
                                        /* Gradient and disabled colours preserved from original Next button */
                                        background: allAnswered
                                            ? 'linear-gradient(135deg,#7c3aed,#6d28d9)'
                                            : '#e5e7eb',
                                        color: allAnswered ? '#fff' : '#9ca3af',
                                        fontSize: 15, fontWeight: 700,
                                        cursor: allAnswered ? 'pointer' : 'not-allowed',
                                        boxShadow: allAnswered ? '0 4px 16px rgba(124,58,237,.35)' : 'none',
                                        transition: 'all .18s',
                                    }}
                                >
                                    Continue
                                    <ArrowRightIcon style={{ width: 16, height: 16 }} />
                                </button>
                            </div>
                            {/* ══ END CHANGED SECTION ══ */}
                        </>
                    )}

                    <style>{`@keyframes wq-spin{to{transform:rotate(360deg)}}`}</style>
                </div>
            </div>
        </>
    );
}