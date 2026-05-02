import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Button } from '../../components/common';
import { TrendChart, StatsCard, MoodCalendar } from '../../components/charts';
import {
    WelcomeCard,
    QuickActions,
    RecentActivity,
    UpcomingActivities,
    AmbientAudioWidget,
} from '../../components/features/dashboard';
import { RiskOverview } from '../../components/features/predictions';
import { ClusterBadge, WeeklyWellnessSummary } from '../../components/features/community';
import { CrisisModal, EmergencyBanner, CrisisSafetyBanner } from '../../components/features/crisis';
import { useAuth } from '../../contexts/AuthContext';
import assessmentService from '../../services/assessmentService';
import {
    getCompletedActivities,
    getUserActivities,
    getUserCommunity,
    getCommunityFeed,
    getDashboardContent,
    searchAmbientSounds,
} from '../../api/client';
import {
    ChartBarIcon,
    ChatBubbleLeftRightIcon,
    UserGroupIcon,
    CalendarIcon,
    ArrowRightIcon,
    ArrowTrendingUpIcon,
    SunIcon,
    HeartIcon,
} from '@heroicons/react/24/outline';

// ─── score normalisation constants ──────────────────────────────────────────
// All three scores are produced by the ML predictor on a 0–100 scale
// (not clinical PHQ-9/GAD-7/PSS-10 scales).
const SCORE_MAX = 100;

// Map a raw risk_level string → 'LOW' | 'MEDIUM' | 'HIGH'
function normRisk(level) {
    if (!level) return 'LOW';
    const u = level.toUpperCase();
    if (u === 'HIGH' || u === 'SEVERE') return 'HIGH';
    if (u === 'MEDIUM' || u === 'MODERATE') return 'MEDIUM';
    return 'LOW';
}

// Derive an overall risk from the three individual levels
function overallRisk(stress, anxiety, depression) {
    const order = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    const highest = [stress, anxiety, depression].reduce((acc, r) => {
        return (order[normRisk(r)] || 0) > (order[acc] || 0) ? normRisk(r) : acc;
    }, 'LOW');
    return highest;
}

