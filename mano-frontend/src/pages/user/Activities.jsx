import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { getActivityCategories, getActivityDetails, completeActivity, getUserActivities, getUserActivitiesByCategory, getCompletedActivities } from '../../api/client';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Button, Tabs, Badge, EmptyState, Alert, Modal, Loader, ConfirmModal } from '../../components/common';
import { ActivityCard, StreakBadges, ActivityFeedback, WeeklyWellnessSummary } from '../../components/features/community';
import { StatsCard } from '../../components/charts';
import { useAuth } from '../../contexts/AuthContext';
import {
    SparklesIcon,
    CheckCircleIcon,
    ClockIcon,
    FireIcon,
    FunnelIcon,
    TrophyIcon,
    LightBulbIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    PlayIcon,
    TagIcon,
    BeakerIcon,
    StarIcon,
    HeartIcon,
    BoltIcon,
    XMarkIcon,
} from '@heroicons/react/24/outline';

// Mock activities data
const mockActivities = [
    {
        id: 1,
        title: '5-Minute Breathing Exercise',
        description: 'A quick box breathing technique to help reduce stress and anxiety. Perfect for a midday reset.',
        category: 'mindfulness',
        duration: 5,
        difficulty: 'easy',
        benefits: ['Reduces stress', 'Improves focus', 'Calms anxiety'],
        completed: false,
    },
    {
        id: 2,
        title: 'Gratitude Journaling',
        description: 'Write down three things you\'re grateful for today. This simple practice can boost your mood and perspective.',
        category: 'cognitive',
        duration: 10,
        difficulty: 'easy',
        benefits: ['Boosts mood', 'Increases positivity', 'Builds resilience'],
        completed: true,
    },
    {
        id: 3,
        title: 'Mindful Nature Walk',
        description: 'Take a 20-minute walk outdoors while focusing on your senses. Notice colors, sounds, and sensations.',
        category: 'nature',
        duration: 20,
        difficulty: 'moderate',
        benefits: ['Physical exercise', 'Mental clarity', 'Stress relief'],
        completed: false,
    },
    {
        id: 4,
        title: 'Progressive Muscle Relaxation',
        description: 'Systematically tense and release muscle groups to reduce physical tension and promote relaxation.',
        category: 'relaxation',
        duration: 15,
        difficulty: 'easy',
        benefits: ['Reduces tension', 'Improves sleep', 'Decreases anxiety'],
        completed: false,
    },
    {
        id: 5,
        title: 'Creative Expression',
        description: 'Spend time drawing, painting, or crafting. No skills needed - just express yourself freely.',
        category: 'creative',
        duration: 30,
        difficulty: 'moderate',
        benefits: ['Self-expression', 'Stress relief', 'Mindfulness'],
        completed: true,
    },
    {
        id: 6,
        title: 'Social Connection Call',
        description: 'Call a friend or family member for a meaningful conversation. Human connection is vital for wellbeing.',
        category: 'social',
        duration: 15,
        difficulty: 'easy',
        benefits: ['Social support', 'Mood boost', 'Reduces isolation'],
        completed: false,
    },
    {
        id: 7,
        title: 'Body Scan Meditation',
        description: 'A guided meditation that involves focusing attention on different parts of your body.',
        category: 'mindfulness',
        duration: 20,
        difficulty: 'moderate',
        benefits: ['Body awareness', 'Stress reduction', 'Better sleep'],
        completed: false,
    },
    {
        id: 8,
        title: 'Sleep Hygiene Routine',
        description: 'Practice a calming bedtime routine: dim lights, avoid screens, and do a relaxation exercise.',
        category: 'sleep',
        duration: 30,
        difficulty: 'easy',
        benefits: ['Better sleep', 'Reduced anxiety', 'Morning energy'],
        completed: false,
    },
];

// ─── API Recommendation Card ─────────────────────────────────────────────────
const categoryIcons = {
    anxiety_relief: '😮‍💨',
    depression_relief: '💛',
    emotional: '❤️',
    mindfulness: '🌸',
    physical: '🏃',
    professional: '💼',
    routine: '📅',
    sleep: '😴',
    social: '👥',
    stress_relief: '🧘',
};

