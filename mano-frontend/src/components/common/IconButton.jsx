import { forwardRef } from 'react';
import { cn } from '../../utils/helpers';
import Tooltip from './Tooltip';

const variants = {
    primary: 'bg-primary-500 text-white hover:bg-primary-600 active:bg-primary-700',
    secondary: 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200 active:bg-neutral-300',
    ghost: 'text-neutral-600 hover:bg-neutral-100 active:bg-neutral-200',
    danger: 'bg-crisis-500 text-white hover:bg-crisis-600 active:bg-crisis-700',
    'ghost-danger': 'text-crisis-600 hover:bg-crisis-50 active:bg-crisis-100',
};

const sizes = {
    xs: 'p-1',
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-2.5',
    xl: 'p-3',
};

const iconSizes = {
    xs: 'w-4 h-4',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-7 h-7',
};

const IconButton = forwardRef(
    (
        {
            icon,
            variant = 'ghost',
            size = 'md',
            tooltip,
            tooltipPosition = 'top',
            className,
            disabled = false,
            ...props
        },
        ref
    ) => {
        const button = (
            <button
                ref={ref}
                disabled={disabled}
                className={cn(
                    'inline-flex items-center justify-center rounded-lg transition-all duration-200',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    variants[variant],
                    sizes[size],
                    className
                )}
                {...props}
            >
                <span className={iconSizes[size]}>{icon}</span>
            </button>
        );

        if (tooltip) {
            return (
                <Tooltip content={tooltip} position={tooltipPosition}>
                    {button}
                </Tooltip>
            );
        }

        return button;
    }
);

IconButton.displayName = 'IconButton';

export default IconButton;