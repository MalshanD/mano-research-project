import { cn } from '../../utils/helpers';

const variants = {
    primary: 'bg-primary-100 text-primary-700',
    secondary: 'bg-neutral-100 text-neutral-700',
    success: 'bg-success-100 text-success-700',
    warning: 'bg-warning-100 text-warning-700',
    danger: 'bg-crisis-100 text-crisis-700',
    info: 'bg-blue-100 text-blue-700',
    // Risk level variants
    'risk-low': 'bg-success-100 text-success-700',
    'risk-medium': 'bg-warning-100 text-warning-700',
    'risk-high': 'bg-accent-100 text-accent-700',
    'risk-severe': 'bg-crisis-100 text-crisis-700',
    'risk-critical': 'bg-crisis-200 text-crisis-800',
};

const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
};

function Badge({
                   children,
                   variant = 'primary',
                   size = 'md',
                   dot = false,
                   removable = false,
                   onRemove,
                   className,
                   ...props
               }) {
    return (
        <span
            className={cn(
                'inline-flex items-center font-medium rounded-full',
                variants[variant],
                sizes[size],
                className
            )}
            {...props}
        >
      {dot && (
          <span
              className={cn(
                  'w-1.5 h-1.5 rounded-full mr-1.5',
                  variant.includes('success') && 'bg-success-500',
                  variant.includes('warning') && 'bg-warning-500',
                  variant.includes('danger') && 'bg-crisis-500',
                  variant === 'primary' && 'bg-primary-500',
                  variant === 'secondary' && 'bg-neutral-500',
                  variant === 'info' && 'bg-blue-500'
              )}
          />
      )}
            {children}
            {removable && (
                <button
                    onClick={onRemove}
                    className="ml-1 -mr-1 p-0.5 hover:bg-black/10 rounded-full transition-colors"
                >
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path
                            fillRule="evenodd"
                            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                            clipRule="evenodd"
                        />
                    </svg>
                </button>
            )}
    </span>
    );
}

// Risk Badge component
export function RiskBadge({ level, showDot = true, size = 'md' }) {
    const levelConfig = {
        LOW: { label: 'Low Risk', variant: 'risk-low' },
        MEDIUM: { label: 'Medium Risk', variant: 'risk-medium' },
        HIGH: { label: 'High Risk', variant: 'risk-high' },
        SEVERE: { label: 'Severe Risk', variant: 'risk-severe' },
        CRITICAL: { label: 'Critical', variant: 'risk-critical' },
    };

    const config = levelConfig[level] || levelConfig.LOW;

    return (
        <Badge variant={config.variant} size={size} dot={showDot}>
            {config.label}
        </Badge>
    );
}

// Status Badge component
export function StatusBadge({ status, size = 'md' }) {
    const statusConfig = {
        active: { label: 'Active', variant: 'success' },
        inactive: { label: 'Inactive', variant: 'secondary' },
        pending: { label: 'Pending', variant: 'warning' },
        resolved: { label: 'Resolved', variant: 'success' },
        escalated: { label: 'Escalated', variant: 'danger' },
    };

    const config = statusConfig[status.toLowerCase()] || { label: status, variant: 'secondary' };

    return (
        <Badge variant={config.variant} size={size} dot>
            {config.label}
        </Badge>
    );
}
export { Badge };
export default Badge ;