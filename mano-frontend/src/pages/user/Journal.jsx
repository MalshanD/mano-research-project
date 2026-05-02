import { useState, useRef, useCallback } from 'react';
import PageContainer from '../../components/layout/PageContainer';
import { Card, CardHeader, CardTitle, Button, Tabs, Badge, EmptyState, Alert, Loader, Textarea } from '../../components/common';
import { StatsCard, SeverityTrendChart, DistortionBarChart } from '../../components/charts';
import { useAuth } from '../../contexts/AuthContext';
import { useJournal, useJournalAnalysis } from '../../hooks/useJournal';
import {
    PencilSquareIcon,
    BookOpenIcon,
    ChartBarIcon,
    LightBulbIcon,
    SparklesIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    HandThumbUpIcon,
    HandThumbDownIcon,
    ClockIcon,
    EyeIcon,
    InformationCircleIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    DocumentTextIcon,
} from '@heroicons/react/24/outline';

// ─── Severity badge helper ──────────────────────────────────────────────────
function severityConfig(severity) {
    if (severity == null) return { label: 'N/A', variant: 'secondary', color: 'neutral' };
    if (severity <= 1) return { label: 'Mild', variant: 'info', color: 'blue' };
    if (severity <= 2) return { label: 'Moderate', variant: 'warning', color: 'amber' };
    return { label: 'Severe', variant: 'danger', color: 'rose' };
}

// ─── Distortion type icon map (emoji fallback when no catalog icon) ─────────
const distortionEmojis = {
    catastrophizing: '🌋',
    black_and_white: '⬛',
    overgeneralization: '🔄',
    mind_reading: '🧠',
    fortune_telling: '🔮',
    emotional_reasoning: '💔',
    should_statements: '📏',
    labeling: '🏷️',
    personalization: '🎯',
    discounting_positive: '🚫',
    none: '✅',
};

// ─── Live Analysis Preview ──────────────────────────────────────────────────
function AnalysisPreview({ analysis, isAnalyzing }) {
    if (isAnalyzing) {
        return (
            <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-cream border border-sand/40 animate-pulse">
                <Loader size="sm" />
                <span className="text-sm text-terracotta">{'\uD83E\uDDE0'} Analyzing your thoughts…</span>
            </div>
        );
    }

    if (!analysis) return null;

    const sev = severityConfig(analysis.severity);
    const emoji = distortionEmojis[analysis.distortion_type] || '🧩';

    return (
        <div className="rounded-2xl border border-sand/40 bg-gradient-to-br from-cream/50 to-white overflow-hidden">
            <div className="px-4 py-3 border-b border-sand/40 flex items-center gap-2">
                <EyeIcon className="w-4 h-4 text-terracotta" />
                <span className="text-xs font-bold uppercase tracking-widest text-terracotta">{'\uD83D\uDD2E'} Live Preview</span>
            </div>
            <div className="px-4 py-3 space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-lg">{emoji}</span>
                    <span className="font-semibold text-neutral-900">{analysis.label || analysis.distortion_type}</span>
                    <Badge variant={sev.variant} size="sm">{sev.label}</Badge>
                    {analysis.confidence != null && (
                        <span className="text-xs text-neutral-400">{Math.round(analysis.confidence * 100)}% confidence</span>
                    )}
                </div>
                {analysis.cbt_explanation && (
                    <p className="text-sm text-neutral-600 leading-relaxed">{analysis.cbt_explanation}</p>
                )}
            </div>
        </div>
    );
}

