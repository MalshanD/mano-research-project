import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submitMoodCheckIn, getCommunityMoodPulse, getMoodHistory } from '../../../api/client';

// ── Mood configuration ───────────────────────────────────────────────────────
const MOODS = [
    { key: 'great', emoji: '\uD83E\uDD29', label: 'Great', color: 'from-emerald-400 to-teal-500', bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-400' },
    { key: 'good', emoji: '\uD83D\uDE0A', label: 'Good', color: 'from-green-400 to-emerald-500', bg: 'bg-green-50', text: 'text-green-700', ring: 'ring-green-400' },
    { key: 'okay', emoji: '\uD83D\uDE10', label: 'Okay', color: 'from-amber-400 to-yellow-500', bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-400' },
    { key: 'low', emoji: '\uD83D\uDE14', label: 'Low', color: 'from-orange-400 to-rose-400', bg: 'bg-orange-50', text: 'text-orange-700', ring: 'ring-orange-400' },
    { key: 'bad', emoji: '\uD83D\uDE22', label: 'Bad', color: 'from-rose-400 to-red-500', bg: 'bg-rose-50', text: 'text-rose-700', ring: 'ring-rose-400' },
];

const MOOD_MAP = Object.fromEntries(MOODS.map((m) => [m.key, m]));

// ── Pulse Bar ────────────────────────────────────────────────────────────────
function PulseBar({ distribution, total }) {
    if (total === 0) return null;

    return (
        <div className="flex items-center gap-1 w-full h-3 rounded-full overflow-hidden bg-neutral-100">
            {MOODS.map((m) => {
                const pct = distribution?.[m.key]?.percentage || 0;
                if (pct === 0) return null;
                return (
                    <div
                        key={m.key}
                        className={`h-full bg-gradient-to-r ${m.color} transition-all duration-700 ease-out`}
                        style={{ width: `${pct}%` }}
                        title={`${m.label}: ${pct}%`}
                    />
                );
            })}
        </div>
    );
}

// ── Mini History Dots ────────────────────────────────────────────────────────
function MoodHistoryDots({ history }) {
    if (!history || history.length === 0) return null;

    // Show last 7 days
    const recent = history.slice(-7);

    return (
        <div className="flex items-center gap-1.5">
            <span className="text-xs text-neutral-400 mr-1">This week:</span>
            {recent.map((entry, i) => {
                const mood = MOOD_MAP[entry.mood];
                return (
                    <span
                        key={i}
                        className="text-sm cursor-default"
                        title={`${entry.date}: ${mood?.label || entry.mood}`}
                    >
                        {mood?.emoji || '\u2B55'}
                    </span>
                );
            })}
        </div>
    );
}

// ── Main Component ───────────────────────────────────────────────────────────
export default function MoodCheckIn({ userId }) {
    const queryClient = useQueryClient();
    const [selectedMood, setSelectedMood] = useState(null);
    const [showPulse, setShowPulse] = useState(false);
    const [justSubmitted, setJustSubmitted] = useState(false);

    // Fetch community mood pulse
    const { data: pulseData } = useQuery({
        queryKey: ['moodPulse', userId],
        queryFn: async () => {
            const { data, error } = await getCommunityMoodPulse(userId);
            if (error) return null;
            return data;
        },
        enabled: !!userId,
        refetchInterval: 60000, // Refresh every minute
    });

    // Fetch mood history
    const { data: historyData } = useQuery({
        queryKey: ['moodHistory', userId],
        queryFn: async () => {
            const { data, error } = await getMoodHistory(userId, 7);
            if (error) return null;
            return data;
        },
        enabled: !!userId,
    });

    // Set selected mood from pulse data (user's existing check-in)
    useEffect(() => {
        if (pulseData?.my_mood) {
            setSelectedMood(pulseData.my_mood);
            setShowPulse(true);
        }
    }, [pulseData?.my_mood]);

    // Submit mutation
    const submitMutation = useMutation({
        mutationFn: ({ userId, mood }) => submitMoodCheckIn(userId, mood),
        onSuccess: (result) => {
            if (result.data) {
                setShowPulse(true);
                setJustSubmitted(true);
                queryClient.invalidateQueries(['moodPulse', userId]);
                queryClient.invalidateQueries(['moodHistory', userId]);
                setTimeout(() => setJustSubmitted(false), 2000);
            }
        },
    });

    const handleMoodSelect = useCallback((moodKey) => {
        setSelectedMood(moodKey);
        submitMutation.mutate({ userId, mood: moodKey });
    }, [userId, submitMutation]);

    const alreadyCheckedIn = !!pulseData?.my_mood;
    const pulse = pulseData || {};
    const history = historyData?.history || [];

    return (
        <div className="rounded-2xl border border-neutral-200 bg-white overflow-hidden shadow-sm">
            {/* ── Header ── */}
            <div className="px-5 pt-4 pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-lg">{'\uD83D\uDC9C'}</span>
                        <h3 className="text-sm font-bold text-neutral-800">
                            {alreadyCheckedIn ? 'Today\'s Mood' : 'How are you feeling today?'}
                        </h3>
                    </div>
                    {alreadyCheckedIn && (
                        <button
                            onClick={() => setShowPulse((s) => !s)}
                            className="text-xs font-medium text-primary-600 hover:text-primary-700 transition"
                        >
                            {showPulse ? 'Change mood' : 'Community pulse'}
                        </button>
                    )}
                </div>
            </div>

            {/* ── Mood Selector ── */}
            {(!alreadyCheckedIn || !showPulse) && (
                <div className="px-5 pb-4">
                    <div className="flex items-center justify-between gap-2">
                        {MOODS.map((m) => {
                            const isSelected = selectedMood === m.key;
                            return (
                                <button
                                    key={m.key}
                                    onClick={() => handleMoodSelect(m.key)}
                                    disabled={submitMutation.isPending}
                                    className={`
                                        flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-xl transition-all duration-200
                                        ${isSelected
                                            ? `${m.bg} ring-2 ${m.ring} scale-110 shadow-md`
                                            : 'hover:bg-neutral-50 hover:scale-105'
                                        }
                                        ${submitMutation.isPending ? 'opacity-60 pointer-events-none' : ''}
                                    `}
                                >
                                    <span className={`text-2xl transition-transform duration-200 ${isSelected ? 'scale-110' : ''}`}>
                                        {m.emoji}
                                    </span>
                                    <span className={`text-xs font-medium ${isSelected ? m.text : 'text-neutral-500'}`}>
                                        {m.label}
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    {justSubmitted && (
                        <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-100 animate-fade-in">
                            <span>{'\u2705'}</span>
                            <span className="text-xs font-medium text-emerald-700">Check-in recorded! Thanks for sharing.</span>
                        </div>
                    )}
                </div>
            )}

            {/* ── Community Pulse ── */}
            {showPulse && pulse.total_checkins > 0 && (
                <div className="px-5 pb-4 space-y-3">
                    {/* Summary message */}
                    <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl bg-primary-50/50 border border-primary-100">
                        <span className="text-base mt-0.5">{'\uD83D\uDCCA'}</span>
                        <div>
                            <p className="text-sm font-medium text-primary-800">{pulse.message}</p>
                            <p className="text-xs text-primary-600 mt-0.5">
                                {pulse.total_checkins} of {pulse.total_members} members checked in
                                ({pulse.participation_rate}%)
                            </p>
                        </div>
                    </div>

                    {/* Distribution bar */}
                    <PulseBar distribution={pulse.distribution} total={pulse.total_checkins} />

                    {/* Legend */}
                    <div className="flex items-center justify-between px-1">
                        {MOODS.map((m) => {
                            const pct = pulse.distribution?.[m.key]?.percentage || 0;
                            return (
                                <div key={m.key} className="flex flex-col items-center gap-0.5">
                                    <span className="text-sm">{m.emoji}</span>
                                    <span className="text-xs text-neutral-500 font-medium">{pct}%</span>
                                </div>
                            );
                        })}
                    </div>

                    {/* History dots */}
                    {history.length > 0 && (
                        <div className="pt-2 border-t border-neutral-100">
                            <MoodHistoryDots history={history} />
                        </div>
                    )}
                </div>
            )}

            {/* ── Empty pulse state ── */}
            {showPulse && pulse.total_checkins === 0 && (
                <div className="px-5 pb-4">
                    <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-neutral-50 border border-neutral-100">
                        <span>{'\uD83C\uDF1F'}</span>
                        <p className="text-xs text-neutral-500">
                            No one in your community has checked in yet today. You were the first!
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
