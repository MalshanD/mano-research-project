import { format } from 'date-fns';
import { cn, getRiskLevel } from '../../../utils/helpers';
import { Card, Badge } from '../../common';
import {
    ChartBarIcon,
    ClockIcon,
    ArrowTrendingUpIcon,
    ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';

function PredictionCard({
                            prediction,
                            onClick,
                            compact = false,
                            className,
                        }) {
    const {
        stressScore = 0,
        depressionScore = 0,
        anxietyScore = 0,
        overallRiskLevel = 'LOW',
        trend = 'STABLE',
        createdAt,
        dataSource,
    } = prediction || {};

    const riskLevel = getRiskLevel(Math.max(stressScore, depressionScore, anxietyScore));

    const TrendIcon = trend === 'IMPROVING'
        ? ArrowTrendingDownIcon
        : trend === 'WORSENING'
            ? ArrowTrendingUpIcon
            : null;

    const trendColor = trend === 'IMPROVING'
        ? 'text-success-600'
        : trend === 'WORSENING'
            ? 'text-crisis-600'
            : 'text-neutral-500';

    if (compact) {
        return (
            <div
                onClick={onClick}
                className={cn(
                    'flex items-center gap-4 p-4 bg-white rounded-xl border border-neutral-100 hover:shadow-soft transition-all cursor-pointer',
                    className
                )}
            >
                <div
                    className={cn(
                        'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                        `bg-${riskLevel.color}-100`
                    )}
                >
                    <ChartBarIcon className={cn('w-5 h-5', `text-${riskLevel.color}-600`)} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-neutral-900">
                            Risk Assessment
                        </p>
                        <Badge variant={`risk-${riskLevel.key.toLowerCase()}`} size="sm">
                            {riskLevel.label}
                        </Badge>
                    </div>
                    <p className="text-xs text-neutral-500 mt-0.5">
                        {createdAt ? format(new Date(createdAt), 'MMM d, h:mm a') : 'Unknown date'}
                    </p>
                </div>
                {TrendIcon && (
                    <TrendIcon className={cn('w-5 h-5', trendColor)} />
                )}
            </div>
        );
    }

    return (
        <Card
            onClick={onClick}
            hover
            className={cn('cursor-pointer', className)}
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center">
                        <ChartBarIcon className="w-6 h-6 text-primary-600" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-neutral-900">Risk Assessment</h3>
                        <div className="flex items-center gap-2 mt-1">
                            <ClockIcon className="w-4 h-4 text-neutral-400" />
                            <span className="text-sm text-neutral-500">
                {createdAt ? format(new Date(createdAt), 'MMM d, yyyy') : 'Unknown'}
              </span>
                        </div>
                    </div>
                </div>
                <Badge variant={`risk-${riskLevel.key.toLowerCase()}`}>
                    {riskLevel.label}
                </Badge>
            </div>

            {/* Score Bars */}
            <div className="space-y-3">
                <ScoreBar label="Stress" score={stressScore} color="accent" />
                <ScoreBar label="Depression" score={depressionScore} color="purple" />
                <ScoreBar label="Anxiety" score={anxietyScore} color="primary" />
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-neutral-100">
        <span className="text-xs text-neutral-400 capitalize">
          Source: {dataSource || 'Assessment'}
        </span>
                {TrendIcon && (
                    <div className={cn('flex items-center gap-1 text-sm font-medium', trendColor)}>
                        <TrendIcon className="w-4 h-4" />
                        <span className="capitalize">{trend.toLowerCase()}</span>
                    </div>
                )}
            </div>
        </Card>
    );
}

function ScoreBar({ label, score, color }) {
    const percentage = Math.round(score * 100);

    const colorClasses = {
        primary: 'bg-primary-500',
        accent: 'bg-accent-500',
        purple: 'bg-purple-500',
        success: 'bg-success-500',
        warning: 'bg-warning-500',
        danger: 'bg-crisis-500',
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-neutral-600">{label}</span>
                <span className="text-sm font-medium text-neutral-900">{percentage}%</span>
            </div>
            <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                <div
                    className={cn('h-full rounded-full transition-all duration-500', colorClasses[color])}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

export default PredictionCard;