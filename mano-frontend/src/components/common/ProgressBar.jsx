import { cn } from '../../utils/helpers';

const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
    xl: 'h-4',
};

const colors = {
    primary: 'bg-primary-500',
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    danger: 'bg-crisis-500',
    gradient: 'bg-gradient-to-r from-primary-500 to-accent-500',
};

function ProgressBar({
                         value = 0,
                         max = 100,
                         size = 'md',
                         color = 'primary',
                         showLabel = false,
                         label,
                         animated = false,
                         striped = false,
                         className,
                     }) {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
        <div className={className}>
            {(showLabel || label) && (
                <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-neutral-700">
            {label || 'Progress'}
          </span>
                    <span className="text-sm text-neutral-500">{Math.round(percentage)}%</span>
                </div>
            )}
            <div
                className={cn(
                    'w-full bg-neutral-200 rounded-full overflow-hidden',
                    sizes[size]
                )}
            >
                <div
                    className={cn(
                        'h-full rounded-full transition-all duration-500 ease-out',
                        colors[color],
                        animated && 'animate-pulse',
                        striped && 'bg-stripes'
                    )}
                    style={{ width: `${percentage}%` }}
                    role="progressbar"
                    aria-valuenow={value}
                    aria-valuemin={0}
                    aria-valuemax={max}
                />
            </div>
        </div>
    );
}

// Circular progress
export function CircularProgress({
                                     value = 0,
                                     max = 100,
                                     size = 100,
                                     strokeWidth = 8,
                                     color = 'primary',
                                     showLabel = true,
                                     className,
                                 }) {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percentage / 100) * circumference;

    const strokeColors = {
        primary: 'stroke-primary-500',
        success: 'stroke-success-500',
        warning: 'stroke-warning-500',
        danger: 'stroke-crisis-500',
    };

    return (
        <div className={cn('relative inline-flex', className)}>
            <svg width={size} height={size} className="transform -rotate-90">
                {/* Background circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={strokeWidth}
                    className="text-neutral-200"
                />
                {/* Progress circle */}
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    className={cn('transition-all duration-500 ease-out', strokeColors[color])}
                />
            </svg>
            {showLabel && (
                <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-semibold text-neutral-700">
            {Math.round(percentage)}%
          </span>
                </div>
            )}
        </div>
    );
}

export default ProgressBar;