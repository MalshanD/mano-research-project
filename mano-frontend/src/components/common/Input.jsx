import { forwardRef, useState } from 'react';
import { cn } from '../../utils/helpers';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

const Input = forwardRef(
    (
        {
            label,
            error,
            hint,
            leftIcon,
            rightIcon,
            type = 'text',
            size = 'md',
            className,
            containerClassName,
            disabled = false,
            required = false,
            showPasswordToggle = true,
            ...props
        },
        ref
    ) => {
        const [showPassword, setShowPassword] = useState(false);
        const isPassword = type === 'password';
        const inputType = isPassword && showPassword ? 'text' : type;

        const sizes = {
            sm: 'px-3 py-2 text-sm',
            md: 'px-4 py-3 text-base',
            lg: 'px-5 py-4 text-lg',
        };

        return (
            <div className={cn('w-full', containerClassName)}>
                {label && (
                    <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                        {label}
                        {required && <span className="text-crisis-500 ml-1">*</span>}
                    </label>
                )}

                <div className="relative">
                    {leftIcon && (
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-neutral-400">{leftIcon}</span>
                        </div>
                    )}

                    <input
                        ref={ref}
                        type={inputType}
                        disabled={disabled}
                        className={cn(
                            'w-full bg-white dark:bg-neutral-900 border rounded-xl text-neutral-800 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500',
                            'transition-all duration-200',
                            'focus:outline-none focus:ring-2 focus:ring-offset-0',
                            'disabled:bg-neutral-50 dark:disabled:bg-neutral-800 disabled:cursor-not-allowed disabled:text-neutral-500 dark:disabled:text-neutral-400',
                            error
                                ? 'border-crisis-300 focus:border-crisis-500 focus:ring-crisis-100 dark:border-crisis-400 dark:focus:border-crisis-400 dark:focus:ring-crisis-900'
                                : 'border-neutral-200 dark:border-neutral-700 focus:border-primary-500 dark:focus:border-primary-400 focus:ring-primary-100 dark:focus:ring-primary-900',
                            sizes[size],
                            leftIcon && 'pl-10',
                            (rightIcon || isPassword) && 'pr-10',
                            className
                        )}
                        {...props}
                    />

                    {isPassword && showPasswordToggle ? (
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-neutral-400 hover:text-neutral-600 transition-colors"
                            tabIndex={-1}
                        >
                            {showPassword ? (
                                <EyeSlashIcon className="h-5 w-5" />
                            ) : (
                                <EyeIcon className="h-5 w-5" />
                            )}
                        </button>
                    ) : rightIcon ? (
                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                            <span className="text-neutral-400">{rightIcon}</span>
                        </div>
                    ) : null}
                </div>

                {(error || hint) && (
                    <p className={cn(
                        'mt-1.5 text-sm',
                        error ? 'text-crisis-500' : 'text-neutral-500'
                    )}>
                        {error || hint}
                    </p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';

export default Input;