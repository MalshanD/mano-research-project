import { useQuery } from '@tanstack/react-query';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, CardContent, Button, Alert, Loader } from '../../components/common';
import { useAuth } from '../../contexts/AuthContext';
import { predictInsightsForUser, counterfactualForUser } from '../../api/client';
import {
    LightBulbIcon,
    ArrowPathIcon,
    ChartBarIcon,
    AdjustmentsHorizontalIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    InformationCircleIcon,
    BeakerIcon,
} from '@heroicons/react/24/outline';
import { cn } from '../../utils/helpers';

/* ─── Demo data — shown as a preview when the user has no real assessment ─── */
const DEMO_INSIGHTS = {
    _isDemo: true,
    scores: {
        stress:     { score: 62.3, risk_level: 'Moderate' },
        anxiety:    { score: 45.8, risk_level: 'Low' },
        depression: { score: 71.1, risk_level: 'High' },
    },
    risk_tier: 'Moderate',
    explanations: {
        stress: [
            { feature: 'Work_Stress',          impact:  0.38 },
            { feature: 'Sleep_Hours',           impact: -0.29 },
            { feature: 'Financial_Stress',      impact:  0.22 },
            { feature: 'Social_Support_Score',  impact: -0.14 },
            { feature: 'Loneliness_Score',      impact:  0.09 },
        ],
        anxiety: [
            { feature: 'Loneliness_Score',      impact:  0.31 },
            { feature: 'Work_Stress',           impact:  0.19 },
            { feature: 'Self_Esteem_Score',     impact: -0.17 },
            { feature: 'Physical_Activity_Hrs', impact: -0.12 },
            { feature: 'Financial_Stress',      impact:  0.08 },
        ],
        depression: [
            { feature: 'Life_Satisfaction_Score', impact: -0.42 },
            { feature: 'Loneliness_Score',         impact:  0.35 },
            { feature: 'Sleep_Hours',              impact: -0.24 },
            { feature: 'Social_Support_Score',     impact: -0.18 },
            { feature: 'Physical_Activity_Hrs',    impact: -0.10 },
        ],
    },
    resources: [
        { title: 'Mindfulness & Meditation Practices' },
        { title: 'Sleep Hygiene Improvement Guide' },
        { title: 'Workplace Stress Management' },
        { title: 'Social Connection Building' },
    ],
};

const DEMO_COUNTERFACTUAL = {
    _isDemo: true,
    recommendations: [
        {
            feature: 'Sleep_Hours',
            current_value: 6.0,
            recommended_value: 7.5,
            risk_reduction: 2.6,
            description: 'Increasing your sleep could significantly reduce your overall risk score.',
        },
        {
            feature: 'Work_Stress',
            current_value: 8,
            recommended_value: 5,
            risk_reduction: 3.1,
            description: 'Reducing work stress is one of the highest-impact changes you can make.',
        },
        {
            feature: 'Physical_Activity_Hrs',
            current_value: 0.5,
            recommended_value: 1.5,
            risk_reduction: 1.8,
            description: 'More physical activity consistently improves mental health outcomes.',
        },
        {
            feature: 'Social_Support_Score',
            current_value: 3,
            recommended_value: 6,
            risk_reduction: 2.2,
            description: 'Building stronger social connections has a protective effect on mental health.',
        },
    ],
};

/* ─── Risk styling ───────────────────────────────────────────────────────── */
const riskStyles = {
    LOW:    { bg: 'bg-success-50',  border: 'border-success-200',  text: 'text-success-700',  label: 'Low Risk'      },
    MEDIUM: { bg: 'bg-warning-50',  border: 'border-warning-200',  text: 'text-warning-700',  label: 'Moderate Risk' },
    HIGH:   { bg: 'bg-crisis-50',   border: 'border-crisis-200',   text: 'text-crisis-700',   label: 'High Risk'     },
};

