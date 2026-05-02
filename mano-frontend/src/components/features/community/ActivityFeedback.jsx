import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submitActivityFeedback, getMyActivityFeedback, getActivityEffectiveness } from '../../../api/client';

// ─── Star Rating ────────────────────────────────────────────────────────────
function StarRating({ value, onChange, size = 'md', disabled = false }) {
    const [hover, setHover] = useState(0);
    const sizeClass = size === 'lg' ? 'text-3xl' : size === 'md' ? 'text-2xl' : 'text-lg';

    return (
        <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
                <button
                    key={star}
                    type="button"
                    disabled={disabled}
                    className={`${sizeClass} transition-all ${
                        disabled ? 'cursor-default' : 'cursor-pointer hover:scale-110'
                    }`}
                    onMouseEnter={() => !disabled && setHover(star)}
                    onMouseLeave={() => !disabled && setHover(0)}
                    onClick={() => !disabled && onChange?.(star)}
                >
                    {(hover || value) >= star ? '⭐' : '☆'}
                </button>
            ))}
        </div>
    );
}

// ─── Mood Selector ──────────────────────────────────────────────────────────
function MoodSelector({ label, value, onChange }) {
    const moods = [
        { value: 1, emoji: '😢', label: 'Very Bad' },
        { value: 2, emoji: '😕', label: 'Bad' },
        { value: 3, emoji: '😐', label: 'Okay' },
        { value: 4, emoji: '🙂', label: 'Good' },
        { value: 5, emoji: '😊', label: 'Great' },
    ];

    return (
        <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">{label}</p>
            <div className="flex gap-2">
                {moods.map((mood) => (
                    <button
                        key={mood.value}
                        type="button"
                        onClick={() => onChange(mood.value)}
                        className={`flex flex-col items-center gap-0.5 p-2 rounded-xl transition-all ${
                            value === mood.value
                                ? 'bg-primary-100 border-2 border-primary-400 scale-110'
                                : 'bg-neutral-50 border-2 border-transparent hover:bg-neutral-100'
                        }`}
                    >
                        <span className="text-xl">{mood.emoji}</span>
                        <span className="text-[10px] text-neutral-500">{mood.label}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}

// ─── Effectiveness Bar ──────────────────────────────────────────────────────
function EffectivenessBar({ data }) {
    if (!data || data.total_reviews === 0) return null;

    const pct = ((data.avg_effectiveness / 5) * 100);
    const color = data.avg_effectiveness >= 4 ? 'from-emerald-400 to-emerald-600'
        : data.avg_effectiveness >= 3 ? 'from-amber-400 to-amber-600'
        : 'from-red-400 to-red-600';

    return (
        <div className="bg-neutral-50 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Community Rating</span>
                <span className="text-sm font-bold text-neutral-700">
                    {data.avg_effectiveness}/5 ({data.total_reviews} reviews)
                </span>
            </div>
            <div className="w-full h-2 bg-neutral-200 rounded-full overflow-hidden">
                <div
                    className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-500`}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <div className="flex gap-4 text-xs text-neutral-500">
                {data.avg_mood_improvement !== null && (
                    <span>
                        Mood change: <span className={`font-semibold ${data.avg_mood_improvement > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {data.avg_mood_improvement > 0 ? '+' : ''}{data.avg_mood_improvement}
                        </span>
                    </span>
                )}
                {data.recommendation_rate !== null && (
                    <span>{data.recommendation_rate}% would recommend</span>
                )}
            </div>
        </div>
    );
}

// ─── Main Feedback Component ────────────────────────────────────────────────
export default function ActivityFeedback({ userId, activityId, activityName, onClose }) {
    const queryClient = useQueryClient();
    const [rating, setRating] = useState(0);
    const [moodBefore, setMoodBefore] = useState(null);
    const [moodAfter, setMoodAfter] = useState(null);
    const [note, setNote] = useState('');
    const [wouldRecommend, setWouldRecommend] = useState(null);
    const [submitted, setSubmitted] = useState(false);

    // Fetch existing feedback
    const { data: existingFeedback } = useQuery({
        queryKey: ['feedback', userId, activityId],
        queryFn: async () => {
            const { data, error } = await getMyActivityFeedback(userId, activityId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId && !!activityId,
    });

    // Fetch community effectiveness
    const { data: effectiveness } = useQuery({
        queryKey: ['effectiveness', activityId],
        queryFn: async () => {
            const { data, error } = await getActivityEffectiveness(activityId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!activityId,
    });

    // Pre-fill if existing feedback
    useEffect(() => {
        if (existingFeedback?.has_feedback) {
            setRating(existingFeedback.effectiveness_rating);
            setMoodBefore(existingFeedback.mood_before);
            setMoodAfter(existingFeedback.mood_after);
            setNote(existingFeedback.feedback_note || '');
            setWouldRecommend(existingFeedback.would_recommend);
        }
    }, [existingFeedback]);

    // Submit mutation
    const mutation = useMutation({
        mutationFn: async () => {
            const { data, error } = await submitActivityFeedback(userId, {
                activity_id: activityId,
                effectiveness_rating: rating,
                mood_before: moodBefore,
                mood_after: moodAfter,
                feedback_note: note || null,
                would_recommend: wouldRecommend,
            });
            if (error) throw new Error(error);
            return data;
        },
        onSuccess: () => {
            setSubmitted(true);
            queryClient.invalidateQueries({ queryKey: ['feedback', userId, activityId] });
            queryClient.invalidateQueries({ queryKey: ['effectiveness', activityId] });
        },
    });

    if (submitted) {
        return (
            <div className="bg-white rounded-2xl border border-neutral-200 p-6 text-center space-y-3">
                <div className="text-4xl">🎉</div>
                <h3 className="text-lg font-bold text-neutral-900">Thanks for your feedback!</h3>
                <p className="text-sm text-neutral-500">
                    Your rating helps the community discover the most effective activities.
                </p>
                {effectiveness && <EffectivenessBar data={effectiveness} />}
                {onClose && (
                    <button
                        onClick={onClose}
                        className="text-sm font-semibold text-primary-600 hover:text-primary-700 mt-2"
                    >
                        Close
                    </button>
                )}
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl border border-neutral-200 p-5 space-y-5">
            <div>
                <h3 className="text-sm font-bold text-neutral-900 uppercase tracking-wider">
                    Rate This Activity
                </h3>
                {activityName && (
                    <p className="text-sm text-neutral-500 mt-0.5">{activityName}</p>
                )}
            </div>

            {/* Community effectiveness preview */}
            {effectiveness && <EffectivenessBar data={effectiveness} />}

            {/* Star rating */}
            <div>
                <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                    How effective was this activity?
                </p>
                <StarRating value={rating} onChange={setRating} size="lg" />
                <p className="text-xs text-neutral-400 mt-1">
                    {rating === 0 && 'Tap a star to rate'}
                    {rating === 1 && 'Not helpful at all'}
                    {rating === 2 && 'Slightly helpful'}
                    {rating === 3 && 'Moderately helpful'}
                    {rating === 4 && 'Very helpful'}
                    {rating === 5 && 'Extremely helpful!'}
                </p>
            </div>

            {/* Mood before/after */}
            <div className="grid grid-cols-2 gap-4">
                <MoodSelector label="Mood Before" value={moodBefore} onChange={setMoodBefore} />
                <MoodSelector label="Mood After" value={moodAfter} onChange={setMoodAfter} />
            </div>

            {moodBefore && moodAfter && (
                <div className={`text-center text-sm font-semibold px-3 py-2 rounded-xl ${
                    moodAfter > moodBefore
                        ? 'bg-emerald-50 text-emerald-700'
                        : moodAfter === moodBefore
                            ? 'bg-neutral-50 text-neutral-600'
                            : 'bg-red-50 text-red-700'
                }`}>
                    {moodAfter > moodBefore && `Mood improved by +${moodAfter - moodBefore} points!`}
                    {moodAfter === moodBefore && 'Mood stayed the same'}
                    {moodAfter < moodBefore && `Mood dropped by ${moodBefore - moodAfter} points`}
                </div>
            )}

            {/* Would recommend */}
            <div>
                <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                    Would you recommend this to others?
                </p>
                <div className="flex gap-2">
                    {[
                        { value: 1, label: 'No', emoji: '👎' },
                        { value: 2, label: 'Maybe', emoji: '🤔' },
                        { value: 3, label: 'Yes!', emoji: '👍' },
                    ].map((opt) => (
                        <button
                            key={opt.value}
                            type="button"
                            onClick={() => setWouldRecommend(opt.value)}
                            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all ${
                                wouldRecommend === opt.value
                                    ? 'bg-primary-100 border-2 border-primary-400 text-primary-700'
                                    : 'bg-neutral-50 border-2 border-transparent text-neutral-600 hover:bg-neutral-100'
                            }`}
                        >
                            <span>{opt.emoji}</span> {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Optional note */}
            <div>
                <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                    Any thoughts? (optional)
                </p>
                <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="What did you like or what could be improved?"
                    className="w-full px-3 py-2 border border-neutral-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-400"
                    rows={2}
                    maxLength={500}
                />
            </div>

            {/* Submit */}
            <div className="flex gap-3">
                <button
                    onClick={() => mutation.mutate()}
                    disabled={rating === 0 || mutation.isPending}
                    className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${
                        rating === 0
                            ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
                            : 'bg-primary-600 text-white hover:bg-primary-700 shadow-sm'
                    }`}
                >
                    {mutation.isPending ? 'Submitting...' : existingFeedback?.has_feedback ? 'Update Feedback' : 'Submit Feedback'}
                </button>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="px-4 py-2.5 rounded-xl text-sm font-medium text-neutral-600 bg-neutral-100 hover:bg-neutral-200 transition-all"
                    >
                        Skip
                    </button>
                )}
            </div>

            {mutation.isError && (
                <p className="text-xs text-red-500">{mutation.error?.message}</p>
            )}
        </div>
    );
}
