import { forwardRef } from 'react';
import { cn } from '../../utils/helpers';

const Textarea = forwardRef(
    (
        {
            label,
            error,
            hint,
            className,
            containerClassName,
            disabled = false,
            required = false,
            rows = 4,
            resize = 'vertical',
            ...props
        },
        ref
    ) => {
        const resizeClasses = {
            none: 'resize-none',
            vertical: 'resize-y',
            horizontal: 'resize-x',
            both: 'resize',
        };

        return (
            <div className={cn('w-full', containerClassName)}>
                {label && (
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                        {label}
                        {required && <span className="text-crisis-500 ml-1">*</span>}
                    </label>
                )}

                <textarea
                    ref={ref}
                    rows={rows}
                    disabled={disabled}
                    className={cn(
                        'w-full px-4 py-3 bg-white border rounded-xl text-neutral-800 placeholder-neutral-400',
                        'transition-all duration-200',
                        'focus:outline-none focus:ring-2 focus:ring-offset-0',
                        'disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:text-neutral-500',
                        error
                            ? 'border-crisis-300 focus:border-crisis-500 focus:ring-crisis-100'
                            : 'border-neutral-200 focus:border-primary-500 focus:ring-primary-100',
                        resizeClasses[resize],
                        className
                    )}
                    {...props}
                />

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

Textarea.displayName = 'Textarea';

export default Textarea;