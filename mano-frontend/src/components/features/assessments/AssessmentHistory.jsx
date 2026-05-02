import { format } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Card, EmptyState } from '../../common';
import {
    ChartBarIcon,
    ArrowTrendingUpIcon,
    ArrowTrendingDownIcon,
    MinusIcon,
} from '@heroicons/react/24/outline';

// New API shape (per session):
// { user_id, created_at, stress:{score,risk_level}, anxiety:{score,risk_level}, depression:{score,risk_level} }

const METRICS = [
    { key: 'depression', label: 'PHQ-9',  color: 'text-violet-600' },
    { key: 'anxiety',    label: 'GAD-7',  color: 'text-sky-600'    },
    { key: 'stress',     label: 'PSS-10', color: 'text-amber-600'  },
];

const RISK_PILL = {
    low:      'bg-emerald-50 text-emerald-700 border border-emerald-200',
    moderate: 'bg-yellow-50  text-yellow-700  border border-yellow-200',
    high:     'bg-red-50     text-red-700     border border-red-200',
};

function riskPillClass(riskLevel = '') {
    const rl = riskLevel.toLowerCase();
    if (rl.includes('high'))                          return RISK_PILL.high;
    if (rl.includes('moderate') || rl.includes('moderate')) return RISK_PILL.moderate;
    return RISK_PILL.low;
}

function AssessmentHistory({ history = [], className }) {
    if (history.length === 0) {
        return (
            <Card className={className}>
                <EmptyState
                    icon={<ChartBarIcon className="w-8 h-8" />}
                    title="No assessment history"
                    description="Complete an assessment to see your history here"
                />
            </Card>
        );
    }

    // Sort newest → oldest
    const sorted = [...history].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    return (
        <Card className={className}>
            <h3 className="font-semibold text-neutral-900 mb-4">Assessment History</h3>

            <div className="overflow-y-auto max-h-[480px] pr-1 space-y-3 history-scroll">
                {sorted.map((session, idx) => {
                    const prev = sorted[idx + 1]; // older entry for trend

                    return (
                        <div
                            key={session.created_at + idx}
                            className="flex flex-col p-4 rounded-xl border border-neutral-100 bg-neutral-50 hover:border-neutral-200 transition-colors"
                        >
                            {/* Date / time header */}
                            <div className="flex items-baseline gap-2 mb-3">
                                <span className="font-bold text-neutral-900 text-sm">
                                    {format(new Date(session.created_at), 'MMM d, yyyy')}
                                </span>
                                <span className="text-xs font-medium text-neutral-400">
                                    {format(new Date(session.created_at), 'h:mm a')}
                                </span>
                            </div>

                            {/* Metric rows */}
                            <div className="grid grid-cols-3 gap-3">
                                {METRICS.map(({ key, label, color }) => {
                                    const curr = session[key];
                                    const prevVal = prev?.[key];

                                    if (!curr) {
                                        return (
                                            <div key={key} className="flex flex-col items-center opacity-40">
                                                <span className="text-[10px] uppercase tracking-wider font-bold text-neutral-500 mb-1">
                                                    {label}
                                                </span>
                                                <span className="text-lg font-semibold text-neutral-400">—</span>
                                            </div>
                                        );
                                    }

                                    const score = curr.score;
                                    const trend = prevVal?.score != null ? score - prevVal.score : null;

                                    return (
                                        <div key={key} className="flex flex-col items-center">
                                            {/* Label */}
                                            <span className="text-[10px] uppercase tracking-wider font-bold text-neutral-500 mb-1">
                                                {label}
                                            </span>

                                            {/* Score + trend arrow */}
                                            <div className="flex items-end gap-1 mb-1.5">
                                                <span className={cn('text-xl font-extrabold leading-none tabular-nums', color)}>
                                                    {score % 1 === 0 ? score : score.toFixed(1)}
                                                </span>
                                                {trend !== null && (
                                                    <span className={cn(
                                                        'flex items-center text-[10px] font-bold mb-0.5',
                                                        trend < 0 ? 'text-emerald-600' : trend > 0 ? 'text-red-500' : 'text-neutral-400'
                                                    )}>
                                                        {trend < 0 ? <ArrowTrendingDownIcon className="w-3 h-3" /> :
                                                         trend > 0 ? <ArrowTrendingUpIcon   className="w-3 h-3" /> :
                                                                     <MinusIcon             className="w-3 h-3" />}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Risk pill */}
                                            {curr.risk_level && (
                                                <span className={cn(
                                                    'text-[10px] font-semibold px-2 py-0.5 rounded-full',
                                                    riskPillClass(curr.risk_level)
                                                )}>
                                                    {curr.risk_level}
                                                </span>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}

export default AssessmentHistory;