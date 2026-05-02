import { useMemo } from 'react';
import { cn } from '../../utils/helpers';

function PasswordStrength({ password = '' }) {
    const strength = useMemo(() => {
        if (!password) return { score: 0, label: '', color: '' };

        let score = 0;
        const checks = {
            length: password.length >= 6,
            lowercase: /[a-z]/.test(password),
            uppercase: /[A-Z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[^A-Za-z0-9]/.test(password),
        };

        Object.values(checks).forEach((passed) => {
            if (passed) score++;
        });

        const levels = [
            { score: 0, label: '', color: '' },
            { score: 1, label: 'Very Weak', color: 'bg-crisis-500' },
            { score: 2, label: 'Weak', color: 'bg-warning-500' },
            { score: 3, label: 'Fair', color: 'bg-warning-400' },
            { score: 4, label: 'Good', color: 'bg-success-400' },
            { score: 5, label: 'Strong', color: 'bg-success-500' },
        ];

        return { ...levels[score], checks };
    }, [password]);

    if (!password) return null;

    return (
        <div className="mt-2 space-y-2">
            {/* Strength Bar */}
            <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((level) => (
                    <div
                        key={level}
                        className={cn(
                            'h-1 flex-1 rounded-full transition-all duration-300',
                            level <= strength.score ? strength.color : 'bg-neutral-200'
                        )}
                    />
                ))}
            </div>

            {/* Label */}
            <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-500">Password strength:</span>
                <span
                    className={cn(
                        'text-xs font-medium',
                        strength.score <= 2 && 'text-crisis-600',
                        strength.score === 3 && 'text-warning-600',
                        strength.score >= 4 && 'text-success-600'
                    )}
                >
          {strength.label}
        </span>
            </div>

            {/* Requirements */}
            {strength.checks && (
                <div className="grid grid-cols-2 gap-1 text-xs">
                    <RequirementItem met={strength.checks.length} text="6+ characters" />
                    <RequirementItem met={strength.checks.lowercase} text="Lowercase letter" />
                    <RequirementItem met={strength.checks.uppercase} text="Uppercase letter" />
                    <RequirementItem met={strength.checks.number} text="Number" />
                    <RequirementItem met={strength.checks.special} text="Special character" />
                </div>
            )}
        </div>
    );
}

function RequirementItem({ met, text }) {
    return (
        <div className={cn('flex items-center gap-1.5', met ? 'text-success-600' : 'text-neutral-400')}>
            {met ? (
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                    />
                </svg>
            ) : (
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                    />
                </svg>
            )}
            <span>{text}</span>
        </div>
    );
}

export default PasswordStrength;