import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { cn } from '../../utils/helpers';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Tabs, Alert, Button, PageLoader } from '../../components/common';
import {
    AssessmentCard,
    AssessmentHistory,
    MLAssessmentModal,
    WellnessQuestionnaireModal,
} from '../../components/features/assessments';
import { TrendChart } from '../../components/charts';
import {
    useLatestAssessments,
    useAssessmentHistory,
    useRecommendedAssessment,
} from '../../hooks/useAssessment';
import { ASSESSMENT_TYPES } from '../../config/assessments';
import {
    InformationCircleIcon,
    SparklesIcon,
    ClockIcon,
    ChartBarIcon,
    ArrowRightIcon,
    XMarkIcon,
} from '@heroicons/react/24/outline';


// ─── First Visit — "Try Assessment" Hero ─────────────────────────────────────
function TryAssessmentHero({ onTry }) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
            {/* Animated background blobs */}
            <div className="relative mb-8">
                <div className="absolute -inset-8 rounded-full bg-peach/40 opacity-50 blur-2xl animate-pulse-soft" />
                <div className="relative w-28 h-28 rounded-3xl bg-gradient-to-br from-terracotta-light to-terracotta flex items-center justify-center shadow-xl shadow-peach">
                    <SparklesIcon className="w-14 h-14 text-white" />
                </div>
            </div>

            <h1 className="text-3xl font-extrabold text-neutral-900 mb-3">
                Understand Your Mental Wellness
            </h1>
            <p className="text-neutral-500 max-w-md mb-8 leading-relaxed">
                Take a quick, clinically validated screening to get insights into your depression, 
                anxiety, or stress levels. Results appear here after your first assessment.
            </p>

            {/* Assessment type previews */}
            <div className="grid grid-cols-3 gap-3 mb-8 w-full max-w-md">
                {Object.values(ASSESSMENT_TYPES).map((a) => (
                    <div
                        key={a.id}
                        className="rounded-2xl bg-white border border-sand/40 p-3 shadow-organic"
                    >
                        <div className="text-2xl mb-1">{a.icon}</div>
                        <div className="text-xs font-semibold text-neutral-700">{a.name}</div>
                        <div className="text-xs text-neutral-400 mt-0.5">{a.duration}</div>
                    </div>
                ))}
            </div>

            <Button
                variant="primary"
                size="lg"
                rightIcon={<ArrowRightIcon className="w-5 h-5" />}
                onClick={onTry}
                className="px-10 shadow-lg shadow-peach hover:shadow-peach/60"
            >
                Try an Assessment
            </Button>

            <p className="mt-4 text-xs text-neutral-400">
                Free • Anonymous • Takes 2-5 minutes
            </p>
        </div>
    );
}

