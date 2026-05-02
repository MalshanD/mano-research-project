import { cn } from '../../utils/helpers';
import {
    CheckCircleIcon,
    ExclamationTriangleIcon,
    InformationCircleIcon,
    XCircleIcon,
    XMarkIcon,
} from '@heroicons/react/24/outline';

const variants = {
    info: {
        container: 'bg-blue-50 border-blue-200 text-blue-800',
        icon: 'text-blue-500',
        Icon: InformationCircleIcon,
    },
    success: {
        container: 'bg-success-50 border-success-200 text-success-800',
        icon: 'text-success-500',
        Icon: CheckCircleIcon,
    },
    warning: {
        container: 'bg-warning-50 border-warning-200 text-warning-800',
        icon: 'text-warning-500',
        Icon: ExclamationTriangleIcon,
    },
    danger: {
        container: 'bg-crisis-50 border-crisis-200 text-crisis-800',
        icon: 'text-crisis-500',
        Icon: XCircleIcon,
    },
    crisis: {
        container: 'bg-crisis-100 border-crisis-300 text-crisis-900',
        icon: 'text-crisis-600',
        Icon: ExclamationTriangleIcon,
    },
};

function Alert({
                   children,
                   title,
                   variant = 'info',
                   icon,
                   dismissible = false,
                   closePosition = 'top-right',
                   onDismiss,
                   className,
                   actions,
               }) {
    const config = variants[variant];
    const IconComponent = icon || config.Icon;

    return (
        <div
            className={cn(
                'relative rounded-xl border p-4',
                config.container,
                className
            )}
            role="alert"
        >
            <div className={cn("flex", closePosition === 'top-left' && dismissible ? "ml-6" : "")}>
                <div className="flex-shrink-0 mt-0.5">
                    <IconComponent className={cn('w-5 h-5', config.icon)} />
                </div>
                <div className="ml-3 flex-1">
                    {title && (
                        <h3 className="text-sm font-semibold mb-1">{title}</h3>
                    )}
                    <div className="text-sm">{children}</div>
                    {actions && (
                        <div className="mt-3 flex gap-2">{actions}</div>
                    )}
                </div>
                {dismissible && (
                    <button
                        onClick={onDismiss}
                        className={cn(
                            'p-1 rounded-lg hover:bg-black/5 transition-colors absolute',
                            closePosition === 'top-left' ? 'top-2 left-2' : 'top-2 right-2',
                            config.icon
                        )}
                    >
                        <XMarkIcon className="w-4 h-4" />
                    </button>
                )}
            </div>
        </div>
    );
}

// Crisis Alert - Special styling for mental health emergencies
export function CrisisAlert({ onClose, onGetHelp }) {
    return (
        <Alert
            variant="crisis"
            title="We're here for you"
            dismissible
            onDismiss={onClose}
            className="animate-fade-in"
            actions={
                <>
                    <button
                        onClick={onGetHelp}
                        className="px-3 py-1.5 bg-crisis-600 text-white text-sm font-medium rounded-lg hover:bg-crisis-700 transition-colors"
                    >
                        Get Help Now
                    </button>
                    <button
                        onClick={onClose}
                        className="px-3 py-1.5 bg-white text-crisis-700 text-sm font-medium rounded-lg hover:bg-crisis-50 transition-colors"
                    >
                        I'm Okay
                    </button>
                </>
            }
        >
            <p>
                It sounds like you might be going through a difficult time.
                Remember, you're not alone and support is available.
            </p>
        </Alert>
    );
}

export default Alert;