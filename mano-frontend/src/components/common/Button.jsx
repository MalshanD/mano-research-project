import { forwardRef } from 'react';
import { cn } from '../../utils/helpers';
import Loader from './Loader';

const variants = {
    primary: 'bg-primary-500 text-white hover:bg-primary-600 active:bg-primary-700 focus-visible:ring-primary-500',
    secondary: 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200 active:bg-neutral-300 focus-visible:ring-neutral-500',
    outline: 'border-2 border-primary-500 text-primary-600 bg-transparent hover:bg-primary-50 active:bg-primary-100 focus-visible:ring-primary-500',
    ghost: 'text-neutral-600 bg-transparent hover:bg-neutral-100 active:bg-neutral-200 focus-visible:ring-neutral-500',
    danger: 'bg-crisis-500 text-white hover:bg-crisis-600 active:bg-crisis-700 focus-visible:ring-crisis-500',
    success: 'bg-success-500 text-white hover:bg-success-600 active:bg-success-700 focus-visible:ring-success-500',
    warning: 'bg-warning-500 text-white hover:bg-warning-600 active:bg-warning-700 focus-visible:ring-warning-500',
    link: 'text-primary-600 bg-transparent hover:text-primary-700 hover:underline p-0',
};

const sizes = {
    xs: 'px-2.5 py-1 text-xs rounded-lg gap-1',
    sm: 'px-3 py-1.5 text-sm rounded-lg gap-1.5',
    md: 'px-4 py-2.5 text-sm rounded-xl gap-2',
    lg: 'px-6 py-3 text-base rounded-xl gap-2',
    xl: 'px-8 py-4 text-lg rounded-2xl gap-3',
    icon: 'p-2.5 rounded-xl',
    'icon-sm': 'p-2 rounded-lg',
    'icon-lg': 'p-3 rounded-xl',
};

const Button = forwardRef(
    (
        {
            children,
            variant = 'primary',
            size = 'md',
            className,
            disabled = false,
            loading = false,
            leftIcon,
            rightIcon,
            fullWidth = false,
            type = 'button',
            as: Component = 'button',
            ...props
        },
        ref
    ) => {
        const isDisabled = disabled || loading;

        return (
            <Component
                ref={ref}
                type={Component === 'button' ? type : undefined}
                disabled={Component === 'button' ? isDisabled : undefined}
                className={cn(
                    'inline-flex items-center justify-center font-medium transition-all duration-200',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
                    'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
                    isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none',
                    variants[variant],
                    sizes[size],
                    fullWidth && 'w-full',
                    className
                )}
                {...props}
            >
                {loading ? (
                    <>
                        <Loader size="sm" color={variant === 'primary' || variant === 'danger' || variant === 'success' ? 'white' : 'primary'} />
                        <span className="ml-2">{children}</span>
                    </>
                ) : (
                    <>
                        {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
                        {children}
                        {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
                    </>
                )}
            </Component>
        );
    }
);

Button.displayName = 'Button';

export default Button;