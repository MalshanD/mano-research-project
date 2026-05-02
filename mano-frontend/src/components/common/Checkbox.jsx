import { forwardRef, useRef, useState, useCallback } from 'react';
import { cn } from '../../utils/helpers';

const Checkbox = forwardRef(
    (
        {
            label,
            description,
            error,
            className,
            containerClassName,
            disabled = false,
            id,
            onChange,
            defaultChecked,
            checked: controlledChecked,
            ...props
        },
        ref
    ) => {
        const internalRef = useRef(null);
        const inputRef = ref || internalRef;

        // Support both controlled (checked prop) and uncontrolled (react-hook-form register)
        const [internalChecked, setInternalChecked] = useState(defaultChecked ?? false);
        const isControlled = controlledChecked !== undefined;
        const isChecked = isControlled ? controlledChecked : internalChecked;

        const handleChange = useCallback((e) => {
            if (!isControlled) setInternalChecked(e.target.checked);
            onChange?.(e);
        }, [isControlled, onChange]);

        const inputId = id || `chk-${label?.replace(/\W+/g, '-').toLowerCase() ?? Math.random().toString(36).slice(2)}`;

        return (
            <div className={cn('w-full', containerClassName)}>
                <label
                    htmlFor={inputId}
                    className={cn(
                        'flex items-start gap-3 w-full',
                        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
                    )}
                >
                    {/* Hidden real input — react-hook-form registers here */}
                    <input
                        ref={inputRef}
                        id={inputId}
                        type="checkbox"
                        disabled={disabled}
                        checked={isChecked}
                        onChange={handleChange}
                        style={{ position: 'absolute', opacity: 0, width: 0, height: 0, margin: 0 }}
                        className={className}
                        {...props}
                    />

                    {/* Custom visual checkbox */}
                    <span
                        className={cn(
                            'flex-shrink-0 mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-150 select-none',
                            isChecked
                                ? 'bg-primary-500 border-primary-500'
                                : error
                                    ? 'bg-white border-crisis-400'
                                    : 'bg-white border-neutral-300',
                            !disabled && !isChecked && 'group-hover:border-primary-400',
                        )}
                        aria-hidden="true"
                    >
                        {/* Checkmark SVG */}
                        <svg
                            className={cn(
                                'w-3 h-3 text-white transition-all duration-150',
                                isChecked ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
                            )}
                            viewBox="0 0 12 12"
                            fill="none"
                        >
                            <path
                                d="M2 6l3 3 5-5"
                                stroke="currentColor"
                                strokeWidth="2.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                        </svg>
                    </span>

                    {/* Text */}
                    {(label || description) && (
                        <span className="flex flex-col gap-0.5 min-w-0">
                            {label && (
                                <span className={cn(
                                    'text-sm font-medium leading-snug',
                                    disabled ? 'text-neutral-400' : 'text-neutral-700'
                                )}>
                                    {label}
                                </span>
                            )}
                            {description && (
                                <span className="text-xs text-neutral-500 leading-snug">{description}</span>
                            )}
                        </span>
                    )}
                </label>

                {/* Error message */}
                {error && (
                    <p className="mt-1 ml-8 text-xs text-crisis-500 font-medium">{error}</p>
                )}
            </div>
        );
    }
);

Checkbox.displayName = 'Checkbox';

export default Checkbox;