import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button, Alert, Loader, Badge } from '../../components/common';
import { useAuth } from '../../contexts/AuthContext';
import {
    startTherapySession, therapyCheckIn, therapySendMessage,
    therapyAdvance, therapyGetCBT, therapyGetReframe,
    therapyGetPlan, therapyGetRelax, therapyComplete,
} from '../../api/client';
import {
    HeartIcon, ChatBubbleLeftRightIcon, LightBulbIcon,
    ArrowPathIcon, SparklesIcon, CloudIcon,
    DocumentTextIcon, PlayIcon, ArrowRightIcon,
    FaceSmileIcon, ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

// ─── Phase definitions ──────────────────────────────────────────────────────
const PHASES = [
    { key: 'not_started', label: 'Welcome', icon: HeartIcon },
    { key: 'check_in', label: 'Check-In', icon: FaceSmileIcon },
    { key: 'listening', label: 'Listening', icon: ChatBubbleLeftRightIcon },
    { key: 'cbt', label: 'CBT', icon: LightBulbIcon },
    { key: 'reframe', label: 'Reframe', icon: ArrowPathIcon },
    { key: 'plan', label: 'Plan', icon: DocumentTextIcon },
    { key: 'relax', label: 'Wind Down', icon: CloudIcon },
    { key: 'summary', label: 'Summary', icon: SparklesIcon },
];

// ─── Progress Bar ───────────────────────────────────────────────────────────
function ProgressBar({ currentPhase }) {
    return (
        <div className="w-full mb-8">
            <div className="flex items-center justify-between">
                {PHASES.slice(1).map((p, idx) => {
                    const phaseIdx = idx + 1;
                    const isActive = currentPhase === phaseIdx;
                    const isComplete = currentPhase > phaseIdx;
                    const Icon = p.icon;
                    return (
                        <div key={p.key} className="flex flex-col items-center flex-1">
                            <div className="flex items-center w-full">
                                {idx > 0 && (
                                    <div
                                        className={`flex-1 h-0.5 transition-colors duration-300 ${
                                            currentPhase > phaseIdx ? 'bg-terracotta' : 'bg-sand'
                                        }`}
                                    />
                                )}
                                <div
                                    className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${
                                        isActive
                                            ? 'bg-terracotta text-white shadow-lg scale-110'
                                            : isComplete
                                            ? 'bg-terracotta/80 text-white'
                                            : 'bg-sand/60 text-terracotta-dark/40'
                                    }`}
                                >
                                    <Icon className="w-4 h-4" />
                                </div>
                                {idx < PHASES.length - 2 && (
                                    <div
                                        className={`flex-1 h-0.5 transition-colors duration-300 ${
                                            currentPhase > phaseIdx ? 'bg-terracotta' : 'bg-sand'
                                        }`}
                                    />
                                )}
                            </div>
                            <span
                                className={`text-xs mt-1.5 font-medium transition-colors duration-300 ${
                                    isActive ? 'text-terracotta-dark' : isComplete ? 'text-terracotta' : 'text-stone-400'
                                }`}
                            >
                                {p.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Breathing animation component ──────────────────────────────────────────
function BreathingExercise() {
    const [breathPhase, setBreathPhase] = useState('inhale');
    const [count, setCount] = useState(4);

    useEffect(() => {
        const durations = { inhale: 4, hold: 7, exhale: 8 };
        const next = { inhale: 'hold', hold: 'exhale', exhale: 'inhale' };
        const timer = setInterval(() => {
            setCount((c) => {
                if (c <= 1) {
                    setBreathPhase((p) => {
                        const np = next[p];
                        setCount(durations[np]);
                        return np;
                    });
                    return 1;
                }
                return c - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    const scale = breathPhase === 'inhale' ? 'scale-125' : breathPhase === 'exhale' ? 'scale-75' : 'scale-110';

    return (
        <div className="flex flex-col items-center py-8">
            <div
                className={`w-32 h-32 rounded-full bg-gradient-to-br from-lavender-light to-sage-light flex items-center justify-center transition-transform duration-1000 ${scale}`}
            >
                <div className="text-center">
                    <p className="text-lg font-display font-semibold text-terracotta-dark capitalize">
                        {breathPhase}
                    </p>
                    <p className="text-3xl font-bold text-terracotta">{count}</p>
                </div>
            </div>
            <p className="mt-4 text-sm text-stone-500">4-7-8 Breathing Pattern</p>
        </div>
    );
}

// ─── Main Component ─────────────────────────────────────────────────────────
function TherapySession() {
    const { user } = useAuth();
    const userId = user?.id;

    // State machine
    const [phase, setPhase] = useState(0);
    const [sessionId, setSessionId] = useState(null);
    const [phaseData, setPhaseData] = useState({});
    const [error, setError] = useState(null);

    // Phase 1 state
    const [moodScore, setMoodScore] = useState(5);
    const [concern, setConcern] = useState('');

    // Phase 2 state
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const chatEndRef = useRef(null);

    // Phase 7 state
    const [finalMood, setFinalMood] = useState(5);

    // Auto-scroll chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Helper to unwrap { data, error } from API client
    const unwrap = async (promise) => {
        const res = await promise;
        if (res.error) throw new Error(res.error);
        return res.data;
    };

    // ── Mutations ────────────────────────────────────────────────────────────
    const startMutation = useMutation({
        mutationFn: () => unwrap(startTherapySession(userId)),
        onSuccess: (data) => {
            setSessionId(data.session_id);
            setPhase(1);
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to start session'),
    });

    const checkInMutation = useMutation({
        mutationFn: () => unwrap(therapyCheckIn(sessionId, moodScore, concern)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, checkIn: data }));
            setMessages([{ role: 'assistant', text: data.opening_message || data.message || "Thank you for sharing. I'm here to listen." }]);
            setPhase(2);
            setError(null);
        },
        onError: (err) => setError(err.message || 'Check-in failed'),
    });

    const sendMsgMutation = useMutation({
        mutationFn: (msg) => unwrap(therapySendMessage(sessionId, msg)),
        onSuccess: (data) => {
            const reply = {
                role: 'assistant',
                text: data.bot_response || data.response || data.message || '',
                emotions: data.emotion ? [data.emotion] : (data.sentiment?.label ? [data.sentiment.label] : []),
            };
            setMessages((prev) => [...prev, reply]);
        },
        onError: (err) => setError(err.message || 'Failed to send message'),
    });

    const advanceMutation = useMutation({
        mutationFn: () => unwrap(therapyAdvance(sessionId)),
        onSuccess: () => {
            setPhase(3);
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to advance'),
    });

    const cbtMutation = useMutation({
        mutationFn: () => unwrap(therapyGetCBT(sessionId)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, cbt: data }));
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to get CBT analysis'),
    });

    const reframeMutation = useMutation({
        mutationFn: () => unwrap(therapyGetReframe(sessionId)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, reframe: data }));
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to get reframe'),
    });

    const planMutation = useMutation({
        mutationFn: () => unwrap(therapyGetPlan(sessionId)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, plan: data }));
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to get plan'),
    });

    const relaxMutation = useMutation({
        mutationFn: () => unwrap(therapyGetRelax(sessionId)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, relax: data }));
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to get relaxation'),
    });

    const completeMutation = useMutation({
        mutationFn: () => unwrap(therapyComplete(sessionId, finalMood)),
        onSuccess: (data) => {
            setPhaseData((prev) => ({ ...prev, summary: data }));
            setError(null);
        },
        onError: (err) => setError(err.message || 'Failed to complete session'),
    });

    // ── Auto-fetch for phases 3-6 ───────────────────────────────────────────
    useEffect(() => {
        if (phase === 3 && !phaseData.cbt && !cbtMutation.isPending) {
            cbtMutation.mutate();
        }
    }, [phase]);

    useEffect(() => {
        if (phase === 4 && !phaseData.reframe && !reframeMutation.isPending) {
            reframeMutation.mutate();
        }
    }, [phase]);

    useEffect(() => {
        if (phase === 5 && !phaseData.plan && !planMutation.isPending) {
            planMutation.mutate();
        }
    }, [phase]);

    useEffect(() => {
        if (phase === 6 && !phaseData.relax && !relaxMutation.isPending) {
            relaxMutation.mutate();
        }
    }, [phase]);

    // ── Handlers ─────────────────────────────────────────────────────────────
    const handleSendMessage = () => {
        if (!chatInput.trim()) return;
        setMessages((prev) => [...prev, { role: 'user', text: chatInput.trim() }]);
        sendMsgMutation.mutate(chatInput.trim());
        setChatInput('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // ── Render Phases ────────────────────────────────────────────────────────
    const renderPhase0 = () => (
        <Card className="rounded-2xl shadow-organic overflow-hidden">
            <div className="bg-gradient-to-br from-cream to-lavender/20 p-8 md:p-12 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-white/60 flex items-center justify-center">
                    <HeartIcon className="w-8 h-8 text-terracotta" />
                </div>
                <h2 className="text-2xl md:text-3xl font-display font-bold text-stone-800 mb-3">
                    Welcome to Your Guided Wellness Session
                </h2>
                <p className="text-stone-600 max-w-lg mx-auto mb-2">
                    This is a safe, private space designed to help you explore your thoughts and feelings.
                    Over the next few minutes, we will guide you through seven gentle phases:
                </p>
                <ul className="text-sm text-stone-500 max-w-md mx-auto text-left space-y-1 mb-8">
                    <li className="flex items-center gap-2"><FaceSmileIcon className="w-4 h-4 text-terracotta" /> Emotional check-in</li>
                    <li className="flex items-center gap-2"><ChatBubbleLeftRightIcon className="w-4 h-4 text-terracotta" /> Active listening conversation</li>
                    <li className="flex items-center gap-2"><LightBulbIcon className="w-4 h-4 text-terracotta" /> Cognitive pattern recognition</li>
                    <li className="flex items-center gap-2"><ArrowPathIcon className="w-4 h-4 text-terracotta" /> Thought reframing</li>
                    <li className="flex items-center gap-2"><DocumentTextIcon className="w-4 h-4 text-terracotta" /> Personalized intervention plan</li>
                    <li className="flex items-center gap-2"><CloudIcon className="w-4 h-4 text-terracotta" /> Relaxation exercise</li>
                    <li className="flex items-center gap-2"><SparklesIcon className="w-4 h-4 text-terracotta" /> Session summary and reflection</li>
                </ul>
                <Button
                    onClick={() => startMutation.mutate()}
                    disabled={startMutation.isPending}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-8 py-3 rounded-xl font-semibold shadow-lg"
                >
                    {startMutation.isPending ? (
                        <span className="flex items-center gap-2"><Loader className="w-4 h-4" /> Starting...</span>
                    ) : (
                        <span className="flex items-center gap-2"><PlayIcon className="w-5 h-5" /> Begin Your Session</span>
                    )}
                </Button>
            </div>
        </Card>
    );

    const renderPhase1 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <FaceSmileIcon className="w-6 h-6 text-terracotta" />
                    How are you feeling right now?
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Mood slider */}
                <div>
                    <label className="block text-sm font-medium text-stone-600 mb-2">
                        Mood Level: <span className="text-terracotta font-bold text-lg">{moodScore}</span>/10
                    </label>
                    <input
                        type="range"
                        min="1"
                        max="10"
                        value={moodScore}
                        onChange={(e) => setMoodScore(Number(e.target.value))}
                        className="w-full h-2 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-coral-light via-sand to-sage-light accent-terracotta"
                    />
                    <div className="flex justify-between text-xs text-stone-400 mt-1">
                        <span>Very Low</span>
                        <span>Neutral</span>
                        <span>Great</span>
                    </div>
                </div>

                {/* Concern textarea */}
                <div>
                    <label className="block text-sm font-medium text-stone-600 mb-2">
                        What is on your mind today?
                    </label>
                    <textarea
                        value={concern}
                        onChange={(e) => setConcern(e.target.value)}
                        placeholder="Share whatever feels right... There are no wrong answers here."
                        rows={4}
                        className="w-full rounded-xl border border-sand bg-cream/30 px-4 py-3 text-stone-700 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta resize-none"
                    />
                </div>
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => checkInMutation.mutate()}
                    disabled={checkInMutation.isPending || !concern.trim()}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                >
                    {checkInMutation.isPending ? (
                        <span className="flex items-center gap-2"><Loader className="w-4 h-4" /> Submitting...</span>
                    ) : (
                        <span className="flex items-center gap-2">Continue <ArrowRightIcon className="w-4 h-4" /></span>
                    )}
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase2 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <ChatBubbleLeftRightIcon className="w-6 h-6 text-terracotta" />
                    Let us Talk
                </CardTitle>
            </CardHeader>
            <CardContent>
                {/* Chat messages */}
                <div className="h-80 overflow-y-auto space-y-3 mb-4 p-3 rounded-xl bg-ivory/50 border border-sand/40">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div
                                className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${
                                    msg.role === 'user'
                                        ? 'bg-cream text-stone-700 rounded-br-sm'
                                        : 'bg-white border border-sand/60 text-stone-700 rounded-bl-sm'
                                }`}
                            >
                                <p>{msg.text}</p>
                                {msg.emotions && msg.emotions.length > 0 && (
                                    <div className="flex gap-1 mt-1.5 flex-wrap">
                                        {msg.emotions.map((em, i) => (
                                            <Badge key={i} className="text-2xs bg-lavender-light/50 text-lavender-dark">
                                                {em}
                                            </Badge>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {sendMsgMutation.isPending && (
                        <div className="flex justify-start">
                            <div className="px-4 py-2.5 rounded-2xl bg-white border border-sand/60 rounded-bl-sm">
                                <Loader className="w-4 h-4 text-terracotta" />
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                {/* Input */}
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type your thoughts..."
                        className="flex-1 rounded-xl border border-sand bg-cream/30 px-4 py-2.5 text-sm text-stone-700 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta"
                    />
                    <Button
                        onClick={handleSendMessage}
                        disabled={!chatInput.trim() || sendMsgMutation.isPending}
                        className="bg-terracotta hover:bg-terracotta-dark text-white px-4 py-2.5 rounded-xl"
                    >
                        Send
                    </Button>
                </div>
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => advanceMutation.mutate()}
                    disabled={advanceMutation.isPending}
                    variant="outline"
                    className="border-terracotta text-terracotta hover:bg-terracotta/5 px-5 py-2 rounded-xl font-medium"
                >
                    {advanceMutation.isPending ? (
                        <span className="flex items-center gap-2"><Loader className="w-4 h-4" /> Moving on...</span>
                    ) : (
                        <span className="flex items-center gap-2">I am ready to move on <ArrowRightIcon className="w-4 h-4" /></span>
                    )}
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase3 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <LightBulbIcon className="w-6 h-6 text-terracotta" />
                    Cognitive Pattern Analysis
                </CardTitle>
            </CardHeader>
            <CardContent>
                {cbtMutation.isPending ? (
                    <div className="flex flex-col items-center py-12">
                        <Loader className="w-8 h-8 text-terracotta mb-3" />
                        <p className="text-stone-500 text-sm">Analyzing your thought patterns...</p>
                    </div>
                ) : phaseData.cbt ? (
                    <div className="space-y-4">
                        {phaseData.cbt.distortion?.distortion_type && (
                            <div>
                                <p className="text-sm font-medium text-stone-600 mb-2">Detected Patterns:</p>
                                <div className="flex flex-wrap gap-2">
                                    <Badge
                                        className="bg-coral-light/20 text-coral-dark border border-coral-light/40 px-3 py-1"
                                    >
                                        {phaseData.cbt.distortion.distortion_type}
                                    </Badge>
                                </div>
                            </div>
                        )}
                        <div className="bg-cream/50 border border-sand/50 rounded-xl p-4">
                            <p className="text-stone-700 text-sm leading-relaxed">
                                {phaseData.cbt.message || phaseData.cbt.analysis || phaseData.cbt.explanation}
                            </p>
                        </div>
                    </div>
                ) : null}
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => setPhase(4)}
                    disabled={!phaseData.cbt}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                >
                    <span className="flex items-center gap-2">Continue <ArrowRightIcon className="w-4 h-4" /></span>
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase4 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <ArrowPathIcon className="w-6 h-6 text-terracotta" />
                    Guided Reframe
                </CardTitle>
            </CardHeader>
            <CardContent>
                {reframeMutation.isPending ? (
                    <div className="flex flex-col items-center py-12">
                        <Loader className="w-8 h-8 text-terracotta mb-3" />
                        <p className="text-stone-500 text-sm">Preparing your reframe exercise...</p>
                    </div>
                ) : phaseData.reframe ? (
                    <div className="space-y-4">
                        {/* Original thought context (if available) */}
                        {phaseData.reframe.original_thought && (
                            <div className="bg-coral-light/10 border border-coral-light/30 rounded-xl p-4">
                                <p className="text-xs font-semibold text-coral-dark uppercase tracking-wide mb-1">Original Thought</p>
                                <p className="text-stone-700 text-sm">{phaseData.reframe.original_thought}</p>
                            </div>
                        )}

                        {/* Identified distortion */}
                        {phaseData.cbt?.distortion?.distortion_type && (
                            <div className="bg-sand/30 border border-sand rounded-xl p-4">
                                <p className="text-xs font-semibold text-terracotta-dark uppercase tracking-wide mb-1">Identified Pattern</p>
                                <p className="text-stone-700 text-sm">{phaseData.cbt.distortion.distortion_type}</p>
                            </div>
                        )}

                        {/* Reframed perspective */}
                        <div className="bg-sage-light/20 border border-sage-light/50 rounded-xl p-4">
                            <p className="text-xs font-semibold text-sage-dark uppercase tracking-wide mb-1">Guided Reframe</p>
                            <p className="text-stone-700 text-sm leading-relaxed">
                                {phaseData.reframe.reframe_exercise || phaseData.reframe.reframed_thought || phaseData.reframe.reframe || phaseData.reframe.message}
                            </p>
                        </div>
                    </div>
                ) : null}
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => setPhase(5)}
                    disabled={!phaseData.reframe}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                >
                    <span className="flex items-center gap-2">Continue <ArrowRightIcon className="w-4 h-4" /></span>
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase5 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <DocumentTextIcon className="w-6 h-6 text-terracotta" />
                    Your Intervention Plan
                </CardTitle>
            </CardHeader>
            <CardContent>
                {planMutation.isPending ? (
                    <div className="flex flex-col items-center py-12">
                        <Loader className="w-8 h-8 text-terracotta mb-3" />
                        <p className="text-stone-500 text-sm">Building your personalized plan...</p>
                    </div>
                ) : phaseData.plan ? (
                    <div className="space-y-3">
                        {(phaseData.plan.recommendations || phaseData.plan.interventions || []).map((item, idx) => (
                            <div
                                key={idx}
                                className="bg-white border border-sand/50 rounded-xl p-4 flex items-start gap-3 shadow-sm"
                            >
                                <div className="w-8 h-8 rounded-full bg-terracotta/10 flex items-center justify-center shrink-0 mt-0.5">
                                    <span className="text-sm font-bold text-terracotta">{idx + 1}</span>
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-stone-700">
                                        {item.activity || item.title || item.name || item.intervention || item}
                                    </p>
                                    {(item.reason || item.description) && (
                                        <p className="text-xs text-stone-500 mt-1">{item.reason || item.description}</p>
                                    )}
                                </div>
                                {(item.duration || item.confidence || item.score) && (
                                    <Badge className="bg-sage-light/30 text-sage-dark text-xs shrink-0">
                                        {item.duration || Math.round((item.confidence || item.score) * 100) + '%'}
                                    </Badge>
                                )}
                            </div>
                        ))}
                        {phaseData.plan.summary && (
                            <p className="text-sm text-stone-600 mt-3 bg-cream/50 rounded-xl p-3 border border-sand/30">
                                {phaseData.plan.summary}
                            </p>
                        )}
                    </div>
                ) : null}
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => setPhase(6)}
                    disabled={!phaseData.plan}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                >
                    <span className="flex items-center gap-2">Continue <ArrowRightIcon className="w-4 h-4" /></span>
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase6 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <CloudIcon className="w-6 h-6 text-terracotta" />
                    Wind Down
                </CardTitle>
            </CardHeader>
            <CardContent>
                {relaxMutation.isPending ? (
                    <div className="flex flex-col items-center py-12">
                        <Loader className="w-8 h-8 text-terracotta mb-3" />
                        <p className="text-stone-500 text-sm">Preparing your relaxation exercise...</p>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Breathing exercise */}
                        <BreathingExercise />

                        {/* Affirmation */}
                        {phaseData.relax?.affirmation && (
                            <div className="bg-gradient-to-br from-lavender-light/30 to-cream rounded-xl p-6 text-center border border-lavender-light/40">
                                <SparklesIcon className="w-6 h-6 text-lavender mx-auto mb-2" />
                                <p className="text-stone-700 italic font-display text-lg leading-relaxed">
                                    &ldquo;{phaseData.relax.affirmation}&rdquo;
                                </p>
                            </div>
                        )}

                        {phaseData.relax?.message && !phaseData.relax?.affirmation && (
                            <div className="bg-gradient-to-br from-lavender-light/30 to-cream rounded-xl p-6 text-center border border-lavender-light/40">
                                <SparklesIcon className="w-6 h-6 text-lavender mx-auto mb-2" />
                                <p className="text-stone-700 italic font-display text-lg leading-relaxed">
                                    &ldquo;{phaseData.relax.message}&rdquo;
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
            <CardFooter className="flex justify-end">
                <Button
                    onClick={() => setPhase(7)}
                    disabled={!phaseData.relax}
                    className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                >
                    <span className="flex items-center gap-2">Continue <ArrowRightIcon className="w-4 h-4" /></span>
                </Button>
            </CardFooter>
        </Card>
    );

    const renderPhase7 = () => (
        <Card className="rounded-2xl shadow-organic">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-stone-800">
                    <SparklesIcon className="w-6 h-6 text-terracotta" />
                    Session Summary
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {!phaseData.summary ? (
                    <>
                        {/* Final mood input */}
                        <div>
                            <label className="block text-sm font-medium text-stone-600 mb-2">
                                How are you feeling now? <span className="text-terracotta font-bold text-lg">{finalMood}</span>/10
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={finalMood}
                                onChange={(e) => setFinalMood(Number(e.target.value))}
                                className="w-full h-2 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-coral-light via-sand to-sage-light accent-terracotta"
                            />
                            <div className="flex justify-between text-xs text-stone-400 mt-1">
                                <span>Very Low</span>
                                <span>Neutral</span>
                                <span>Great</span>
                            </div>
                        </div>
                        <div className="flex justify-end">
                            <Button
                                onClick={() => completeMutation.mutate()}
                                disabled={completeMutation.isPending}
                                className="bg-terracotta hover:bg-terracotta-dark text-white px-6 py-2.5 rounded-xl font-medium"
                            >
                                {completeMutation.isPending ? (
                                    <span className="flex items-center gap-2"><Loader className="w-4 h-4" /> Completing...</span>
                                ) : (
                                    <span className="flex items-center gap-2">Complete Session <SparklesIcon className="w-4 h-4" /></span>
                                )}
                            </Button>
                        </div>
                    </>
                ) : (
                    <div className="space-y-5">
                        {/* Mood comparison */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-coral-light/10 border border-coral-light/30 rounded-xl p-4 text-center">
                                <p className="text-xs uppercase font-semibold text-stone-500 mb-1">Before</p>
                                <p className="text-3xl font-bold text-coral">{moodScore}</p>
                                <p className="text-xs text-stone-400">/10</p>
                            </div>
                            <div className="bg-sage-light/20 border border-sage-light/50 rounded-xl p-4 text-center">
                                <p className="text-xs uppercase font-semibold text-stone-500 mb-1">After</p>
                                <p className="text-3xl font-bold text-sage">{finalMood}</p>
                                <p className="text-xs text-stone-400">/10</p>
                            </div>
                        </div>

                        {/* Mood change indicator */}
                        <div className="text-center">
                            {finalMood > moodScore ? (
                                <Badge className="bg-sage-light/30 text-sage-dark px-4 py-1.5 text-sm">
                                    +{finalMood - moodScore} improvement
                                </Badge>
                            ) : finalMood < moodScore ? (
                                <Badge className="bg-coral-light/30 text-coral-dark px-4 py-1.5 text-sm">
                                    {finalMood - moodScore} change
                                </Badge>
                            ) : (
                                <Badge className="bg-sand/50 text-stone-600 px-4 py-1.5 text-sm">
                                    No change in mood
                                </Badge>
                            )}
                        </div>

                        {/* Journal / summary text */}
                        {phaseData.summary.summary?.auto_journal_entry && (
                            <div className="bg-cream/50 border border-sand/50 rounded-xl p-5">
                                <p className="text-xs uppercase font-semibold text-terracotta-dark mb-2">Session Journal</p>
                                <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
                                    {phaseData.summary.summary.auto_journal_entry}
                                </p>
                            </div>
                        )}

                        <div className="text-center pt-2">
                            <p className="text-sm text-stone-500">
                                Thank you for taking this time for yourself. Remember, every step counts.
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );

    // ── Phase renderer map ───────────────────────────────────────────────────
    const phaseRenderers = [
        renderPhase0, renderPhase1, renderPhase2, renderPhase3,
        renderPhase4, renderPhase5, renderPhase6, renderPhase7,
    ];

    return (
        <PageContainer>
            <div className="max-w-3xl mx-auto">
                {/* Page title */}
                <div className="mb-6">
                    <h1 className="text-2xl font-display font-bold text-stone-800">Guided Wellness Session</h1>
                    <p className="text-sm text-stone-500 mt-1">A structured journey toward clarity and calm</p>
                </div>

                {/* Progress indicator (shown after session starts) */}
                {phase > 0 && <ProgressBar currentPhase={phase} />}

                {/* Error alert */}
                {error && (
                    <Alert variant="destructive" className="mb-4 rounded-xl">
                        <ExclamationTriangleIcon className="w-4 h-4" />
                        <span>{error}</span>
                    </Alert>
                )}

                {/* Current phase content */}
                <div className="transition-all duration-300">
                    {phaseRenderers[phase]()}
                </div>
            </div>
        </PageContainer>
    );
}

export default TherapySession;
