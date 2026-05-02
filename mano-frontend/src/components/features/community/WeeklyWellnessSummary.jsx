import { useQuery } from '@tanstack/react-query';
import { cn } from '../../../utils/helpers';
import { getWeeklyWellnessSummary } from '../../../api/client';
import {
    ArrowTrendingUpIcon,
    ArrowTrendingDownIcon,
    MinusIcon,
    CalendarDaysIcon,
    FireIcon,
    SparklesIcon,
    ChatBubbleLeftEllipsisIcon,
    BookOpenIcon,
} from '@heroicons/react/24/outline';

// ─── Wellness Score Ring ─────────────────────────────────────────────────────
function ScoreRing({ score, size = 120 }) {
    const radius = (size - 16) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = (score / 100) * circumference;
    const remaining = circumference - progress;

    const color =
        score >= 70 ? 'text-success-500' :
        score >= 40 ? 'text-warning-500' :
        'text-crisis-500';

    const bgColor =
        score >= 70 ? 'text-success-100' :
        score >= 40 ? 'text-warning-100' :
        'text-crisis-100';

    const label =
        score >= 80 ? 'Excellent' :
        score >= 60 ? 'Good' :
        score >= 40 ? 'Fair' :
        score >= 20 ? 'Low' :
        'Needs Attention';

    return (
        <div className="flex flex-col items-center">
            <div className="relative" style={{ width: size, height: size }}>
                <svg
                    viewBox={`0 0 ${size} ${size}`}
                    className="transform -rotate-90"
                    style={{ width: size, height: size }}
                >
                    {/* Background circle */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        strokeWidth="10"
                        className={cn('stroke-current', bgColor)}
                    />
                    {/* Progress circle */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        strokeWidth="10"
                        strokeLinecap="round"
                        className={cn('stroke-current transition-all duration-1000', color)}
                        strokeDasharray={`${progress} ${remaining}`}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={cn('text-2xl font-bold', color)}>{Math.round(score)}</span>
                    <span className="text-[10px] text-neutral-400 font-medium uppercase tracking-wider">score</span>
                </div>
            </div>
            <span className={cn('text-xs font-semibold mt-1.5', color)}>{label}</span>
        </div>
    );
}

// ─── Delta Badge ─────────────────────────────────────────────────────────────
function DeltaBadge({ value, suffix = '' }) {
    if (value === null || value === undefined) return null;

    const isPositive = value > 0;
    const isNeutral = value === 0;

    return (
        <span
            className={cn(
                'inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full',
                isPositive && 'bg-success-50 text-success-700',
                isNeutral && 'bg-neutral-100 text-neutral-500',
                !isPositive && !isNeutral && 'bg-crisis-50 text-crisis-600'
            )}
        >
            {isPositive ? (
                <ArrowTrendingUpIcon className="w-3 h-3" />
            ) : isNeutral ? (
                <MinusIcon className="w-3 h-3" />
            ) : (
                <ArrowTrendingDownIcon className="w-3 h-3" />
            )}
            {isPositive && '+'}{value}{suffix}
        </span>
    );
}

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatItem({ icon, label, value, delta, deltaSuffix }) {
    return (
        <div className="flex items-center gap-3 py-2">
            <div className="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center text-primary-500 flex-shrink-0">
                {icon}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-xs text-neutral-500">{label}</p>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-800">{value}</span>
                    <DeltaBadge value={delta} suffix={deltaSuffix} />
                </div>
            </div>
        </div>
    );
}

// ─── Mood Mini Trend ─────────────────────────────────────────────────────────
function MoodMiniTrend({ trend = [] }) {
    if (trend.length === 0) return null;

    const MOOD_COLORS = {
        great: 'bg-success-400',
        good: 'bg-success-300',
        okay: 'bg-warning-300',
        low: 'bg-orange-300',
        bad: 'bg-crisis-400',
    };

    const MOOD_EMOJIS = {
        great: '😄',
        good: '🙂',
        okay: '😐',
        low: '😔',
        bad: '😢',
    };

    return (
        <div className="mt-3">
            <p className="text-xs text-neutral-400 font-medium mb-2">Mood This Week</p>
            <div className="flex gap-1.5">
                {trend.map((day, i) => (
                    <div key={i} className="flex flex-col items-center gap-1 flex-1">
                        <div
                            className={cn(
                                'w-full h-6 rounded-md flex items-center justify-center text-xs',
                                MOOD_COLORS[day.mood] || 'bg-neutral-200'
                            )}
                            title={`${day.date}: ${day.mood}`}
                        >
                            {MOOD_EMOJIS[day.mood] || ''}
                        </div>
                        <span className="text-[9px] text-neutral-400">
                            {new Date(day.date + 'T00:00:00').toLocaleDateString('en', { weekday: 'narrow' })}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Insight Card ────────────────────────────────────────────────────────────
function InsightItem({ insight }) {
    const bgMap = {
        positive: 'bg-success-50 border-success-100',
        celebration: 'bg-warning-50 border-warning-100',
        support: 'bg-primary-50 border-primary-100',
        neutral: 'bg-neutral-50 border-neutral-100',
        nudge: 'bg-accent-50 border-accent-100',
    };

    return (
        <div className={cn(
            'flex items-start gap-2.5 px-3 py-2.5 rounded-xl border',
            bgMap[insight.type] || bgMap.neutral
        )}>
            <span className="text-base flex-shrink-0 mt-0.5">{insight.icon}</span>
            <p className="text-xs text-neutral-700 leading-relaxed">{insight.text}</p>
        </div>
    );
}

// ─── Main Component ──────────────────────────────────────────────────────────
function WeeklyWellnessSummary({ userId, variant = 'full' }) {
    const { data: summary, isLoading, error } = useQuery({
        queryKey: ['wellnessSummary', userId],
        queryFn: async () => {
            const { data, error } = await getWeeklyWellnessSummary(userId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
        refetchInterval: 5 * 60 * 1000,
    });

    if (isLoading) {
        return (
            <div className="bg-white rounded-2xl border border-neutral-100 p-6">
                <div className="animate-pulse space-y-4">
                    <div className="h-4 bg-neutral-200 rounded w-1/3" />
                    <div className="h-24 bg-neutral-100 rounded-xl" />
                    <div className="h-3 bg-neutral-200 rounded w-2/3" />
                    <div className="h-3 bg-neutral-200 rounded w-1/2" />
                </div>
            </div>
        );
    }

    if (error || !summary) {
        return (
            <div className="bg-white rounded-2xl border border-neutral-100 p-6 text-center">
                <SparklesIcon className="w-8 h-8 text-neutral-300 mx-auto mb-2" />
                <p className="text-sm text-neutral-500">Your weekly summary will appear here once you start tracking.</p>
            </div>
        );
    }

    // ─── Compact variant (for sidebar/dashboard) ────────────────────────
    if (variant === 'compact') {
        return (
            <div className="bg-white rounded-2xl border border-neutral-100 p-4">
                <div className="flex items-center gap-2 mb-3">
                    <SparklesIcon className="w-4 h-4 text-primary-500" />
                    <h3 className="text-sm font-semibold text-neutral-800">Weekly Wellness</h3>
                </div>

                <div className="flex items-center gap-4">
                    <ScoreRing score={summary.wellness_score} size={80} />
                    <div className="flex-1 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-neutral-500">Mood checkins</span>
                            <span className="font-medium">{summary.mood.checkin_count}/7</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-neutral-500">Activities</span>
                            <span className="font-medium">{summary.engagement.activities_completed}</span>
                        </div>
                        {summary.journal?.entry_count > 0 && (
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-neutral-500">Journal entries</span>
                                <span className="font-medium">{summary.journal.entry_count}</span>
                            </div>
                        )}
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-neutral-500">Active days</span>
                            <span className="font-medium">{summary.engagement.active_days}/7</span>
                        </div>
                    </div>
                </div>

                {summary.insights?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-neutral-100">
                        <div className="flex items-start gap-2">
                            <span className="text-sm">{summary.insights[0].icon}</span>
                            <p className="text-xs text-neutral-600 leading-relaxed">{summary.insights[0].text}</p>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // ─── Full variant ───────────────────────────────────────────────────
    return (
        <div className="bg-white rounded-2xl border border-neutral-100 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-primary-50 to-accent-50 px-6 py-4 border-b border-neutral-100">
                <div className="flex items-center gap-2">
                    <SparklesIcon className="w-5 h-5 text-primary-500" />
                    <h2 className="text-base font-semibold text-neutral-800">Weekly Wellness Summary</h2>
                </div>
                <p className="text-xs text-neutral-500 mt-1">
                    {summary.period.start} to {summary.period.end}
                </p>
            </div>

            <div className="p-6 space-y-6">
                {/* Score + Stats Row */}
                <div className="flex gap-6">
                    {/* Score Ring */}
                    <ScoreRing score={summary.wellness_score} size={120} />

                    {/* Stats */}
                    <div className="flex-1 divide-y divide-neutral-100">
                        <StatItem
                            icon={<CalendarDaysIcon className="w-4 h-4" />}
                            label="Active Days"
                            value={`${summary.engagement.active_days} / 7`}
                            delta={summary.deltas?.active_days}
                        />
                        <StatItem
                            icon={<FireIcon className="w-4 h-4" />}
                            label="Activities Completed"
                            value={summary.engagement.activities_completed}
                            delta={summary.deltas?.activities_completed}
                        />
                        <StatItem
                            icon={<ChatBubbleLeftEllipsisIcon className="w-4 h-4" />}
                            label="Community Posts"
                            value={summary.engagement.posts_created}
                        />
                        {summary.journal && (
                            <StatItem
                                icon={<BookOpenIcon className="w-4 h-4" />}
                                label="Journal Entries"
                                value={summary.journal.entry_count}
                            />
                        )}
                    </div>
                </div>

                {/* Mood Mini Trend */}
                {summary.mood?.trend?.length > 0 && (
                    <MoodMiniTrend trend={summary.mood.trend} />
                )}

                {/* Mood Stats */}
                {summary.mood?.checkin_count > 0 && (
                    <div className="bg-neutral-50 rounded-xl px-4 py-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-neutral-500">Mood Average</p>
                                <p className="text-lg font-bold text-neutral-800">
                                    {summary.mood.avg_score} <span className="text-xs font-normal text-neutral-400">/ 5</span>
                                </p>
                            </div>
                            <DeltaBadge value={summary.deltas?.mood_score} suffix=" pts" />
                            {summary.mood.dominant_mood && (
                                <div className="text-center">
                                    <p className="text-xs text-neutral-500">Dominant Mood</p>
                                    <p className="text-sm font-semibold text-neutral-700 capitalize mt-0.5">
                                        {summary.mood.dominant_mood}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Activity Effectiveness */}
                {summary.feedback?.count > 0 && (
                    <div className="bg-neutral-50 rounded-xl px-4 py-3">
                        <p className="text-xs text-neutral-500 mb-1">Activity Effectiveness</p>
                        <div className="flex items-center gap-4">
                            <div>
                                <span className="text-lg font-bold text-neutral-800">
                                    {summary.feedback.avg_effectiveness}
                                </span>
                                <span className="text-xs text-neutral-400"> / 5 avg rating</span>
                            </div>
                            {summary.feedback.avg_mood_change !== 0 && (
                                <div className={cn(
                                    'text-xs font-medium px-2 py-1 rounded-full',
                                    summary.feedback.avg_mood_change > 0
                                        ? 'bg-success-50 text-success-700'
                                        : 'bg-crisis-50 text-crisis-600'
                                )}>
                                    {summary.feedback.avg_mood_change > 0 ? '+' : ''}{summary.feedback.avg_mood_change} mood change
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Journal Summary */}
                {summary.journal?.entry_count > 0 && (
                    <div className="bg-neutral-50 rounded-xl px-4 py-3">
                        <p className="text-xs text-neutral-500 mb-1">Thought Journal</p>
                        <div className="flex items-center gap-4 flex-wrap">
                            <div>
                                <span className="text-lg font-bold text-neutral-800">
                                    {summary.journal.entry_count}
                                </span>
                                <span className="text-xs text-neutral-400"> entries</span>
                            </div>
                            {summary.journal.distortions_found > 0 && (
                                <div className="text-xs font-medium px-2 py-1 rounded-full bg-warning-50 text-warning-700">
                                    {summary.journal.distortions_found} patterns found
                                </div>
                            )}
                            {summary.journal.helpful_reframes > 0 && (
                                <div className="text-xs font-medium px-2 py-1 rounded-full bg-success-50 text-success-700">
                                    {summary.journal.helpful_reframes} helpful reframes
                                </div>
                            )}
                            {summary.journal.top_distortion && (
                                <div className="text-xs text-neutral-500">
                                    Top pattern: <span className="font-medium capitalize">{summary.journal.top_distortion.replace(/_/g, ' ')}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Badges Earned This Week */}
                {summary.badges_earned?.length > 0 && (
                    <div>
                        <p className="text-xs text-neutral-400 font-medium mb-2">Badges Earned This Week</p>
                        <div className="flex flex-wrap gap-2">
                            {summary.badges_earned.map((badge, i) => (
                                <div
                                    key={i}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-warning-50 border border-warning-200 rounded-full"
                                >
                                    <span className="text-sm">{badge.icon}</span>
                                    <span className="text-xs font-medium text-warning-800">{badge.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Insights */}
                {summary.insights?.length > 0 && (
                    <div>
                        <p className="text-xs text-neutral-400 font-medium mb-2">Insights & Tips</p>
                        <div className="space-y-2">
                            {summary.insights.map((insight, i) => (
                                <InsightItem key={i} insight={insight} />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default WeeklyWellnessSummary;
