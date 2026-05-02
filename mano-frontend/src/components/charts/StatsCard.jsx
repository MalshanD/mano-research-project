import { cn } from '../../utils/helpers';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/solid';

function StatsCard({
                       title,
                       value,
                       previousValue,
                       suffix = '',
                       prefix = '',
                       icon,
                       trend,
                       trendLabel,
                       color = 'primary',
                       loading = false,
                       className,
                   }) {
    const calculateTrend = () => {
        if (trend !== undefined) return trend;
        if (previousValue === undefined || previousValue === 0) return 0;
        return ((value - previousValue) / previousValue) * 100;
    };

    const trendValue = calculateTrend();
    const isPositive = trendValue > 0;
    const isNegative = trendValue < 0;
    const isNeutral = trendValue === 0;

    const colorClasses = {
        primary: 'bg-peach/30 text-terracotta',
        success: 'bg-mint/40 text-sage-dark',
        warning: 'bg-butter text-terracotta-light',
        danger: 'bg-coral-light/15 text-coral-dark',
        accent: 'bg-cream text-terracotta-light',
    };

    if (loading) {
        return (
            <div className={cn('bg-white rounded-3xl shadow-organic p-6 border border-sand/40', className)}>
                <div className="animate-pulse">
                    <div className="h-4 bg-neutral-200 rounded w-1/2 mb-4" />
                    <div className="h-8 bg-neutral-200 rounded w-3/4 mb-2" />
                    <div className="h-4 bg-neutral-200 rounded w-1/3" />
                </div>
            </div>
        );
    }

    return (
        <div className={cn('bg-white rounded-3xl shadow-organic p-6 border border-sand/40', className)}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <p className="text-sm font-medium text-neutral-500 mb-1">{title}</p>
                    <p className="text-2xl lg:text-3xl font-bold text-neutral-900">
                        {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
                    </p>

                    {/* Trend indicator */}
                    {(trendValue !== undefined || trendLabel) && (
                        <div className="flex items-center gap-1 mt-2">
                            {!isNeutral && (
                                <span
                                    className={cn(
                                        'flex items-center gap-0.5 text-sm font-medium',
                                        isPositive ? 'text-success-600' : 'text-crisis-600'
                                    )}
                                >
                  {isPositive ? (
                      <ArrowUpIcon className="w-4 h-4" />
                  ) : (
                      <ArrowDownIcon className="w-4 h-4" />
                  )}
                                    {Math.abs(trendValue).toFixed(1)}%
                </span>
                            )}
                            {isNeutral && (
                                <span className="flex items-center gap-0.5 text-sm font-medium text-neutral-500">
                  <MinusIcon className="w-4 h-4" />
                  0%
                </span>
                            )}
                            <span className="text-sm text-neutral-400">
                {trendLabel || 'vs last period'}
              </span>
                        </div>
                    )}
                </div>

                {icon && (
                    <div className={cn('p-3 rounded-2xl', colorClasses[color])}>
                        {icon}
                    </div>
                )}
            </div>
        </div>
    );
}

export default StatsCard;