function Dashboard() {
    const { user } = useAuth();
    const userId = user?.id;
    const [showCrisisModal, setShowCrisisModal] = useState(false);
    const [showEmergencyBanner, setShowEmergencyBanner] = useState(false);

    // ── Latest assessment scores ─────────────────────────────────────────────
    const { data: latestAssessment } = useQuery({
        queryKey: ['latestAssessment', userId],
        queryFn: () => assessmentService.getLatest(userId),
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
    });

    // ── Assessment history (trend + mood) ────────────────────────────────────
    const { data: assessmentHistory = [] } = useQuery({
        queryKey: ['assessmentHistory', userId],
        queryFn: () => assessmentService.getHistory(userId),
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
    });

    // ── Completed activities ─────────────────────────────────────────────────
    const { data: completedActivities = [] } = useQuery({
        queryKey: ['completedActivities', userId],
        queryFn: () => getCompletedActivities(userId),
        select: (res) => res.data ?? [],
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
    });

    // ── Recommended activities ───────────────────────────────────────────────
    const { data: recommendedActivities = {} } = useQuery({
        queryKey: ['userActivities', userId],
        queryFn: () => getUserActivities(userId),
        select: (res) => res.data ?? {},
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
    });

    // ── Community / cluster ──────────────────────────────────────────────────
    const { data: myCommunity } = useQuery({
        queryKey: ['userCommunity', userId],
        queryFn: () => getUserCommunity(userId),
        select: (res) => res.data ?? null,
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
    });

    // ── Community feed (latest posts) ────────────────────────────────────────
    // Uses the same queryKey as useCommunity so both share the cached result.
    // queryFn MUST match useCommunity exactly — normalization inside queryFn, no select.
    const { data: communityFeed = [] } = useQuery({
        queryKey: ['communityFeed', userId],
        queryFn: async () => {
            if (!userId) return [];
            const { data, error } = await getCommunityFeed(userId);
            if (error) throw new Error(error);
            return (data || []).map((p) => {
                const nameParts = (p.author_name || `User ${p.author_id}`).split(' ');
                return {
                    id: p.id,
                    type: p.post_type,
                    content: p.paragraph,
                    timestamp: p.created_at,
                    likes: p.likes ?? 0,
                    comments: p.comments ?? 0,
                    isLiked: false,
                    author: {
                        id: p.author_id,
                        firstName: nameParts[0] || '',
                        lastName: nameParts.slice(1).join(' ') || '',
                        avatar: null,
                        status: 'online',
                    },
                };
            });
        },
        enabled: !!userId,
        staleTime: 2 * 60 * 1000,
    });

    // ── Daily affirmation & quote ─────────────────────────────────────────────
    const { data: dashboardContent } = useQuery({
        queryKey: ['dashboardContent'],
        queryFn: () => getDashboardContent(),
        select: (res) => res.data ?? null,
        staleTime: 30 * 60 * 1000, // refresh every 30 min
    });

    // ── Ambient Sounds ────────────────────────────────────────────────────────
    const { data: ambientSounds } = useQuery({
        queryKey: ['ambientSounds'],
        queryFn: () => searchAmbientSounds('calm'),
        select: (res) => res.data ?? null,
        staleTime: 60 * 60 * 1000, // refresh every hour
    });

    // ── Derived: risk scores ─────────────────────────────────────────────────
    const stressScore = latestAssessment?.PSS10
        ? (latestAssessment.PSS10.score ?? 0) / SCORE_MAX
        : null;
    const depressionScore = latestAssessment?.PHQ9
        ? (latestAssessment.PHQ9.score ?? 0) / SCORE_MAX
        : null;
    const anxietyScore = latestAssessment?.GAD7
        ? (latestAssessment.GAD7.score ?? 0) / SCORE_MAX
        : null;

    const riskLevel = overallRisk(
        latestAssessment?.PSS10?.risk_level,
        latestAssessment?.GAD7?.risk_level,
        latestAssessment?.PHQ9?.risk_level,
    );

    const lastUpdated = latestAssessment?.PSS10?.completedAt
        || latestAssessment?.PHQ9?.completedAt
        || latestAssessment?.GAD7?.completedAt;

    // ── Derived: trend chart data from history ───────────────────────────────
    const trendData = useMemo(() => {
        if (!assessmentHistory.length) return [];
        return assessmentHistory
            .slice()
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            .slice(-30)
            .map((entry) => ({
                date: format(new Date(entry.created_at), 'MMM d'),
                stress: entry.stress ? (entry.stress.score ?? 0) / SCORE_MAX : 0,
                depression: entry.depression ? (entry.depression.score ?? 0) / SCORE_MAX : 0,
                anxiety: entry.anxiety ? (entry.anxiety.score ?? 0) / SCORE_MAX : 0,
            }));
    }, [assessmentHistory]);

    // ── Derived: mood calendar from history ──────────────────────────────────
    const moodData = useMemo(() => {
        if (!assessmentHistory.length) return [];
        return assessmentHistory.map((entry) => {
            const s = entry.stress ? 1 - (entry.stress.score ?? 0) / SCORE_MAX : 0.5;
            const a = entry.anxiety ? 1 - (entry.anxiety.score ?? 0) / SCORE_MAX : 0.5;
            const d = entry.depression ? 1 - (entry.depression.score ?? 0) / SCORE_MAX : 0.5;
            return {
                date: entry.created_at,
                averageMood: (s + a + d) / 3,
            };
        });
    }, [assessmentHistory]);

    // ── Derived: recent activity feed ────────────────────────────────────────
    const recentActivity = useMemo(() => {
        const items = [];
        // Completed activities
        const actArray = Array.isArray(completedActivities)
            ? completedActivities
            : (completedActivities?.activities ?? []);
        actArray.slice(0, 3).forEach((act, i) => {
            items.push({
                id: `act-${act.id ?? i}`,
                type: 'activity',
                title: `Completed: ${act.title ?? act.activity_name ?? 'Activity'}`,
                description: act.description ?? '',
                timestamp: act.completed_at ?? act.created_at ?? new Date().toISOString(),
            });
        });
        // Latest assessment entry
        if (assessmentHistory.length) {
            const latest = [...assessmentHistory].sort(
                (a, b) => new Date(b.created_at) - new Date(a.created_at)
            )[0];
            items.push({
                id: 'assess-latest',
                type: 'assessment',
                title: 'Mental Health Assessment',
                description: `Risk level: ${riskLevel}`,
                timestamp: latest.created_at,
            });
        }
        // Sort by recency and cap at 5
        return items
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 5);
    }, [completedActivities, assessmentHistory, riskLevel]);


    const handleCrisisClick = () => {
        setShowCrisisModal(true);
    };

    // ── Activity counts (handle both array and { activities: [] } shapes) ──────
    const actArray = Array.isArray(completedActivities)
        ? completedActivities
        : (completedActivities?.activities ?? []);
    const activitiesDoneCount = actArray.length;
    const assessmentCount = assessmentHistory.length;

    return (
        <>
            {/* Emergency Banner */}
            <EmergencyBanner
                show={showEmergencyBanner}
                onDismiss={() => setShowEmergencyBanner(false)}
            />

            <PageContainer>
                {/* Welcome Card */}
                <WelcomeCard user={user} className="mb-6" />

                {/* Crisis Safety Banner (passive monitoring) */}
                <CrisisSafetyBanner userId={userId} className="mb-6" />

                {/* Quick Actions */}
                <QuickActions onCrisisClick={handleCrisisClick} className="mb-8" />

                {/* Main Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left Column - 2/3 width */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Risk Overview */}
                        <RiskOverview
                            stressScore={stressScore}
                            depressionScore={depressionScore}
                            anxietyScore={anxietyScore}
                            overallRisk={riskLevel}
                            lastUpdated={
                                lastUpdated
                                    ? format(new Date(lastUpdated), 'MMM d, h:mm a')
                                    : '—'
                            }
                        />

                        {/* Trend Chart */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between">
                                <div>
                                    <CardTitle className="doodle-underline inline-block">30-Day Trends</CardTitle>
                                    <p className="text-sm text-neutral-500 mt-2 font-hand text-base">
                                        Your mental health patterns over time
                                    </p>
                                </div>
                                <Button
                                    as={Link}
                                    to="/predictions"
                                    variant="ghost"
                                    size="sm"
                                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                                    className="text-terracotta hover:bg-cream"
                                >
                                    Details
                                </Button>
                            </CardHeader>
                            <TrendChart data={trendData} height={280} />
                        </Card>

                        {/* Stats Row */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <StatsCard
                                title="Chat Sessions"
                                value="—"
                                icon={<ChatBubbleLeftRightIcon className="w-6 h-6" />}
                                color="primary"
                                trendLabel="coming soon"
                            />
                            <StatsCard
                                title="Assessments"
                                value={assessmentCount}
                                icon={<ChartBarIcon className="w-6 h-6" />}
                                color="accent"
                                trendLabel="total"
                            />
                            <StatsCard
                                title="Activities Done"
                                value={activitiesDoneCount}
                                icon={<ArrowTrendingUpIcon className="w-6 h-6" />}
                                color="success"
                                trendLabel="total"
                            />
                        </div>

                        {/* Recent Activity */}
                        <RecentActivity activities={recentActivity} />
                    </div>

                    {/* Right Column - 1/3 width */}
                    <div className="space-y-6">
                        {/* Daily Affirmation */}
                        {dashboardContent && (
                            <Card className="bg-gradient-to-br from-cream to-lavender/20 border-lavender/30">
                                <CardHeader className="pb-2">
                                    <CardTitle className="flex items-center gap-2 text-sm">
                                        <SunIcon className="w-5 h-5 text-terracotta" />
                                        Daily Affirmation
                                    </CardTitle>
                                </CardHeader>
                                <div className="px-4 pb-4">
                                    <p className="text-sm text-neutral-700 italic font-hand text-base leading-relaxed">
                                        "{dashboardContent.affirmation}"
                                    </p>
                                    {dashboardContent.quote && (
                                        <div className="mt-3 pt-3 border-t border-lavender/20">
                                            <p className="text-xs text-neutral-500 italic">
                                                "{dashboardContent.quote.text}"
                                            </p>
                                            {dashboardContent.quote.author && (
                                                <p className="text-xs text-terracotta-light mt-1">
                                                    — {dashboardContent.quote.author}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </Card>
                        )}

                        {/* Ambient Sounds */}
                        {ambientSounds && ambientSounds.tracks && (
                            <AmbientAudioWidget ambient={ambientSounds} />
                        )}

                        {/* Start Therapy Session CTA */}
                        <Card className="bg-gradient-to-br from-sage/10 to-mint/20 border-sage/30">
                            <div className="p-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <HeartIcon className="w-5 h-5 text-sage" />
                                    <h3 className="font-semibold text-neutral-800 text-sm">Guided Wellness</h3>
                                </div>
                                <p className="text-xs text-neutral-600 mb-3">
                                    Start a personalized therapy session with mood check-in, active listening, and CBT exercises.
                                </p>
                                <Button
                                    as={Link}
                                    to="/therapy"
                                    variant="ghost"
                                    size="sm"
                                    fullWidth
                                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                                    className="text-sage hover:bg-mint/30 border border-sage/30"
                                >
                                    Begin Session
                                </Button>
                            </div>
                        </Card>

                        {/* Weekly Wellness Summary (compact) */}
                        <WeeklyWellnessSummary userId={userId} variant="compact" />

                        {/* Mood Calendar */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <span className="text-lg">{'\uD83D\uDCC5'}</span>
                                    Mood Calendar
                                </CardTitle>
                            </CardHeader>
                            <MoodCalendar data={moodData} />
                        </Card>

                        {/* Recommended Activities */}
                        <UpcomingActivities
                            activities={
                                // API shape: { recommendations: [{ activity: { name, duration_minutes, ... } }] }
                                // ActivityCard needs: { title, duration, category, difficulty, benefits }
                                (recommendedActivities?.recommendations ?? []).map((r) => ({
                                    ...r.activity,
                                    title: r.activity?.name ?? r.activity?.title ?? 'Activity',
                                    duration: r.activity?.duration_minutes ?? r.activity?.duration ?? 10,
                                }))
                            }
                            onStartActivity={(activity) => console.log('Start:', activity)}
                            onCompleteActivity={(activity) => console.log('Complete:', activity)}
                        />

                        {/* Community — latest posts (compact) */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="flex items-center gap-2 text-sm">
                                    <span>{'\uD83E\uDDD1\u200D\uD83E\uDD1D\u200D\uD83E\uDDD1'}</span>
                                    Your Community
                                </CardTitle>
                                <ClusterBadge
                                    clusterName={myCommunity?.community_name}
                                    size="sm"
                                />
                            </CardHeader>

                            <div className="space-y-1.5">
                                {communityFeed.length > 0 ? (
                                    communityFeed.slice(0, 3).map((post) => (
                                        <Link
                                            key={post.id}
                                            to="/community"
                                            className="flex items-start gap-2.5 px-3 py-2.5 rounded-2xl hover:bg-cream/60 transition-colors group"
                                        >
                                            {/* Avatar initials */}
                                            <div className="w-7 h-7 rounded-full bg-peach/60 text-terracotta-dark flex items-center justify-center text-xs font-semibold flex-shrink-0 mt-0.5">
                                                {(post.author?.firstName?.[0] ?? '?').toUpperCase()}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs font-medium text-neutral-700 truncate">
                                                    {post.author?.firstName} {post.author?.lastName}
                                                </p>
                                                <p className="text-xs text-neutral-500 line-clamp-2 mt-0.5">
                                                    {post.content}
                                                </p>
                                            </div>
                                            <ArrowRightIcon className="w-3.5 h-3.5 text-sand group-hover:text-terracotta flex-shrink-0 mt-1 transition-colors" />
                                        </Link>
                                    ))
                                ) : (
                                    <p className="text-xs text-neutral-400 py-3 text-center font-hand text-base">
                                        No posts yet. Be the first!
                                    </p>
                                )}
                            </div>

                            <div className="mt-2 pt-2 border-t border-sand/30">
                                <Button
                                    as={Link}
                                    to="/community"
                                    variant="ghost"
                                    size="sm"
                                    fullWidth
                                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                                    className="text-terracotta hover:bg-cream"
                                >
                                    View Community
                                </Button>
                            </div>
                        </Card>
                    </div>
                </div>
            </PageContainer>

            {/* Crisis Modal */}
            <CrisisModal
                isOpen={showCrisisModal}
                onClose={() => setShowCrisisModal(false)}
            />
        </>
    );
}

export default Dashboard;