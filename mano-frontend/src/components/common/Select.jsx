import { forwardRef } from 'react';
import { cn } from '../../utils/helpers';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

const Select = forwardRef(
    (
        {
            label,
            error,
            hint,
            options = [],
            placeholder = 'Select an option',
            size = 'md',
            className,
            containerClassName,
            disabled = false,
            required = false,
            ...props
        },
        ref
    ) => {
        const sizes = {
            sm: 'px-3 py-2 text-sm',
            md: 'px-4 py-3 text-base',
            lg: 'px-5 py-4 text-lg',
        };

        return (
            <div className={cn('w-full', containerClassName)}>
                {label && (
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                        {label}
                        {required && <span className="text-crisis-500 ml-1">*</span>}
                    </label>
                )}

                <div className="relative">
                    <select
                        ref={ref}
                        disabled={disabled}
                        className={cn(
                            'w-full bg-white border rounded-xl text-neutral-800 appearance-none cursor-pointer',
                            'transition-all duration-200',
                            'focus:outline-none focus:ring-2 focus:ring-offset-0',
                            'disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:text-neutral-500',
                            error
                                ? 'border-crisis-300 focus:border-crisis-500 focus:ring-crisis-100'
                                : 'border-neutral-200 focus:border-primary-500 focus:ring-primary-100',
                            sizes[size],
                            'pr-10',
                            className
                        )}
                        {...props}
                    >
                        {placeholder && (
                            <option value="" disabled>
                                {placeholder}
                            </option>
                        )}
                        {options.map((option) => (
                            <option
                                key={option.value}
                                value={option.value}
                                disabled={option.disabled}
                            >
                                {option.label}
                            </option>
                        ))}
                    </select>

                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <ChevronDownIcon className="h-5 w-5 text-neutral-400" />
                    </div>
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

Select.displayName = 'Select';

export default Select;