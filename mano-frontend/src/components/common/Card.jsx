import { forwardRef } from 'react';
import { cn } from '../../utils/helpers';

const Card = forwardRef(
    (
        {
            children,
            className,
            variant = 'default',
            padding = 'md',
            hover = false,
            onClick,
            ...props
        },
        ref
    ) => {
        const variants = {
            default: 'bg-white border border-sand/40',
            elevated: 'bg-white shadow-organic-lg',
            outlined: 'bg-white border-2 border-sand/60',
            ghost: 'bg-cream/30',
            gradient: 'bg-gradient-to-br from-white to-cream/40 border border-sand/40',
        };

        const paddings = {
            none: 'p-0',
            sm: 'p-4',
            md: 'p-6',
            lg: 'p-8',
        };

        const isClickable = !!onClick;

        return (
            <div
                ref={ref}
                onClick={onClick}
                className={cn(
                    'rounded-3xl shadow-organic transition-all duration-300',
                    variants[variant],
                    paddings[padding],
                    hover && 'hover:shadow-organic-hover hover:-translate-y-1',
                    isClickable && 'cursor-pointer',
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);

Card.displayName = 'Card';

// Card Header
export const CardHeader = ({ children, className, ...props }) => (
    <div className={cn('mb-4', className)} {...props}>
        {children}
    </div>
);

// Card Title
export const CardTitle = ({ children, className, as: Component = 'h3', ...props }) => (
    <Component
        className={cn('text-lg font-semibold text-neutral-900', className)}
        {...props}
    >
        {children}
    </Component>
);

// Card Description
export const CardDescription = ({ children, className, ...props }) => (
    <p className={cn('text-sm text-neutral-500 mt-1', className)} {...props}>
        {children}
    </p>
);

// Card Content
export const CardContent = ({ children, className, ...props }) => (
    <div className={cn('', className)} {...props}>
        {children}
    </div>
);

// Card Footer
export const CardFooter = ({ children, className, ...props }) => (
    <div className={cn('mt-4 pt-4 border-t border-sand/30', className)} {...props}>
        {children}
    </div>
);

export default Card;