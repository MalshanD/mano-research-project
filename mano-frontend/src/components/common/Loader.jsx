import { cn } from '../../utils/helpers';

const sizes = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12',
};

const colors = {
    primary: 'text-primary-500',
    white: 'text-white',
    neutral: 'text-neutral-500',
    success: 'text-success-500',
    danger: 'text-crisis-500',
};

function Loader({ size = 'md', color = 'primary', className, ...props }) {
    return (
        <svg
            className={cn('animate-spin', sizes[size], colors[color], className)}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            {...props}
        >
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
        </svg>
    );
}

// Full page loader
export function PageLoader({ message = 'Loading...' }) {
    return (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center z-50">
            <div className="w-16 h-16 mb-4 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-glow animate-pulse">
                <span className="text-2xl font-bold text-white font-display">M</span>
            </div>
            <Loader size="lg" />
            <p className="mt-4 text-neutral-600 animate-pulse">{message}</p>
        </div>
    );
}

// Skeleton loader
export function Skeleton({ className, ...props }) {
    return (
        <div
            className={cn('animate-pulse bg-neutral-200 rounded', className)}
            {...props}
        />
    );
}

// Content loader with skeleton
export function ContentLoader({ lines = 3, avatar = false }) {
    return (
        <div className="animate-pulse">
            {avatar && (
                <div className="flex items-center mb-4">
                    <div className="w-10 h-10 bg-neutral-200 rounded-full" />
                    <div className="ml-3 flex-1">
                        <div className="h-4 bg-neutral-200 rounded w-1/3" />
                        <div className="h-3 bg-neutral-200 rounded w-1/4 mt-2" />
                    </div>
                </div>
            )}
            <div className="space-y-3">
                {Array.from({ length: lines }).map((_, i) => (
                    <div
                        key={i}
                        className="h-4 bg-neutral-200 rounded"
                        style={{ width: `${Math.random() * 40 + 60}%` }}
                    />
                ))}
            </div>
        </div>
    );
}

export default Loader;