// ─── Main Assessments Page ───────────────────────────────────────────────────
function Assessments() {
    const navigate = useNavigate();
    const [showAlert, setShowAlert] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [wellnessModal, setWellnessModal] = useState({ open: false, type: null });
    const [pendingRefetch, setPendingRefetch] = useState(false);

    const { data: latestAssessments = {}, isLoading: latestLoading, refetch: refetchLatest } = useLatestAssessments();
    const { data: history = [], isLoading: historyLoading, refetch: refetchHistory } = useAssessmentHistory();
    const { data: recommendedType } = useRecommendedAssessment();

    const hasCompletedAny = latestAssessments && Object.keys(latestAssessments).length > 0;

    // Called when ML assessment results come back — mark as pending, refresh after modal closes
    const handleResultsReady = () => {
        setPendingRefetch(true);
    };

    // Close modal and trigger deferred refetch if results were just submitted
    const handleModalClose = () => {
        setModalOpen(false);
        if (pendingRefetch) {
            setPendingRefetch(false);
            setTimeout(() => {
                refetchLatest?.();
                refetchHistory?.();
            }, 300); // slight delay so modal finishes closing before re-render
        }
    };

    // Format last completed dates
    const getLastCompleted = (type) => {
        const assessment = latestAssessments[type];
        if (!assessment) return null;
        return format(new Date(assessment.completedAt), 'MMM d, yyyy h:mm a');
    };

    // Determine the highest-score card (by absolute score)
    const highestScoreType = Object.keys(ASSESSMENT_TYPES).reduce((highest, type) => {
        const rawScore = latestAssessments[type]?.score;
        if (rawScore === undefined) return highest;
        const score = rawScore;
        if (!highest) return type;
        const highestRaw = latestAssessments[highest]?.score ?? 0;
        const highestScore = highestRaw;
        return score > highestScore ? type : highest;
    }, null);

    // Build trend data from history — new API shape:
    // each entry: { created_at, stress:{score}, anxiety:{score}, depression:{score} }
    const trendData = history
        .slice(0, 30)
        .reverse()
        .map((entry) => ({
            date: format(new Date(entry.created_at), 'MMM d'),
            depression: entry.depression?.score != null ? entry.depression.score / 100 : undefined,
            anxiety:    entry.anxiety?.score    != null ? entry.anxiety.score    / 100 : undefined,
            stress:     entry.stress?.score     != null ? entry.stress.score     / 100 : undefined,
        }));

    const tabs = [
        {
            id: 'all',
            label: 'Assessment',
            content: (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {Object.keys(ASSESSMENT_TYPES).map((type) => (
                        <AssessmentCard
                            key={type}
                            type={type}
                            lastCompleted={getLastCompleted(type)}
                            lastScore={latestAssessments[type]?.score}
                            riskLevel={latestAssessments[type]?.risk_level}
                            isHighest={type === highestScoreType && !!latestAssessments[type]}
                            onTakeAssessment={() => setModalOpen(true)}
                            onCheckLevel={() => setWellnessModal({ open: true, type })}
                        />
                    ))}
                </div>
            ),
        },
        {
            id: 'history',
            label: 'History',
            content: (
                <div className="grid gap-6 lg:grid-cols-2">
                    <AssessmentHistory history={history} />
                    {trendData.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle>Score Trends</CardTitle>
                            </CardHeader>
                            <TrendChart
                                data={trendData}
                                height={300}
                                lines={[
                                    { key: 'depression', name: 'Depression (PHQ-9)', color: '#8b5cf6' },
                                    { key: 'anxiety', name: 'Anxiety (GAD-7)', color: '#0ea5e9' },
                                    { key: 'stress', name: 'Stress (PSS-10)', color: '#f97316' },
                                ]}
                            />
                        </Card>
                    )}
                </div>
            ),
        },
    ];

    // ── Still fetching ──
    if (latestLoading) {
        return (
            <PageContainer title="" subtitle="">
                <PageLoader />
            </PageContainer>
        );
    }

    // ── First-visit: no data yet ──
    if (!hasCompletedAny) {
        return (
            <PageContainer title="" subtitle="">
                <TryAssessmentHero onTry={() => setModalOpen(true)} />

                <MLAssessmentModal
                    isOpen={modalOpen}
                    onClose={handleModalClose}
                    onResultsReady={handleResultsReady}
                />
            </PageContainer>
        );
    }

    // ── Has history: show full assessments dashboard ──
    return (
        <PageContainer
            title="Mental Health Assessments"
            subtitle="Track your mental health with standardized screening tools"
        >
            {/* Info Alert */}
            {showAlert && (
                <Alert 
                    variant="info" 
                    title="About These Assessments" 
                    className="mb-6 relative"
                    dismissible
                    closePosition="top-left"
                    onDismiss={() => setShowAlert(false)}
                >
                    <p className="text-sm text-terracotta-dark mt-1">
                        These are validated screening tools used by healthcare professionals.
                        They help track your mental health over time but are not diagnostic.
                        For clinical diagnosis, please consult a mental health professional.
                    </p>
                </Alert>
            )}

            {/* Take new assessment CTA */}
            <div className="flex justify-end mb-4">
                <Button
                    variant="primary"
                    size="sm"
                    rightIcon={<SparklesIcon className="w-4 h-4" />}
                    onClick={() => setModalOpen(true)}
                >
                    Take Assessment
                </Button>
            </div>

            {/* Tabs */}
            <Tabs tabs={tabs} defaultTab="all" variant="pills" />

            {/* ML Assessment Modal */}
            <MLAssessmentModal
                isOpen={modalOpen}
                onClose={handleModalClose}
                onResultsReady={handleResultsReady}
            />

            {/* Wellness Questionnaire Modal */}
            <WellnessQuestionnaireModal
                isOpen={wellnessModal.open}
                onClose={() => setWellnessModal({ open: false, type: null })}
                assessmentType={wellnessModal.type}
                latestScore={wellnessModal.type ? latestAssessments[wellnessModal.type]?.score : undefined}
            />
        </PageContainer>
    );
}

export default Assessments;