function normalizeRisk(level) {
    if (!level) return 'LOW';
    const u = level.toUpperCase();
    if (u === 'HIGH' || u === 'SEVERE') return 'HIGH';
    if (u === 'MEDIUM' || u === 'MODERATE') return 'MEDIUM';
    return 'LOW';
}

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function ShapBar({ feature, value, maxAbsValue }) {
    const isPositive = value >= 0;
    const widthPercent = Math.min((Math.abs(value) / maxAbsValue) * 100, 100);

    return (
        <div className="flex items-center gap-3 py-1.5">
            <span className="text-xs text-neutral-600 w-36 truncate text-right flex-shrink-0">
                {feature.replace(/_/g, ' ')}
            </span>
            <div className="flex-1 flex items-center h-5">
                {/* Negative side (decreases risk — green) */}
                <div className="flex-1 flex justify-end">
                    {!isPositive && (
                        <div
                            className="h-4 rounded-l-sm bg-success-400/70"
                            style={{ width: `${widthPercent}%` }}
                        />
                    )}
                </div>
                {/* Centre line */}
                <div className="w-px h-5 bg-neutral-300 flex-shrink-0 mx-0.5" />
                {/* Positive side (increases risk — red) */}
                <div className="flex-1 flex justify-start">
                    {isPositive && (
                        <div
                            className="h-4 rounded-r-sm bg-crisis-400/70"
                            style={{ width: `${widthPercent}%` }}
                        />
                    )}
                </div>
            </div>
            <span className={cn(
                'text-xs font-medium w-12 text-right flex-shrink-0',
                isPositive ? 'text-crisis-600' : 'text-success-600'
            )}>
                {isPositive ? '+' : ''}{value.toFixed(2)}
            </span>
        </div>
    );
}

function ScoreCard({ label, score, riskLevel, icon: Icon }) {
    const risk  = normalizeRisk(riskLevel);
    const style = riskStyles[risk];

    return (
        <div className={cn('rounded-2xl border p-5 transition-all', style.bg, style.border)}>
            <div className="flex items-center gap-3 mb-3">
                <div className={cn('p-2 rounded-xl', style.bg)}>
                    <Icon className={cn('w-5 h-5', style.text)} />
                </div>
                <h4 className="font-semibold text-neutral-800">{label}</h4>
            </div>
            <div className="flex items-end justify-between">
                <div>
                    <p className={cn('text-3xl font-bold', style.text)}>
                        {typeof score === 'number' ? score.toFixed(1) : (score ?? '—')}
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">out of 100</p>
                </div>
                <span className={cn(
                    'text-xs font-semibold px-2.5 py-1 rounded-full border',
                    style.bg, style.text, style.border
                )}>
                    {style.label}
                </span>
            </div>
        </div>
    );
}