// ─── Reframe Card (shown after submit or in entry list) ─────────────────────
function ReframeCard({ reframe, explanation, entryId, userFoundHelpful, onRate, isRating }) {
    if (!reframe) return null;

    return (
        <div className="rounded-2xl bg-gradient-to-br from-mint/40 to-sage-light/20 border border-sage-light/40 p-4 space-y-3">
            <div className="flex items-start gap-2">
                <LightBulbIcon className="w-5 h-5 text-sage-dark flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                    <h4 className="text-xs font-bold uppercase tracking-widest text-sage-dark mb-1">{'\uD83D\uDCA1'} Suggested Reframe</h4>
                    <p className="text-sm text-neutral-800 leading-relaxed">{reframe}</p>
                </div>
            </div>

            {explanation && (
                <div className="flex items-start gap-2 px-3 py-2 bg-white/60 rounded-xl">
                    <InformationCircleIcon className="w-4 h-4 text-terracotta-light flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-neutral-600 leading-relaxed">{explanation}</p>
                </div>
            )}

            {/* Feedback buttons */}
            {entryId && (
                <div className="flex items-center gap-2 pt-1">
                    <span className="text-xs text-neutral-500">Was this helpful?</span>
                    {userFoundHelpful === true ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-sage-dark">
                            <HandThumbUpIcon className="w-4 h-4" /> You found this helpful
                        </span>
                    ) : userFoundHelpful === false ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-neutral-500">
                            <HandThumbDownIcon className="w-4 h-4" /> Not helpful
                        </span>
                    ) : (
                        <>
                            <Button
                                variant="ghost"
                                size="xs"
                                leftIcon={<HandThumbUpIcon className="w-3.5 h-3.5" />}
                                onClick={() => onRate?.(entryId, true)}
                                disabled={isRating}
                            >
                                Yes
                            </Button>
                            <Button
                                variant="ghost"
                                size="xs"
                                leftIcon={<HandThumbDownIcon className="w-3.5 h-3.5" />}
                                onClick={() => onRate?.(entryId, false)}
                                disabled={isRating}
                            >
                                No
                            </Button>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── Single Entry Card ──────────────────────────────────────────────────────
function EntryCard({ entry, onRate, isRating }) {
    const [expanded, setExpanded] = useState(false);
    const sev = severityConfig(entry.severity);
    const emoji = distortionEmojis[entry.distortion_type] || '🧩';
    const dateStr = new Date(entry.entry_date || entry.created_at).toLocaleDateString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric',
    });
    const timeStr = entry.created_at
        ? new Date(entry.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
        : null;

    return (
        <Card>
            <div className="space-y-3">
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-lg">{emoji}</span>
                        <span className="font-semibold text-neutral-900">
                            {entry.distortion_label || entry.distortion_type || 'No distortion'}
                        </span>
                        {entry.distortion_type && entry.distortion_type !== 'none' && (
                            <Badge variant={sev.variant} size="sm">{sev.label}</Badge>
                        )}
                        {entry.confidence != null && (
                            <span className="text-xs text-neutral-400">
                                {Math.round(entry.confidence * 100)}%
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-neutral-400 flex-shrink-0">
                        <ClockIcon className="w-3.5 h-3.5" />
                        <span>{dateStr}</span>
                        {timeStr && <span>· {timeStr}</span>}
                    </div>
                </div>

                {/* Entry text (truncated unless expanded) */}
                <div>
                    <p className={cn(
                        'text-sm text-neutral-700 leading-relaxed',
                        !expanded && 'line-clamp-3',
                    )}>
                        {entry.entry_text}
                    </p>
                    {entry.entry_text?.length > 200 && (
                        <button
                            onClick={() => setExpanded((e) => !e)}
                            className="mt-1 flex items-center gap-1 text-xs font-semibold text-terracotta hover:text-terracotta-dark"
                        >
                            {expanded
                                ? <><ChevronUpIcon className="w-3.5 h-3.5" /> Show less</>
                                : <><ChevronDownIcon className="w-3.5 h-3.5" /> Read more</>
                            }
                        </button>
                    )}
                </div>

                {/* Reframe */}
                {entry.reframe_suggestion && (
                    <ReframeCard
                        reframe={entry.reframe_suggestion}
                        explanation={entry.cbt_explanation}
                        entryId={entry.id}
                        userFoundHelpful={entry.user_found_helpful}
                        onRate={onRate}
                        isRating={isRating}
                    />
                )}
            </div>
        </Card>
    );
}

// ─── Trends Overview ────────────────────────────────────────────────────────
function TrendsOverview({ trends, trendsLoading }) {
    if (trendsLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Loader size="lg" />
                <p className="text-sm text-neutral-400">Loading trends…</p>
            </div>
        );
    }

    if (!trends) {
        return (
            <EmptyState
                icon={<ChartBarIcon className="w-8 h-8" />}
                title="No trends yet"
                description="Write a few journal entries to see your distortion patterns over time."
            />
        );
    }

    const { distortion_frequency = {}, daily_severity = [], top_distortion, balanced_ratio, avg_severity, total_entries, insights = [] } = trends;

    return (
        <div className="space-y-6">
            {/* Summary stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card className="text-center">
                    <p className="text-2xl font-bold text-neutral-900">{total_entries || 0}</p>
                    <p className="text-xs text-neutral-500 mt-1">Total Entries (30d)</p>
                </Card>
                <Card className="text-center">
                    <p className="text-2xl font-bold text-neutral-900 capitalize">
                        {top_distortion ? top_distortion.replace(/_/g, ' ') : 'None'}
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">Most Frequent Pattern</p>
                </Card>
                <Card className="text-center">
                    <p className="text-2xl font-bold text-neutral-900">
                        {avg_severity != null ? avg_severity.toFixed(1) : 'N/A'}
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">Avg Severity</p>
                </Card>
                <Card className="text-center">
                    <p className="text-2xl font-bold text-neutral-900">
                        {balanced_ratio != null ? `${Math.round(balanced_ratio * 100)}%` : 'N/A'}
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">Balanced Thinking</p>
                </Card>
            </div>

            {/* Severity over time (area chart) */}
            {daily_severity.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Severity Over Time</CardTitle>
                    </CardHeader>
                    <SeverityTrendChart data={daily_severity} height={260} />
                </Card>
            )}

            {/* Distortion frequency (bar chart) */}
            {Object.keys(distortion_frequency).length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Distortion Patterns</CardTitle>
                    </CardHeader>
                    <DistortionBarChart frequencyMap={distortion_frequency} height={Math.max(200, Object.keys(distortion_frequency).length * 40)} />
                </Card>
            )}

            {/* Personalized insights */}
            {insights.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Insights</CardTitle>
                    </CardHeader>
                    <div className="space-y-3">
                        {insights.map((insight, i) => (
                            <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-2xl bg-cream border border-sand/40">
                                <span className="mt-0.5 flex-shrink-0">{'\u2728'}</span>
                                <p className="text-sm text-terracotta-dark">{insight.text}</p>
                            </div>
                        ))}
                    </div>
                </Card>
            )}
        </div>
    );
}

// ─── Distortion Catalog Reference ───────────────────────────────────────────
function CatalogReference({ catalog }) {
    const [expandedType, setExpandedType] = useState(null);

    // Catalog can be: { distortions: [...] } OR { catastrophizing: {...}, ... } (flat object)
    // Normalize to an array of { type, label, description, ... }
    let distortions = [];
    if (catalog) {
        if (Array.isArray(catalog.distortions)) {
            distortions = catalog.distortions;
        } else if (typeof catalog === 'object') {
            // Flat object keyed by distortion type — convert to array
            distortions = Object.entries(catalog)
                .filter(([key]) => key !== 'none') // exclude "none" from learn tab
                .map(([type, data]) => ({ type, ...data }));
        }
    }

    if (!catalog || distortions.length === 0) {
        return (
            <EmptyState
                icon={<BookOpenIcon className="w-8 h-8" />}
                title="Catalog loading…"
                description="The CBT distortion catalog will appear here."
            />
        );
    }

    return (
        <div className="space-y-3">
            <p className="text-sm text-neutral-500 mb-4">
                Learn about the 10 cognitive distortions identified in Cognitive Behavioral Therapy (CBT). Understanding these patterns is the first step to healthier thinking.
            </p>
            {distortions.map((d) => {
                const isExpanded = expandedType === d.type;
                const emoji = distortionEmojis[d.type] || '🧩';
                return (
                    <Card key={d.type} hover onClick={() => setExpandedType(isExpanded ? null : d.type)}>
                        <div className="flex items-start gap-3">
                            <span className="text-xl flex-shrink-0">{emoji}</span>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                    <h4 className="font-semibold text-neutral-900">{d.label}</h4>
                                    {isExpanded
                                        ? <ChevronUpIcon className="w-4 h-4 text-neutral-400" />
                                        : <ChevronDownIcon className="w-4 h-4 text-neutral-400" />
                                    }
                                </div>
                                <p className="text-sm text-neutral-600 mt-1">{d.description}</p>
                                {isExpanded && (
                                    <div className="mt-3 space-y-2">
                                        {d.cbt_explanation && (
                                            <div className="px-3 py-2 bg-cream rounded-xl border border-sand/30">
                                                <p className="text-xs text-terracotta-dark">{d.cbt_explanation}</p>
                                            </div>
                                        )}
                                        {d.reframe_templates?.length > 0 && (
                                            <div>
                                                <p className="text-xs font-semibold text-neutral-500 mb-1">Example reframes:</p>
                                                <ul className="space-y-1">
                                                    {d.reframe_templates.slice(0, 3).map((rt, i) => (
                                                        <li key={i} className="flex items-start gap-2">
                                                            <LightBulbIcon className="w-3.5 h-3.5 text-sage mt-0.5 flex-shrink-0" />
                                                            <span className="text-xs text-neutral-600">{rt}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </Card>
                );
            })}
        </div>
    );
}

// ─── Main Journal Page ──────────────────────────────────────────────────────
function Journal() {
    const { user } = useAuth();
    const userId = user?.id;

    const {
        entries,
        trends,
        catalog,
        entriesLoading,
        trendsLoading,
        submitEntry,
        rateReframe,
        refetchEntries,
        refetchTrends,
        isSubmitting,
        submitError,
        isRating,
    } = useJournal(userId);

    const { analysis, isAnalyzing, analyze, clearAnalysis } = useJournalAnalysis(userId);

    const [text, setText] = useState('');
    const [lastResult, setLastResult] = useState(null);
    const [showResult, setShowResult] = useState(false);
    const debounceRef = useRef(null);

    // Debounced live analysis while typing
    const handleTextChange = useCallback((e) => {
        const val = e.target.value;
        setText(val);
        setShowResult(false);
        setLastResult(null);

        if (debounceRef.current) clearTimeout(debounceRef.current);

        if (val.trim().length >= 20) {
            debounceRef.current = setTimeout(() => {
                analyze(val);
            }, 800);
        } else {
            clearAnalysis();
        }
    }, [analyze, clearAnalysis]);

    // Submit entry
    const handleSubmit = async () => {
        if (!text.trim() || text.trim().length < 10) return;
        const { data, error } = await submitEntry(text);
        if (!error && data) {
            setLastResult(data.entry ? { ...data.entry, crisis_alert: data.crisis_alert } : data);
            setShowResult(true);
            setText('');
            clearAnalysis();
        }
    };

    // Rate reframe
    const handleRate = async (entryId, helpful) => {
        await rateReframe(entryId, helpful);
    };

    // Stats
    const totalEntries = entries?.length || 0;
    const distortionEntries = entries?.filter((e) => e.distortion_type && e.distortion_type !== 'none').length || 0;
    const helpfulCount = entries?.filter((e) => e.user_found_helpful === true).length || 0;

    const tabs = [
        {
            id: 'write',
            label: 'Write',
            icon: <PencilSquareIcon className="w-4 h-4" />,
            content: (
                <div className="space-y-4">
                    {/* Editor */}
                    <Card>
                        <CardHeader>
                            <CardTitle>What's on your mind?</CardTitle>
                            <p className="text-sm text-neutral-500 mt-1">
                                Write freely about your thoughts and feelings. Our AI will identify cognitive patterns and suggest healthier perspectives.
                            </p>
                        </CardHeader>

                        <Textarea
                            placeholder="Today I feel... / I keep thinking that... / Something happened and I noticed..."
                            rows={6}
                            resize="vertical"
                            value={text}
                            onChange={handleTextChange}
                            disabled={isSubmitting}
                        />

                        {/* Live analysis preview */}
                        <div className="mt-4">
                            <AnalysisPreview analysis={analysis} isAnalyzing={isAnalyzing} />
                        </div>

                        {/* Submit */}
                        <div className="flex items-center justify-between mt-4 pt-4 border-t border-sand/30">
                            <span className="text-xs text-neutral-400">
                                {text.trim().length < 10
                                    ? `${10 - text.trim().length} more characters needed`
                                    : `${text.trim().length} characters`
                                }
                            </span>
                            <Button
                                variant="primary"
                                leftIcon={<PencilSquareIcon className="w-4 h-4" />}
                                onClick={handleSubmit}
                                loading={isSubmitting}
                                disabled={text.trim().length < 10}
                            >
                                Save Entry
                            </Button>
                        </div>

                        {submitError && (
                            <Alert variant="danger" className="mt-3">
                                <p className="text-sm">{submitError}</p>
                            </Alert>
                        )}
                    </Card>

                    {/* Result after submission */}
                    {showResult && lastResult && (
                        <Card className="border-2 border-sage-light/60 bg-mint/20">
                            <div className="flex items-center gap-2 mb-3">
                                <CheckCircleIcon className="w-5 h-5 text-sage-dark" />
                                <span className="font-semibold text-sage-dark">{'\u2705'} Entry Saved & Analyzed</span>
                            </div>

                            <div className="space-y-3">
                                {/* Distortion result */}
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-lg">{distortionEmojis[lastResult.distortion_type] || '🧩'}</span>
                                    <span className="font-semibold text-neutral-900">
                                        {lastResult.distortion_label || lastResult.distortion_type}
                                    </span>
                                    <Badge variant={severityConfig(lastResult.severity).variant} size="sm">
                                        {severityConfig(lastResult.severity).label}
                                    </Badge>
                                    {lastResult.confidence != null && (
                                        <span className="text-xs text-neutral-400">
                                            {Math.round(lastResult.confidence * 100)}% confidence
                                        </span>
                                    )}
                                </div>

                                {/* Reframe */}
                                <ReframeCard
                                    reframe={lastResult.reframe_suggestion}
                                    explanation={lastResult.cbt_explanation}
                                    entryId={lastResult.id}
                                    userFoundHelpful={lastResult.user_found_helpful}
                                    onRate={handleRate}
                                    isRating={isRating}
                                />

                                {/* Crisis alert if present */}
                                {lastResult.crisis_alert && (
                                    <Alert variant="crisis" title="We noticed something">
                                        <p className="text-sm">
                                            {lastResult.crisis_alert.message || 'It sounds like you might be going through a difficult time. Remember, support is available.'}
                                        </p>
                                    </Alert>
                                )}
                            </div>
                        </Card>
                    )}
                </div>
            ),
        },
        {
            id: 'entries',
            label: 'Past Entries',
            badge: totalEntries > 0 ? totalEntries : undefined,
            icon: <DocumentTextIcon className="w-4 h-4" />,
            content: (
                <div className="space-y-4">
                    {entriesLoading ? (
                        <div className="flex flex-col items-center justify-center py-16 gap-3">
                            <Loader size="lg" />
                            <p className="text-sm text-neutral-400">Loading your journal entries…</p>
                        </div>
                    ) : entries.length === 0 ? (
                        <EmptyState
                            icon={<BookOpenIcon className="w-8 h-8" />}
                            title="No journal entries yet"
                            description="Start writing to track your thoughts and discover cognitive patterns."
                        />
                    ) : (
                        <div className="flex flex-col gap-3">
                            {entries.map((entry) => (
                                <EntryCard
                                    key={entry.id}
                                    entry={entry}
                                    onRate={handleRate}
                                    isRating={isRating}
                                />
                            ))}
                        </div>
                    )}
                </div>
            ),
        },
        {
            id: 'trends',
            label: 'Trends',
            icon: <ChartBarIcon className="w-4 h-4" />,
            content: <TrendsOverview trends={trends} trendsLoading={trendsLoading} />,
        },
        {
            id: 'learn',
            label: 'Learn',
            icon: <BookOpenIcon className="w-4 h-4" />,
            content: <CatalogReference catalog={catalog} />,
        },
    ];

    return (
        <PageContainer
            title="Thought Journal"
            subtitle="Track your thinking patterns and build healthier perspectives with CBT"
        >
            {/* Stats Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <StatsCard
                    title="Journal Entries"
                    value={totalEntries}
                    icon={<DocumentTextIcon className="w-6 h-6" />}
                    color="primary"
                    loading={entriesLoading}
                />
                <StatsCard
                    title="Patterns Found"
                    value={distortionEntries}
                    icon={<ExclamationTriangleIcon className="w-6 h-6" />}
                    color="warning"
                    loading={entriesLoading}
                />
                <StatsCard
                    title="Helpful Reframes"
                    value={helpfulCount}
                    icon={<HandThumbUpIcon className="w-6 h-6" />}
                    color="success"
                    loading={entriesLoading}
                />
            </div>

            {/* Main Content */}
            <Tabs tabs={tabs} defaultTab="write" variant="pills" />
        </PageContainer>
    );
}

// Helper
function cn(...classes) {
    return classes.filter(Boolean).join(' ');
}

export default Journal;