function formatCategoryLabel(id) {
    return id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const difficultyVariant = {
    easy: 'success',
    moderate: 'warning',
    challenging: 'accent',
};

const difficultyColor = {
    easy: 'from-sage to-sage-dark',
    moderate: 'from-terracotta-light to-terracotta',
    challenging: 'from-coral-light to-coral-dark',
};

// ─── Activity Detail Modal ────────────────────────────────────────────────────
function ActivityDetailModal({ isOpen, onClose, activityId, userId, onCompleted }) {
    const [detail, setDetail] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [completing, setCompleting] = useState(false);
    const [completed, setCompleted] = useState(false);
    const [completeError, setCompleteError] = useState(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [showFeedback, setShowFeedback] = useState(false);

    useEffect(() => {
        if (!isOpen || !activityId) return;
        setDetail(null);
        setError(null);
        setCompleted(false);
        setCompleteError(null);
        setConfirmOpen(false);
        setShowFeedback(false);
        setLoading(true);
        getActivityDetails(activityId).then(({ data, error: err }) => {
            if (err) setError(err);
            else setDetail(data);
            setLoading(false);
        });
    }, [isOpen, activityId]);

    const handleComplete = async () => {
        if (!userId) { setCompleteError('User not found. Please log in again.'); return; }
        setCompleting(true);
        setCompleteError(null);
        const { error: err } = await completeActivity(userId, activityId);
        setCompleting(false);
        setConfirmOpen(false);
        if (err) {
            setCompleteError(err);
        } else {
            setCompleted(true);
            onCompleted?.(activityId);
        }
    };

    const icon = detail ? (categoryIcons[detail.category] || '✨') : '✨';
    const diffGradient = detail ? (difficultyColor[detail.difficulty] || 'from-primary-400 to-accent-500') : 'from-primary-400 to-accent-500';
    const diffBadge = detail ? (difficultyVariant[detail.difficulty] || 'primary') : 'primary';

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="lg" showCloseButton={false}>
            {loading && (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                    <Loader size="lg" />
                    <p className="text-sm text-terracotta-light/70">Loading activity…</p>
                </div>
            )}

            {error && !loading && (
                <div className="py-10 text-center">
                    <p className="text-sm text-coral-dark">Failed to load activity details.</p>
                    <Button variant="ghost" size="sm" className="mt-3" onClick={onClose}>Close</Button>
                </div>
            )}

            {detail && !loading && (
                <div className="-m-6 overflow-hidden rounded-2xl">
                    {/* ── Gradient Header ── */}
                    <div className={`bg-gradient-to-br ${diffGradient} px-6 pt-6 pb-8 relative`}>
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 p-1.5 rounded-full bg-white/20 hover:bg-white/30 text-white transition"
                        >
                            <XMarkIcon className="w-4 h-4" />
                        </button>
                        <div className="flex items-start gap-4">
                            <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center text-4xl flex-shrink-0 shadow-lg">
                                {icon}
                            </div>
                            <div className="flex-1 min-w-0 pt-1">
                                <div className="flex flex-wrap items-center gap-2 mb-1">
                                    <span className="text-xs font-semibold uppercase tracking-widest text-white/70">
                                        {formatCategoryLabel(detail.category)}
                                    </span>
                                    {detail.scientific_backing && (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/20 text-white text-xs font-medium">
                                            <BeakerIcon className="w-3 h-3" /> Science-backed
                                        </span>
                                    )}
                                </div>
                                <h2 className="text-xl font-bold text-white leading-tight">{detail.name}</h2>
                                {/* Meta pills */}
                                <div className="flex flex-wrap items-center gap-3 mt-3">
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-white text-xs font-medium">
                                        <ClockIcon className="w-3.5 h-3.5" /> {detail.duration_minutes} min
                                    </span>
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-white text-xs font-medium capitalize">
                                        <BoltIcon className="w-3.5 h-3.5" /> {detail.difficulty}
                                    </span>
                                    {detail.effectiveness_score && (
                                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-white text-xs font-medium">
                                            <StarIcon className="w-3.5 h-3.5" /> {detail.effectiveness_score}% effective
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ── Body ── */}
                    <div className="px-6 py-5 space-y-5 bg-white">
                        {/* Description */}
                        <p className="text-sm text-neutral-600 leading-relaxed">{detail.description}</p>

                        {/* Step-by-step Instructions */}
                        {detail.instructions?.length > 0 && (
                            <div>
                                <h3 className="text-xs font-bold uppercase tracking-widest text-terracotta-light/70 mb-3">How to do it</h3>
                                <ol className="space-y-2.5">
                                    {detail.instructions.map((step, i) => (
                                        <li key={i} className="flex items-start gap-3">
                                            <span className={`flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br ${diffGradient} text-white text-xs font-bold flex items-center justify-center shadow-sm`}>
                                                {i + 1}
                                            </span>
                                            <span className="text-sm text-neutral-700 pt-0.5 leading-snug">{step}</span>
                                        </li>
                                    ))}
                                </ol>
                            </div>
                        )}

                        {/* Benefits */}
                        {detail.benefits?.length > 0 && (
                            <div>
                                <h3 className="text-xs font-bold uppercase tracking-widest text-terracotta-light/70 mb-3">Benefits</h3>
                                <div className="flex flex-wrap gap-2">
                                    {detail.benefits.map((b, i) => (
                                        <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-mint/40 text-sage-dark text-xs font-medium rounded-xl border border-sage-light/40">
                                            <HeartIcon className="w-3 h-3" />{b}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Target Conditions */}
                        {detail.target_conditions?.length > 0 && (
                            <div>
                                <h3 className="text-xs font-bold uppercase tracking-widest text-terracotta-light/70 mb-3">Helps with</h3>
                                <div className="flex flex-wrap gap-2">
                                    {detail.target_conditions.map((c, i) => (
                                        <span key={i} className="px-2.5 py-1 bg-cream text-terracotta-dark text-xs font-medium rounded-xl capitalize">
                                            {c.replace(/_/g, ' ')}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Tags */}
                        {detail.tags?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {detail.tags.map((tag, i) => (
                                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-cream text-terracotta-light text-xs rounded-xl">
                                        <TagIcon className="w-3 h-3" />#{tag}
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Footer Actions */}
                        <div className="flex items-center gap-3 pt-2 border-t border-sand/30">
                            {completed ? (
                                showFeedback ? null : (
                                    <div className="flex-1 space-y-2">
                                        <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-mint/30 border border-sage-light/40">
                                            <CheckCircleIcon className="w-5 h-5 text-sage-dark flex-shrink-0" />
                                            <span className="text-sm font-semibold text-sage-dark">Activity completed! Great work 🎉</span>
                                        </div>
                                        <button
                                            onClick={() => setShowFeedback(true)}
                                            className="w-full text-center text-xs font-semibold text-terracotta hover:text-terracotta-dark py-2 rounded-xl hover:bg-cream transition-colors"
                                        >
                                            Rate this activity & share your experience
                                        </button>
                                    </div>
                                )
                            ) : (
                                <Button
                                    variant="primary"
                                    className="flex-1"
                                    leftIcon={<CheckCircleIcon className="w-4 h-4" />}
                                    onClick={() => setConfirmOpen(true)}
                                    disabled={completing}
                                >
                                    Mark as Complete
                                </Button>
                            )}
                            {!showFeedback && <Button variant="outline" onClick={onClose}>Close</Button>}
                        </div>

                        {/* Feedback form after completion */}
                        {showFeedback && (
                            <div className="mt-4">
                                <ActivityFeedback
                                    userId={userId}
                                    activityId={activityId}
                                    activityName={detail?.name}
                                    onClose={() => setShowFeedback(false)}
                                />
                            </div>
                        )}

                        {completeError && (
                            <p className="text-xs text-coral-dark mt-1">{completeError}</p>
                        )}
                    </div>
                </div>
            )}

            <ConfirmModal
                isOpen={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                onConfirm={handleComplete}
                title="Mark as Complete?"
                message={`Have you completed "${detail?.name}"? This will be logged to your activity history.`}
                confirmText="Yes, Mark Complete"
                cancelText="Not Yet"
                variant="primary"
                loading={completing}
            />
        </Modal>
    );
}

function ApiActivityCard({ rec, onStartActivity, userId, isCompleted: alreadyDone }) {
    const [expanded, setExpanded] = useState(false);
    const [completing, setCompleting] = useState(false);
    const [completed, setCompleted] = useState(!!alreadyDone);
    const [completeError, setCompleteError] = useState(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const { activity, why_recommended } = rec;
    const icon = categoryIcons[activity.category] || '✨';
    const diffVariant = difficultyVariant[activity.difficulty] || 'primary';

    const handleMarkComplete = async () => {
        if (!userId) { setCompleteError('Not logged in'); return; }
        setCompleting(true);
        setCompleteError(null);
        const { error } = await completeActivity(userId, rec.activity_id);
        setCompleting(false);
        setConfirmOpen(false);
        if (error) setCompleteError(error);
        else setCompleted(true);
    };

    return (
        <Card>
            <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cream to-peach/40 flex items-center justify-center text-2xl flex-shrink-0">
                    {icon}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-neutral-900">{activity.name}</h3>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                            {completed && (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-mint/40 text-sage-dark text-xs font-semibold">
                                    <CheckCircleIcon className="w-3 h-3" /> Completed
                                </span>
                            )}
                            {activity.scientific_backing && (
                                <Badge variant="primary" size="sm">Science-backed</Badge>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                        <div className="flex items-center gap-1 text-neutral-500">
                            <ClockIcon className="w-4 h-4" />
                            <span className="text-sm">{activity.duration_minutes} min</span>
                        </div>
                        <Badge variant={diffVariant} size="sm">{activity.difficulty}</Badge>
                        {activity.effectiveness_score && (
                            <span className="text-xs text-neutral-400">⭐ {activity.effectiveness_score}% effective</span>
                        )}
                        {/* Component 4: cold-start flag — recommendation came from population
                            priors because the user's individual signal was too thin. */}
                        {rec.cold_start && (
                            <span
                                title="Cold-start: this recommendation uses population-level priors because your individual signal is still building up."
                                className="inline-flex items-center px-2 py-0.5 rounded-full bg-cream/60 text-terracotta-dark text-[11px] font-semibold border border-sand/40"
                            >
                                Starter pick
                            </span>
                        )}
                        {/* Component 4: MMR diversity rerank — present when diversity_lambda < 1. */}
                        {typeof rec.mmr_score === 'number' && (
                            <span
                                title={`MMR diversity score ${rec.mmr_score.toFixed(2)} — picked partly to broaden your set, not just maximise relevance.`}
                                className="inline-flex items-center px-2 py-0.5 rounded-full bg-mint/30 text-sage-dark text-[11px] font-semibold"
                            >
                                Diverse · {rec.mmr_score.toFixed(2)}
                            </span>
                        )}
                        {/* Component 4: MC-Dropout uncertainty band on the activity ranker. */}
                        {(rec.uncertainty?.std != null || rec.std != null) && (
                            <span
                                title={`Mean ${(rec.uncertainty?.mean ?? rec.mean ?? rec.score)?.toFixed?.(2)} ± std ${(rec.uncertainty?.std ?? rec.std)?.toFixed?.(2)} across ${rec.uncertainty?.n_samples ?? rec.n_samples ?? '?'} stochastic forward passes (MC-Dropout).`}
                                className="inline-flex items-center px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 text-[11px] font-semibold border border-primary-100"
                            >
                                ± {(rec.uncertainty?.std ?? rec.std).toFixed(2)}
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-neutral-600 mt-3">{activity.description}</p>
                    {why_recommended && (
                        <p className="text-xs text-terracotta italic mt-2">💡 {why_recommended}</p>
                    )}
                    {activity.benefits?.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                            {activity.benefits.map((b, i) => (
                                <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-mint/30 text-sage-dark text-xs rounded-xl">
                                    <SparklesIcon className="w-3 h-3" />{b}
                                </span>
                            ))}
                        </div>
                    )}
                    {activity.instructions?.length > 0 && (
                        <button
                            onClick={() => setExpanded((e) => !e)}
                            className="mt-3 flex items-center gap-1 text-xs font-semibold text-terracotta hover:text-terracotta-dark"
                        >
                            {expanded
                                ? <><ChevronUpIcon className="w-3.5 h-3.5" /> Hide steps</>
                                : <><ChevronDownIcon className="w-3.5 h-3.5" /> See steps</>}
                        </button>
                    )}
                    {expanded && activity.instructions?.length > 0 && (
                        <ol className="mt-2 ml-4 list-decimal space-y-1">
                            {activity.instructions.map((step, i) => (
                                <li key={i} className="text-xs text-neutral-600">{step}</li>
                            ))}
                        </ol>
                    )}
                    <div className="flex items-center gap-3 mt-4">
                        <Button
                            variant="primary"
                            size="sm"
                            leftIcon={<PlayIcon className="w-4 h-4" />}
                            onClick={() => onStartActivity?.(rec.activity_id)}
                        >
                            Start Activity
                        </Button>
                        {completed ? (
                            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-sage-dark">
                                <CheckCircleIcon className="w-4 h-4" /> Completed!
                            </span>
                        ) : (
                            <Button
                                variant="ghost"
                                size="sm"
                                leftIcon={<CheckCircleIcon className="w-4 h-4" />}
                                onClick={() => setConfirmOpen(true)}
                                disabled={completing}
                            >
                                Mark Complete
                            </Button>
                        )}
                    </div>
                    {completeError && (
                        <p className="text-xs text-coral-dark mt-1">{completeError}</p>
                    )}
                </div>
            </div>

            <ConfirmModal
                isOpen={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                onConfirm={handleMarkComplete}
                title="Mark as Complete?"
                message={`Have you completed "${activity.name}"? This will be logged to your activity history.`}
                confirmText="Yes, Mark Complete"
                cancelText="Not Yet"
                variant="primary"
                loading={completing}
            />
        </Card>
    );
}

// ─── Completed Activity Card ───────────────────────────────────────────────────
function CompletedActivityCard({ item }) {
    const act = item.activity_json;
    const icon = categoryIcons[act.category] || '✨';
    const diffVariant = difficultyVariant[act.difficulty] || 'primary';
    const lastDone = item.last_completed
        ? new Date(item.last_completed).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
        : null;

    return (
        <Card>
            <div className="flex items-start gap-4">
                <div className="relative flex-shrink-0">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-mint/40 to-sage-light/30 flex items-center justify-center text-2xl">
                        {icon}
                    </div>
                    <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-sage border-2 border-white flex items-center justify-center">
                        <CheckCircleIcon className="w-3 h-3 text-white" />
                    </span>
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-neutral-900">{act.name}</h3>
                        {act.scientific_backing && (
                            <Badge variant="primary" size="sm" className="flex-shrink-0">Science-backed</Badge>
                        )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 mt-1">
                        <div className="flex items-center gap-1 text-neutral-500">
                            <ClockIcon className="w-4 h-4" />
                            <span className="text-sm">{act.duration_minutes} min</span>
                        </div>
                        <Badge variant={diffVariant} size="sm">{act.difficulty}</Badge>
                        {act.effectiveness_score && (
                            <span className="text-xs text-neutral-400">⭐ {act.effectiveness_score}% effective</span>
                        )}
                    </div>
                    <p className="text-sm text-neutral-600 mt-2">{act.description}</p>
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-sand/30">
                        <div className="flex items-center gap-3">
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-mint/30 text-sage-dark text-xs font-semibold rounded-xl">
                                <FireIcon className="w-3.5 h-3.5" /> {item.count}x completed
                            </span>
                        </div>
                        {lastDone && (
                            <span className="text-xs text-neutral-400">Last: {lastDone}</span>
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}

function Activities() {
    const location = useLocation();
    const { user } = useAuth();
    const apiState = location.state || {};
    const apiRecommendations = apiState.recommendations || [];
    const hasApiResults = apiRecommendations.length > 0;
    const [activities, setActivities] = useState(mockActivities);
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [categories, setCategories] = useState([{ id: 'all', label: 'All', icon: '✨' }]);
    const [categoriesLoading, setCategoriesLoading] = useState(true);
    const [detailModal, setDetailModal] = useState({ open: false, activityId: null });
    const [userRecs, setUserRecs] = useState([]);
    const [recsMessage, setRecsMessage] = useState(null);
    const [recsLoading, setRecsLoading] = useState(true);
    const [recsError, setRecsError] = useState(null);
    const [completedItems, setCompletedItems] = useState([]);
    const [completedLoading, setCompletedLoading] = useState(true);
    const [completedError, setCompletedError] = useState(null);

    useEffect(() => {
        async function fetchCategories() {
            const { data, error } = await getActivityCategories();
            if (!error && data?.categories) {
                const apiCats = data.categories.map((id) => ({
                    id,
                    label: formatCategoryLabel(id),
                    icon: categoryIcons[id] || '✨',
                }));
                setCategories([{ id: 'all', label: 'All', icon: '✨' }, ...apiCats]);
            }
            setCategoriesLoading(false);
        }
        fetchCategories();
    }, []);

    useEffect(() => {
        if (!user?.id) return;
        setRecsLoading(true);
        setRecsError(null);
        const req = selectedCategory === 'all'
            ? getUserActivities(user.id)
            : getUserActivitiesByCategory(user.id, selectedCategory);
        req.then(({ data, error }) => {
            if (error) {
                setRecsError(error);
            } else if (selectedCategory === 'all') {
                // shape: { recommendations: [...], message }
                setUserRecs(data?.recommendations || []);
                setRecsMessage(data?.message || null);
            } else {
                // shape: { category, activities: [...] }
                // normalise to the same rec shape ApiActivityCard expects
                const normalised = (data?.activities || []).map((act) => ({
                    activity_id: act.id,
                    activity: act,
                    why_recommended: null,
                    matched_problems: [],
                    matched_conditions: [],
                }));
                setUserRecs(normalised);
                setRecsMessage(null);
            }
            setRecsLoading(false);
        });
    }, [user?.id, selectedCategory]);

    // Fetch completed activities
    useEffect(() => {
        if (!user?.id) return;
        setCompletedLoading(true);
        getCompletedActivities(user.id).then(({ data, error }) => {
            if (!error && Array.isArray(data)) setCompletedItems(data);
            setCompletedLoading(false);
        });
    }, [user?.id]);

    const completedCount = completedItems.length;
    const totalMinutes = completedItems.reduce(
        (sum, item) => sum + (item.activity_json?.duration_minutes || 0) * (item.count || 1), 0
    );

    // Compute streak: consecutive days ending today that have at least one completion
    const currentStreak = (() => {
        if (!completedItems.length) return 0;
        const days = new Set(
            completedItems.map((item) =>
                item.last_completed ? item.last_completed.slice(0, 10) : null
            ).filter(Boolean)
        );
        let streak = 0;
        const today = new Date();
        for (let i = 0; i <= 365; i++) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            const key = d.toISOString().slice(0, 10);
            if (days.has(key)) streak++;
            else if (i > 0) break; // allow today to be missed, stop on first gap after day 0
        }
        return streak;
    })();

    const handleStart = (activity) => {};

    const handleStartActivity = (activityId) => {
        setDetailModal({ open: true, activityId });
    };

    const handleActivityCompleted = (activityId) => {
        setTimeout(() => setDetailModal({ open: false, activityId: null }), 1800);
        // refresh completed list
        if (user?.id) {
            getCompletedActivities(user.id).then(({ data }) => {
                if (Array.isArray(data)) setCompletedItems(data);
            });
        }
    };

    const handleComplete = (activity) => {
        setActivities((prev) =>
            prev.map((a) =>
                a.id === activity.id ? { ...a, completed: true } : a
            )
        );
    };

    const tabs = [
        {
            id: 'recommended',
            label: 'Recommended',
            content: (
                <div className="space-y-4">

                    {/* ── Assessment label (only the label, no duplicate list) ── */}
                    {hasApiResults && (
                        <div className="flex items-center gap-2">
                            <SparklesIcon className="w-4 h-4 text-terracotta" />
                            <span className="text-sm font-bold text-terracotta-dark">
                                Personalised for You — {apiState.assessmentLabel || 'Your Assessment'}
                            </span>
                        </div>
                    )}

                    {/* ── Daily Recommendations from API ── */}
                    {recsMessage && (
                        <div className="flex items-start gap-2 px-3 py-2.5 rounded-2xl bg-cream border border-sand/40 mb-2">
                            <LightBulbIcon className="w-4 h-4 text-terracotta mt-0.5 flex-shrink-0" />
                            <p className="text-sm text-terracotta-dark">{recsMessage}</p>
                        </div>
                    )}

                    {/* Category Filter */}
                    <div className="flex flex-wrap gap-2">
                        {categoriesLoading ? (
                            <span className="text-sm text-neutral-400 italic">Loading categories…</span>
                        ) : (
                            categories.map((cat) => (
                                <button
                                    key={cat.id}
                                    onClick={() => setSelectedCategory(cat.id)}
                                    className={cn(
                                        'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all',
                                        selectedCategory === cat.id
                                            ? 'bg-cream text-terracotta shadow-organic'
                                            : 'bg-sand/20 text-neutral-600 hover:bg-cream/60'
                                    )}
                                >
                                    <span>{cat.icon}</span>
                                    {cat.label}
                                </button>
                            ))
                        )}
                    </div>

                    {/* Activities List */}
                    {recsLoading ? (
                        <div className="flex flex-col items-center justify-center py-16 gap-3">
                            <Loader size="lg" />
                            <p className="text-sm text-neutral-400">Loading your activities…</p>
                        </div>
                    ) : recsError ? (
                        <Alert variant="error">
                            <p className="text-sm">Could not load activities: {recsError}</p>
                        </Alert>
                    ) : userRecs.length === 0 ? (
                        <EmptyState
                            icon={<SparklesIcon className="w-8 h-8" />}
                            title="No activities found"
                            description="Try selecting a different category."
                        />
                    ) : (
                        <div className="flex flex-col gap-3">
                            {userRecs.map((rec) => (
                                <ApiActivityCard
                                    key={rec.activity_id}
                                    rec={rec}
                                    onStartActivity={handleStartActivity}
                                    userId={user?.id}
                                    isCompleted={completedItems.some((c) => c.activity_id === rec.activity_id)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            ),
        },
        {
            id: 'completed',
            label: 'Completed',
            badge: completedCount > 0 ? completedCount : undefined,
            content: (
                <div className="space-y-4">
                    {completedLoading ? (
                        <div className="flex flex-col items-center justify-center py-16 gap-3">
                            <Loader size="lg" />
                            <p className="text-sm text-neutral-400">Loading completed activities…</p>
                        </div>
                    ) : completedError ? (
                        <Alert variant="error">
                            <p className="text-sm">Could not load completed activities: {completedError}</p>
                        </Alert>
                    ) : completedItems.length === 0 ? (
                        <EmptyState
                            icon={<CheckCircleIcon className="w-8 h-8" />}
                            title="No completed activities"
                            description="Start an activity to track your progress"
                        />
                    ) : (
                        <div className="flex flex-col gap-3">
                            {completedItems.map((item) => (
                                <CompletedActivityCard key={item.id} item={item} />
                            ))}
                        </div>
                    )}
                </div>
            ),
        },
        {
            id: 'streaks',
            id: 'streaks',
            label: 'Streaks & Badges',
            icon: <TrophyIcon className="w-4 h-4" />,
            content: (
                <StreakBadges userId={user?.id} variant="full" />
            ),
        },
        {
            id: 'wellness',
            label: 'Weekly Summary',
            icon: <SparklesIcon className="w-4 h-4" />,
            content: (
                <WeeklyWellnessSummary userId={user?.id} variant="full" />
            ),
        },
    ];

    return (
        <PageContainer
            title="Wellness Activities"
            subtitle="Personalized activities to support your mental health journey"
        >
            {/* Stats Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <StatsCard
                    title="Activities Completed"
                    value={completedCount}
                    icon={<CheckCircleIcon className="w-6 h-6" />}
                    color="success"
                    loading={completedLoading}
                />
                <StatsCard
                    title="Total Minutes"
                    value={totalMinutes}
                    suffix=" min"
                    icon={<ClockIcon className="w-6 h-6" />}
                    color="primary"
                    loading={completedLoading}
                />
                <StatsCard
                    title="Current Streak"
                    value={currentStreak}
                    suffix=" days"
                    icon={<FireIcon className="w-6 h-6" />}
                    color="accent"
                    loading={completedLoading}
                />
            </div>

            {/* Main Content */}
            <Tabs tabs={tabs} defaultTab="recommended" variant="pills" />

            {/* Activity Detail Modal */}
            <ActivityDetailModal
                isOpen={detailModal.open}
                activityId={detailModal.activityId}
                userId={user?.id}
                onCompleted={handleActivityCompleted}
                onClose={() => setDetailModal({ open: false, activityId: null })}
            />
        </PageContainer>
    );
}

// Helper
function cn(...classes) {
    return classes.filter(Boolean).join(' ');
}

export default Activities;
