import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getUserStreaks, getUserBadges } from '../../../api/client';

// ─── Icon map for badges ────────────────────────────────────────────────────
const badgeIcons = {
    fire: '🔥',
    sparkles: '✨',
    'check-circle': '✅',
    trophy: '🏆',
    chat: '💬',
    users: '🦋',
    heart: '💜',
    compass: '🧭',
    crown: '👑',
};

const tierColors = {
    bronze: { bg: 'bg-amber-100', border: 'border-amber-300', text: 'text-amber-800', glow: 'shadow-amber-200' },
    silver: { bg: 'bg-slate-100', border: 'border-slate-300', text: 'text-slate-700', glow: 'shadow-slate-200' },
    gold: { bg: 'bg-yellow-100', border: 'border-yellow-400', text: 'text-yellow-800', glow: 'shadow-yellow-200' },
    platinum: { bg: 'bg-violet-100', border: 'border-violet-400', text: 'text-violet-800', glow: 'shadow-violet-200' },
};

// ─── Streak Fire Display ────────────────────────────────────────────────────
function StreakFire({ currentStreak, longestStreak }) {
    const flames = currentStreak >= 30 ? '🔥🔥🔥' : currentStreak >= 14 ? '🔥🔥' : currentStreak >= 3 ? '🔥' : '';

    return (
        <div className="flex items-center gap-4">
            <div className="relative">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-3xl ${
                    currentStreak > 0
                        ? 'bg-gradient-to-br from-orange-100 to-red-100 border-2 border-orange-200'
                        : 'bg-neutral-100 border-2 border-neutral-200'
                }`}>
                    {currentStreak > 0 ? '🔥' : '💤'}
                </div>
                {currentStreak > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[22px] h-[22px] flex items-center justify-center rounded-full bg-orange-500 text-white text-xs font-bold px-1 shadow-md">
                        {currentStreak}
                    </span>
                )}
            </div>
            <div className="flex-1">
                <div className="flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold text-neutral-900">{currentStreak}</span>
                    <span className="text-sm text-neutral-500">day streak {flames}</span>
                </div>
                <p className="text-xs text-neutral-400 mt-0.5">
                    {currentStreak === 0
                        ? 'Complete an activity to start your streak!'
                        : currentStreak >= longestStreak
                            ? "You're at your best streak ever!"
                            : `Best: ${longestStreak} days`}
                </p>
            </div>
        </div>
    );
}

// ─── Activity Heatmap ───────────────────────────────────────────────────────
function Heatmap({ data }) {
    const intensityColors = [
        'bg-neutral-100',       // 0 — no activity
        'bg-emerald-200',       // 1
        'bg-emerald-300',       // 2
        'bg-emerald-400',       // 3
        'bg-emerald-500',       // 4
        'bg-emerald-600',       // 5+
    ];

    return (
        <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Last 14 Days</p>
            <div className="flex gap-1 flex-wrap">
                {data.map((day, i) => (
                    <div
                        key={day.date}
                        className={`w-6 h-6 rounded-md ${intensityColors[Math.min(day.intensity, 5)]} ${
                            day.is_today ? 'ring-2 ring-primary-400 ring-offset-1' : ''
                        } transition-all hover:scale-110`}
                        title={`${day.date}: ${day.intensity} activities`}
                    />
                ))}
            </div>
            <div className="flex items-center gap-1 mt-1.5">
                <span className="text-[10px] text-neutral-400">Less</span>
                {[0, 1, 2, 3, 4, 5].map((level) => (
                    <div key={level} className={`w-3 h-3 rounded-sm ${intensityColors[level]}`} />
                ))}
                <span className="text-[10px] text-neutral-400">More</span>
            </div>
        </div>
    );
}

// ─── Weekly Stats Bar ───────────────────────────────────────────────────────
function WeeklyStats({ week }) {
    const progress = (week.active_days / 7) * 100;

    return (
        <div>
            <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">This Week</p>
                <span className="text-xs text-neutral-400">{week.active_days}/7 days</span>
            </div>
            <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                />
            </div>
            <div className="flex gap-4 mt-2">
                <span className="text-xs text-neutral-500">
                    <span className="font-semibold text-neutral-700">{week.activities_completed}</span> activities
                </span>
                <span className="text-xs text-neutral-500">
                    <span className="font-semibold text-neutral-700">{week.posts_created}</span> posts
                </span>
                <span className="text-xs text-neutral-500">
                    <span className="font-semibold text-neutral-700">{week.moods_logged}</span> mood logs
                </span>
            </div>
        </div>
    );
}

// ─── Badge Card ─────────────────────────────────────────────────────────────
function BadgeCard({ badge, compact = false }) {
    const tier = tierColors[badge.tier] || tierColors.bronze;
    const icon = badgeIcons[badge.icon] || '⭐';

    if (compact) {
        return (
            <div
                className={`relative flex items-center justify-center w-10 h-10 rounded-xl border-2 ${
                    badge.earned
                        ? `${tier.bg} ${tier.border} shadow-sm ${tier.glow}`
                        : 'bg-neutral-50 border-neutral-200 opacity-40 grayscale'
                } transition-all hover:scale-110`}
                title={`${badge.name}${badge.earned ? '' : ' (Locked)'}`}
            >
                <span className="text-lg">{icon}</span>
            </div>
        );
    }

    return (
        <div className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
            badge.earned
                ? `${tier.bg} ${tier.border} shadow-sm`
                : 'bg-neutral-50 border-neutral-200 opacity-50'
        }`}>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${
                badge.earned ? '' : 'grayscale'
            }`}>
                {icon}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${badge.earned ? tier.text : 'text-neutral-400'}`}>
                        {badge.name}
                    </span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                        badge.earned ? `${tier.bg} ${tier.text}` : 'bg-neutral-100 text-neutral-400'
                    }`}>
                        {badge.tier}
                    </span>
                </div>
                <p className="text-xs text-neutral-500 mt-0.5">{badge.description}</p>
                {badge.earned && badge.earned_at && (
                    <p className="text-[10px] text-neutral-400 mt-0.5">
                        Earned {new Date(badge.earned_at).toLocaleDateString()}
                    </p>
                )}
            </div>
            {badge.earned && <span className="text-lg">✓</span>}
        </div>
    );
}

// ─── Main StreakBadges Component ─────────────────────────────────────────────
export default function StreakBadges({ userId, variant = 'full' }) {
    const [showAllBadges, setShowAllBadges] = useState(false);

    const { data: streakData } = useQuery({
        queryKey: ['streaks', userId],
        queryFn: async () => {
            const { data, error } = await getUserStreaks(userId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        refetchInterval: 60000,
    });

    const { data: badgeData } = useQuery({
        queryKey: ['badges', userId],
        queryFn: async () => {
            const { data, error } = await getUserBadges(userId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        refetchInterval: 60000,
    });

    if (!streakData && !badgeData) {
        return (
            <div className="bg-white rounded-2xl border border-neutral-200 p-5 animate-pulse">
                <div className="h-16 bg-neutral-100 rounded-xl" />
            </div>
        );
    }

    // ─── Compact variant: sidebar widget ─────────────────────
    if (variant === 'compact') {
        return (
            <div className="bg-white rounded-2xl border border-neutral-200 p-4 space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-neutral-900">Your Streaks</h3>
                    {streakData?.current_streak > 0 && (
                        <span className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">
                            🔥 {streakData.current_streak}d
                        </span>
                    )}
                </div>
                {streakData && (
                    <StreakFire
                        currentStreak={streakData.current_streak}
                        longestStreak={streakData.longest_streak}
                    />
                )}
                {badgeData?.earned_badges?.length > 0 && (
                    <div>
                        <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                            Badges ({badgeData.total_earned}/{badgeData.total_available})
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                            {badgeData.earned_badges.slice(0, 8).map((badge) => (
                                <BadgeCard key={badge.badge_type} badge={badge} compact />
                            ))}
                            {badgeData.earned_badges.length > 8 && (
                                <div className="w-10 h-10 rounded-xl bg-neutral-100 border-2 border-neutral-200 flex items-center justify-center text-xs font-bold text-neutral-400">
                                    +{badgeData.earned_badges.length - 8}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // ─── Full variant: Activities page ───────────────────────
    const earnedBadges = badgeData?.earned_badges || [];
    const lockedBadges = badgeData?.locked_badges || [];
    const displayBadges = showAllBadges
        ? [...earnedBadges, ...lockedBadges]
        : earnedBadges.length > 0
            ? earnedBadges
            : lockedBadges.slice(0, 4);

    return (
        <div className="space-y-4">
            {/* Streak + Heatmap Card */}
            <div className="bg-white rounded-2xl border border-neutral-200 p-5 space-y-5">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-neutral-900 uppercase tracking-wider">Activity Streak</h3>
                    {streakData && (
                        <span className="text-xs text-neutral-400">
                            {streakData.total_active_days} total active days
                        </span>
                    )}
                </div>

                {streakData && (
                    <>
                        <StreakFire
                            currentStreak={streakData.current_streak}
                            longestStreak={streakData.longest_streak}
                        />
                        <WeeklyStats week={streakData.week} />
                        {streakData.heatmap && <Heatmap data={streakData.heatmap} />}
                    </>
                )}
            </div>

            {/* Badges Card */}
            <div className="bg-white rounded-2xl border border-neutral-200 p-5 space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-neutral-900 uppercase tracking-wider">
                        Achievement Badges
                    </h3>
                    {badgeData && (
                        <span className="text-xs font-bold text-primary-600 bg-primary-50 px-2.5 py-1 rounded-full">
                            {badgeData.total_earned}/{badgeData.total_available}
                        </span>
                    )}
                </div>

                {/* Progress bar */}
                {badgeData && (
                    <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-amber-400 via-yellow-400 to-emerald-400 rounded-full transition-all duration-500"
                            style={{ width: `${(badgeData.total_earned / badgeData.total_available) * 100}%` }}
                        />
                    </div>
                )}

                {/* Badge grid */}
                <div className="space-y-2">
                    {displayBadges.map((badge) => (
                        <BadgeCard key={badge.badge_type} badge={badge} />
                    ))}
                </div>

                {/* Show all toggle */}
                {lockedBadges.length > 0 && (
                    <button
                        onClick={() => setShowAllBadges(!showAllBadges)}
                        className="w-full text-center text-xs font-semibold text-primary-600 hover:text-primary-700 py-2 rounded-lg hover:bg-primary-50 transition-colors"
                    >
                        {showAllBadges
                            ? 'Show earned only'
                            : `Show all badges (${lockedBadges.length} locked)`}
                    </button>
                )}

                {earnedBadges.length === 0 && !showAllBadges && (
                    <p className="text-center text-sm text-neutral-400 py-2">
                        Complete activities and engage with the community to earn badges!
                    </p>
                )}
            </div>
        </div>
    );
}
