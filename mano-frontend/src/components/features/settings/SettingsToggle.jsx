import { cn } from '../../../utils/helpers';
import { Switch } from '@headlessui/react';

function SettingsToggle({
                            label,
                            description,
                            checked,
                            onChange,
                            disabled = false,
                            className,
                        }) {
    return (
        <div className={cn('flex items-center justify-between py-3', className)}>
            <div className="flex-1 pr-4">
                <p className={cn('font-medium', disabled ? 'text-neutral-400' : 'text-neutral-900')}>
                    {label}
                </p>
                {description && (
                    <p className="text-sm text-neutral-500 mt-0.5">{description}</p>
                )}
            </div>
            <Switch
                checked={checked}
                onChange={onChange}
                disabled={disabled}
                className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    checked ? 'bg-primary-500' : 'bg-neutral-300',
                    disabled && 'opacity-50 cursor-not-allowed'
                )}
            >
        <span
            className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                checked ? 'translate-x-6' : 'translate-x-1'
            )}
        />
            </Switch>
        </div>
    );
}

export default SettingsToggle;