
import { cn } from '../../../utils/helpers';
import { Card, Button } from '../../common';
import {
    ArrowRightIcon,
    CheckCircleIcon,
    MagnifyingGlassIcon,
    SparklesIcon,
} from '@heroicons/react/24/outline';
import { ASSESSMENT_TYPES, getScoreLevel } from '../../../config/assessments';

function AssessmentCard({
    type,
    lastCompleted,
    lastScore,
    riskLevel,
    recommended = false,
    isHighest = false,
    onClick,
    onTakeAssessment,
    onCheckLevel,
    className,
}) {
    const assessment = ASSESSMENT_TYPES[type];
    if (!assessment) return null;

    // Pass the raw score for display without rounding since it is float (e.g. 50.4)
    const displayScore = lastScore !== undefined ? lastScore : undefined;

    // ── Category palettes — all tones are soft & on-brand ──────────────────────
    const palette = {
        depression: {
            iconBg:        'bg-violet-100 text-violet-600',
            scoreBg:       'bg-violet-50 border-violet-100',
            scoreNum:      'text-violet-600',
            checkBtn:      'border-violet-300 text-violet-700 bg-violet-50 hover:bg-violet-100 hover:border-violet-400',
            takeBtn:       'border-violet-200 text-violet-600 hover:bg-violet-50 focus-visible:ring-violet-500',
            highlightRing: 'ring-2 ring-violet-300 ring-offset-2',
            bannerBg:      'bg-violet-600',
            bar:           'bg-violet-400',
        },
        anxiety: {
            iconBg:        'bg-sky-100 text-sky-600',
            scoreBg:       'bg-sky-50 border-sky-100',
            scoreNum:      'text-sky-600',
            checkBtn:      'border-sky-300 text-sky-700 bg-sky-50 hover:bg-sky-100 hover:border-sky-400',
            takeBtn:       'border-sky-200 text-sky-600 hover:bg-sky-50 focus-visible:ring-sky-500',
            highlightRing: 'ring-2 ring-sky-300 ring-offset-2',
            bannerBg:      'bg-sky-600',
            bar:           'bg-sky-400',
        },
        stress: {
            iconBg:        'bg-amber-100 text-amber-600',
            scoreBg:       'bg-amber-50 border-amber-100',
            scoreNum:      'text-amber-600',
            checkBtn:      'border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 hover:border-amber-400',
            takeBtn:       'border-amber-200 text-amber-600 hover:bg-amber-50 focus-visible:ring-amber-500',
            highlightRing: 'ring-2 ring-amber-300 ring-offset-2',
            bannerBg:      'bg-amber-500',
            bar:           'bg-amber-400',
        },
    }[assessment.category];

    // Determine color map based directly on backend "risk_level" strings
    const mappedColor = (() => {
        if (!riskLevel) return 'default';
        const rl = riskLevel.toLowerCase();
        if (rl.includes('low')) return 'success';
        if (rl.includes('mild') || rl.includes('moderate')) return 'warning';
        if (rl.includes('high') || rl.includes('severe')) return 'danger';
        return 'default';
    })();

    const severityPill = {
        success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
        warning: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
        accent:  'bg-orange-50 text-orange-700 border border-orange-200',
        danger:  'bg-red-50 text-red-700 border border-red-200',
    }[mappedColor] ?? 'bg-neutral-100 text-neutral-600 border border-neutral-200';

    const severityDot = {
        success: 'bg-emerald-400',
        warning: 'bg-yellow-400',
        accent:  'bg-orange-400',
        danger:  'bg-red-400',
    }[mappedColor] ?? 'bg-neutral-400';

    // The ML model returns values out of 100 max score
    const scorePct = displayScore !== undefined
        ? Math.min(100, Math.round(displayScore))
        : 0;

    return (
        <Card
            className={cn(
                'relative overflow-hidden flex flex-col transition-all duration-300',
                isHighest && palette.highlightRing,
                className
            )}
            hover
            onClick={onClick}
        >
            {/* ── Highest Score Banner ── */}
            {isHighest && (
                <div className={cn(
                    'absolute top-0 left-0 right-0 flex items-center justify-center gap-1.5 py-1.5 text-white text-xs font-semibold',
                    palette.bannerBg
                )}>
                    <SparklesIcon className="w-3.5 h-3.5" />
                    Highest Score — Review Recommended
                </div>
            )}

            {/* ── Recommended badge ── */}
            {recommended && !isHighest && (
                <div className="absolute top-0 right-0 bg-primary-500 text-white text-xs font-medium px-3 py-1 rounded-bl-xl">
                    Recommended
                </div>
            )}

            <div className={cn('flex flex-col flex-1', isHighest ? 'pt-8' : 'pt-0')}>

                {/* Header */}
                <div className="flex items-start gap-3 mb-3">
                    <div className={cn('w-12 h-12 rounded-2xl flex items-center justify-center text-xl flex-shrink-0', palette.iconBg)}>
                        {assessment.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-neutral-900 text-base leading-tight">{assessment.name}</h3>
                        <p className="text-xs text-neutral-400 leading-snug">{assessment.fullName}</p>
                    </div>
                </div>

                {/* Description */}
                <p className="text-sm text-neutral-500 mb-3 leading-relaxed">{assessment.description}</p>

                {/* ── Score block — only shown when a previous result exists ──── */}
                {lastCompleted && displayScore !== undefined && (
                    <div className={cn('rounded-xl border p-3.5 mb-4', palette.scoreBg)}>

                        {/* Top row: date + level pill */}
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-1.5">
                                <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-500" />
                                <span className="text-xs text-neutral-400">{lastCompleted}</span>
                            </div>
                            {riskLevel && (
                                <span className={cn(
                                    'flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full',
                                    severityPill
                                )}>
                                    <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', severityDot)} />
                                    {riskLevel}
                                </span>
                            )}
                        </div>

                        {/* Big score number — always category color */}
                        <div className="flex items-end gap-2">
                            <span className={cn('text-5xl font-extrabold leading-none tabular-nums', palette.scoreNum)}>
                                {displayScore.toFixed(1)}
                            </span>
                            <div className="flex-1 ml-1 pb-1 min-w-0">
                                <div className="flex justify-end text-[10px] text-neutral-400 mb-1">{scorePct}%</div>
                                <div className="h-1.5 bg-white rounded-full border border-neutral-200 overflow-hidden">
                                    <div
                                        className={cn('h-full rounded-full transition-all duration-700', palette.bar)}
                                        style={{ width: `${scorePct}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Actions ── */}
                <div className="mt-auto flex flex-col gap-2">

                    {/* "Check Your Level" — soft outlined, category-tinted */}
                    {lastCompleted && (
                        <button
                            className={cn(
                                'flex items-center justify-center gap-2 w-full rounded-xl border px-4 py-2.5',
                                'text-sm font-semibold transition-all duration-200',
                                palette.checkBtn
                            )}
                            onClick={(e) => { e.stopPropagation(); onCheckLevel?.(); }}
                        >
                            <MagnifyingGlassIcon className="w-4 h-4 flex-shrink-0" />
                            Check Your {assessment.name} Level
                        </button>
                    )}

                    {/* Take Again / Start Assessment */}
                    <button
                        className={cn(
                            'btn flex items-center justify-center gap-2 w-full rounded-xl border px-3 py-1.5 text-xs font-semibold',
                            palette.takeBtn
                        )}
                        onClick={(e) => { e.stopPropagation(); onTakeAssessment?.(); }}
                    >
                        {!lastCompleted ? 'Start Assessment' : (
                            mappedColor === 'danger' ? 'Retake & Track Changes' :
                            mappedColor === 'accent' || mappedColor === 'warning' ? 'Enhance Model ReTry' :
                            'Quick Check-in'
                        )}
                        <ArrowRightIcon className="w-3.5 h-3.5" />
                    </button>

                </div>
            </div>
        </Card>
    );
}

export default AssessmentCard;