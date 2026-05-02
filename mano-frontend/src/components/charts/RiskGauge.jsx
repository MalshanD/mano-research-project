import { useMemo } from 'react';
import { cn } from '../../utils/helpers';

function RiskGauge({
                       value = 0,
                       maxValue = 1,
                       label,
                       size = 'md',
                       showValue = true,
                       animated = true,
                       className,
                   }) {
    const percentage = Math.min(Math.max((value / maxValue) * 100, 0), 100);

    const sizes = {
        sm: { width: 100, height: 60, strokeWidth: 8, fontSize: 'text-lg' },
        md: { width: 140, height: 80, strokeWidth: 10, fontSize: 'text-2xl' },
        lg: { width: 180, height: 100, strokeWidth: 12, fontSize: 'text-3xl' },
    };

    const config = sizes[size];
    const radius = (config.width - config.strokeWidth) / 2;
    const circumference = Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    const riskLevel = useMemo(() => {
        if (percentage < 30) return { label: 'Low', color: 'text-success-500', stroke: '#22c55e', bg: 'bg-success-50' };
        if (percentage < 50) return { label: 'Medium', color: 'text-warning-500', stroke: '#eab308', bg: 'bg-warning-50' };
        if (percentage < 70) return { label: 'High', color: 'text-accent-500', stroke: '#f97316', bg: 'bg-accent-50' };
        if (percentage < 85) return { label: 'Severe', color: 'text-crisis-500', stroke: '#ef4444', bg: 'bg-crisis-50' };
        return { label: 'Critical', color: 'text-crisis-600', stroke: '#dc2626', bg: 'bg-crisis-100' };
    }, [percentage]);

    return (
        <div className={cn('flex flex-col items-center', className)}>
            <div className="relative" style={{ width: config.width, height: config.height }}>
                <svg
                    width={config.width}
                    height={config.height}
                    viewBox={`0 0 ${config.width} ${config.height + 10}`}
                    className="transform -rotate-0"
                >
                    {/* Background arc */}
                    <path
                        d={`M ${config.strokeWidth / 2} ${config.height} A ${radius} ${radius} 0 0 1 ${config.width - config.strokeWidth / 2} ${config.height}`}
                        fill="none"
                        stroke="#e5e5e5"
                        strokeWidth={config.strokeWidth}
                        strokeLinecap="round"
                    />
                    {/* Progress arc */}
                    <path
                        d={`M ${config.strokeWidth / 2} ${config.height} A ${radius} ${radius} 0 0 1 ${config.width - config.strokeWidth / 2} ${config.height}`}
                        fill="none"
                        stroke={riskLevel.stroke}
                        strokeWidth={config.strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        className={cn(animated && 'transition-all duration-1000 ease-out')}
                    />
                </svg>

                {/* Value display */}
                {showValue && (
                    <div className="absolute inset-0 flex items-end justify-center pb-1">
            <span className={cn('font-bold font-display', config.fontSize, riskLevel.color)}>
              {Math.round(percentage)}%
            </span>
                    </div>
                )}
            </div>

            {/* Label */}
            {label && (
                <div className="mt-2 text-center">
                    <p className="text-sm font-medium text-neutral-700">{label}</p>
                    <p className={cn('text-xs font-medium', riskLevel.color)}>{riskLevel.label} Risk</p>
                </div>
            )}
        </div>
    );
}

export default RiskGauge;