function SHAPSection({ explanations }) {
    return (
        <div>
            <h4 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
                Feature Contributions (SHAP)
            </h4>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {['stress', 'anxiety', 'depression'].map((dimension) => {
                    const shapValues = explanations[dimension];
                    if (!shapValues || shapValues.length === 0) return null;

                    const top5 = shapValues.slice(0, 5);
                    const maxAbsValue = Math.max(...top5.map((s) => Math.abs(s.impact)), 0.01);

                    return (
                        <div key={dimension} className="rounded-2xl bg-neutral-50 border border-neutral-200/60 p-4">
                            <h5 className="text-sm font-semibold text-neutral-700 capitalize mb-3">
                                {dimension}
                            </h5>
                            <div className="space-y-0.5">
                                {top5.map((item, idx) => (
                                    <ShapBar
                                        key={idx}
                                        feature={item.feature}
                                        value={item.impact}
                                        maxAbsValue={maxAbsValue}
                                    />
                                ))}
                            </div>
                            <div className="flex items-center justify-between mt-3 pt-2 border-t border-neutral-200/60">
                                <span className="text-[10px] text-success-600 flex items-center gap-1">
                                    <span className="w-2.5 h-2.5 rounded-sm bg-success-400/70 inline-block" />
                                    Decreases risk
                                </span>
                                <span className="text-[10px] text-crisis-600 flex items-center gap-1">
                                    <span className="w-2.5 h-2.5 rounded-sm bg-crisis-400/70 inline-block" />
                                    Increases risk
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function CounterfactualCard({ item }) {
    return (
        <div className="rounded-2xl bg-white border border-neutral-200 p-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-primary-50 flex-shrink-0 mt-0.5">
                    <AdjustmentsHorizontalIcon className="w-5 h-5 text-primary-500" />
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-neutral-800 capitalize text-sm">
                        {(item.feature || '').replace(/_/g, ' ')}
                    </h4>
                    {/* Current → Recommended */}
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-lg">
                            Now: {String(item.current_value)}
                        </span>
                        <ArrowPathIcon className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
                        <span className="text-xs text-primary-700 bg-primary-50 border border-primary-200 px-2 py-0.5 rounded-lg font-medium">
                            Target: {String(item.recommended_value)}
                        </span>
                    </div>
                    {/* Risk reduction badge */}
                    {item.risk_reduction != null && (
                        <p className="text-xs text-success-700 mt-2 flex items-center gap-1 font-medium">
                            <CheckCircleIcon className="w-3.5 h-3.5 flex-shrink-0" />
                            −{item.risk_reduction.toFixed(1)} pts average risk reduction
                        </p>
                    )}
                    {/* Description */}
                    {item.description && (
                        <p className="text-xs text-neutral-500 mt-1 leading-relaxed">{item.description}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ─── Demo banner ────────────────────────────────────────────────────────── */
function DemoBanner() {
    return (
        <div className="flex items-start gap-3 p-3 rounded-xl bg-warning-50 border border-warning-200 mb-4">
            <BeakerIcon className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-warning-700 leading-relaxed">
                <span className="font-semibold">Preview mode — </span>
                This is sample data. Complete an{' '}
                <span className="font-semibold">ML Assessment</span> from the Assessments page
                to see your personalised risk insights here.
            </p>
        </div>
    );
}

/* ─── Insights results section ───────────────────────────────────────────── */
function InsightsResults({ data }) {
    const isDemo = data._isDemo;

    return (
        <div className="space-y-6">
            {isDemo && <DemoBanner />}

            {/* Critical flag */}
            {data.critical_flag && (
                <Alert variant="warning" title="Critical Flag Detected">
                    {data.critical_flag.message}
                    {data.critical_flag.hotline && (
                        <p className="mt-1 font-semibold">Hotline: {data.critical_flag.hotline}</p>
                    )}
                </Alert>
            )}

            {/* Score cards */}
            <div>
                <h4 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
                    Predicted Risk Scores
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <ScoreCard
                        label="Stress"
                        score={data.scores?.stress?.score}
                        riskLevel={data.scores?.stress?.risk_level}
                        icon={ExclamationTriangleIcon}
                    />
                    <ScoreCard
                        label="Anxiety"
                        score={data.scores?.anxiety?.score}
                        riskLevel={data.scores?.anxiety?.risk_level}
                        icon={InformationCircleIcon}
                    />
                    <ScoreCard
                        label="Depression"
                        score={data.scores?.depression?.score}
                        riskLevel={data.scores?.depression?.risk_level}
                        icon={ChartBarIcon}
                    />
                </div>
            </div>

            {/* SHAP explanations */}
            {data.explanations && <SHAPSection explanations={data.explanations} />}

            {/* Recommended resources */}
            {data.resources && data.resources.length > 0 && (
                <div>
                    <h4 className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-3">
                        Recommended Resources
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {data.resources.map((resource, idx) => (
                            <div
                                key={idx}
                                className="flex items-center gap-3 p-3 rounded-xl bg-neutral-50 border border-neutral-200"
                            >
                                <CheckCircleIcon className="w-4 h-4 text-success-500 flex-shrink-0" />
                                <span className="text-sm text-neutral-700">{resource.title || resource}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ─── Counterfactual results section ─────────────────────────────────────── */
function CounterfactualResults({ data }) {
    const isDemo = data._isDemo;
    const recs   = data.recommendations || [];

    return (
        <div className="space-y-4">
            {isDemo && <DemoBanner />}

            {recs.length === 0 ? (
                <div className="text-center py-8">
                    <p className="text-neutral-500 text-sm">
                        No actionable changes found. Your current scores may already be at a healthy baseline.
                    </p>
                </div>
            ) : (
                <>
                    <Alert variant="info" title="How to read these suggestions">
                        Each card shows a single lifestyle change and its estimated impact on your overall risk score.
                        These are AI-generated suggestions based on counterfactual analysis — always consult a
                        professional for personalised advice.
                    </Alert>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {recs.map((item, idx) => (
                            <CounterfactualCard key={idx} item={item} />
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}

/* ─── Main Insights page ─────────────────────────────────────────────────── */
export default function Insights() {
    const { user } = useAuth();
    const userId   = user?.id;

    // ── Predict query ──────────────────────────────────────────────────
    const insightsQuery = useQuery({
        queryKey: ['insights', userId],
        queryFn: async () => {
            if (!userId) throw new Error('You must be logged in to run analysis.');
            const { data, error } = await predictInsightsForUser(userId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        retry: false,
    });

    // ── Counterfactual query ───────────────────────────────────────────
    const counterfactualQuery = useQuery({
        queryKey: ['counterfactual', userId],
        queryFn: async () => {
            if (!userId) throw new Error('You must be logged in to find actionable changes.');
            const { data, error } = await counterfactualForUser(userId, 1);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        retry: false,
    });

    // Determine what to display for each panel
    // Real data → use it. Error → show error + demo preview. Idle → show demo preview.
    const showInsightsDemo        = !insightsQuery.data;
    const showCounterfactualDemo  = !counterfactualQuery.data;
    const displayInsights         = insightsQuery.data ?? DEMO_INSIGHTS;
    const displayCounterfactual   = counterfactualQuery.data ?? DEMO_COUNTERFACTUAL;

    return (
        <PageContainer
            title="Risk Insights"
            subtitle="AI-powered explainability and personalised recommendations based on your assessment"
        >
            <div className="space-y-8">

                {/* ── Section 1: Risk Analysis ── */}
                <section>
                    <Card variant="default" padding="lg">
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2.5 rounded-xl bg-warning-50">
                                        <ChartBarIcon className="w-6 h-6 text-warning-600" />
                                    </div>
                                    <div>
                                        <CardTitle>Risk Analysis</CardTitle>
                                        <p className="text-sm text-neutral-500 mt-0.5">
                                            {showInsightsDemo
                                                ? 'Preview — complete an ML Assessment to see your real scores'
                                                : 'Your personalised risk scores based on your latest assessment'}
                                        </p>
                                    </div>
                                </div>
                                <Button
                                    id="btn-run-analysis"
                                    onClick={() => insightsQuery.refetch()}
                                    loading={insightsQuery.isFetching}
                                    disabled={!userId || insightsQuery.isFetching}
                                    leftIcon={<LightBulbIcon className="w-4 h-4" />}
                                    size="lg"
                                >
                                    Refresh Analysis
                                </Button>
                            </div>
                        </CardHeader>

                        <CardContent>
                            {/* Loading */}
                            {insightsQuery.isFetching && (
                                <div className="flex flex-col items-center justify-center py-12">
                                    <Loader size="lg" />
                                    <p className="mt-4 text-neutral-500 text-sm">
                                        Analysing your risk profile with SHAP…
                                    </p>
                                </div>
                            )}

                            {/* Error banner (shown alongside demo preview) */}
                            {insightsQuery.isError && !insightsQuery.isFetching && (
                                <Alert variant="warning" title="Could not load your real data" className="mb-4">
                                    {insightsQuery.error?.message}
                                    {insightsQuery.error?.message?.toLowerCase().includes('assessment') && (
                                        <span className="block mt-1">
                                            Go to <strong>Assessments</strong> and complete an ML Assessment first.
                                        </span>
                                    )}
                                </Alert>
                            )}

                            {/* Results (real or demo) — always visible */}
                            {!insightsQuery.isFetching && (
                                <InsightsResults data={displayInsights} />
                            )}
                        </CardContent>
                    </Card>
                </section>

                {/* ── Section 2: Actionable Changes ── */}
                <section>
                    <Card variant="default" padding="lg">
                        <CardHeader>
                            <div className="flex items-center justify-between flex-wrap gap-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2.5 rounded-xl bg-primary-50">
                                        <AdjustmentsHorizontalIcon className="w-6 h-6 text-primary-500" />
                                    </div>
                                    <div>
                                        <CardTitle>What Could Help?</CardTitle>
                                        <p className="text-sm text-neutral-500 mt-0.5">
                                            {showCounterfactualDemo
                                                ? 'Preview — complete an ML Assessment to see your real recommendations'
                                                : 'Lifestyle changes most likely to reduce your risk scores'}
                                        </p>
                                    </div>
                                </div>
                                <Button
                                    id="btn-find-changes"
                                    onClick={() => counterfactualQuery.refetch()}
                                    loading={counterfactualQuery.isFetching}
                                    disabled={!userId || counterfactualQuery.isFetching}
                                    leftIcon={<ArrowPathIcon className="w-4 h-4" />}
                                    variant="outline"
                                    size="lg"
                                >
                                    Refresh Actionable Changes
                                </Button>
                            </div>
                        </CardHeader>

                        <CardContent>
                            {/* Loading */}
                            {counterfactualQuery.isFetching && (
                                <div className="flex flex-col items-center justify-center py-12">
                                    <Loader size="lg" />
                                    <p className="mt-4 text-neutral-500 text-sm">
                                        Generating counterfactual scenarios…
                                    </p>
                                </div>
                            )}

                            {/* Error banner */}
                            {counterfactualQuery.isError && !counterfactualQuery.isFetching && (
                                <Alert variant="warning" title="Could not load your real data" className="mb-4">
                                    {counterfactualQuery.error?.message}
                                    {counterfactualQuery.error?.message?.toLowerCase().includes('assessment') && (
                                        <span className="block mt-1">
                                            Go to <strong>Assessments</strong> and complete an ML Assessment first.
                                        </span>
                                    )}
                                </Alert>
                            )}

                            {/* Results (real or demo) — always visible */}
                            {!counterfactualQuery.isFetching && (
                                <CounterfactualResults data={displayCounterfactual} />
                            )}
                        </CardContent>
                    </Card>
                </section>

            </div>
        </PageContainer>
    );
}
