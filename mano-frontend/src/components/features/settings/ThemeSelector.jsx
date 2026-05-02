import { cn } from '../../../utils/helpers';
import { useTheme } from '../../../contexts/ThemeContext';
import {
    SunIcon,
    MoonIcon,
    ComputerDesktopIcon,
} from '@heroicons/react/24/outline';

const themes = [
    { id: 'light', label: 'Light', icon: SunIcon },
    { id: 'dark', label: 'Dark', icon: MoonIcon },
    { id: 'system', label: 'System', icon: ComputerDesktopIcon },
];

function ThemeSelector({ className }) {
    const { theme, setTheme } = useTheme();

    return (
        <div className={cn('grid grid-cols-3 gap-3', className)}>
            {themes.map((t) => {
                const Icon = t.icon;
                const isActive = theme === t.id;

                return (
                    <button
                        key={t.id}
                        onClick={() => setTheme(t.id)}
                        className={cn(
                            'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all',
                            isActive
                                ? 'border-primary-500 bg-primary-50'
                                : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
                        )}
                    >
                        <Icon
                            className={cn(
                                'w-6 h-6',
                                isActive ? 'text-primary-600' : 'text-neutral-500'
                            )}
                        />
                        <span
                            className={cn(
                                'text-sm font-medium',
                                isActive ? 'text-primary-700' : 'text-neutral-600'
                            )}
                        >
              {t.label}
            </span>
                    </button>
                );
            })}
        </div>
    );
}

export default ThemeSelector;