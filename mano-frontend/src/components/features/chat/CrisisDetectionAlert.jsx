import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import { CrisisModal } from '../crisis';
import {
    ExclamationTriangleIcon,
    XMarkIcon,
    HeartIcon,
    PhoneIcon,
    ShieldExclamationIcon,
} from '@heroicons/react/24/outline';

const SEVERITY_CONFIG = {
    critical: {
        bg: 'bg-red-50 border-red-300',
        iconBg: 'bg-red-100',
        iconColor: 'text-red-600',
        title: 'Please reach out for help right now',
        titleColor: 'text-red-900',
        textColor: 'text-red-700',
        btnVariant: 'danger',
    },
    high: {
        bg: 'bg-crisis-50 border-crisis-300',
        iconBg: 'bg-crisis-100',
        iconColor: 'text-crisis-600',
        title: "We're here for you",
        titleColor: 'text-crisis-900',
        textColor: 'text-crisis-700',
        btnVariant: 'danger',
    },
    medium: {
        bg: 'bg-warning-50 border-warning-200',
        iconBg: 'bg-warning-100',
        iconColor: 'text-warning-600',
        title: "We're here for you",
        titleColor: 'text-warning-900',
        textColor: 'text-warning-700',
        btnVariant: 'primary',
    },
    low: {
        bg: 'bg-primary-50 border-primary-200',
        iconBg: 'bg-primary-100',
        iconColor: 'text-primary-600',
        title: "We noticed you might be struggling",
        titleColor: 'text-primary-900',
        textColor: 'text-primary-700',
        btnVariant: 'primary',
    },
};

function CrisisDetectionAlert({
    show = false,
    crisisAlert = null,
    onDismiss,
    onGetHelp,
    className,
}) {
    const [showModal, setShowModal] = useState(false);

    if (!show) return null;

    const severity = crisisAlert?.severity || 'medium';
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
    const isCritical = severity === 'critical' || severity === 'high';
    const supportMessage = crisisAlert?.message;
    const resources = crisisAlert?.resources || [];

    const handleGetHelp = () => {
        setShowModal(true);
        onGetHelp?.();
    };

    return (
        <>
            <div
                className={cn(
                    'mx-4 my-2 p-4 rounded-xl border-2 animate-fade-in',
                    config.bg,
                    className
                )}
            >
                <div className="flex items-start gap-3">
                    <div className={cn('w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0', config.iconBg)}>
                        {isCritical ? (
                            <ShieldExclamationIcon className={cn('w-5 h-5', config.iconColor)} />
                        ) : (
                            <HeartIcon className={cn('w-5 h-5', config.iconColor)} />
                        )}
                    </div>

                    <div className="flex-1">
                        <h4 className={cn('font-semibold mb-1', config.titleColor)}>
                            {config.title}
                        </h4>
                        <p className={cn('text-sm mb-3', config.textColor)}>
                            {supportMessage ||
                                "It sounds like you might be going through a difficult time. Remember, it's okay to reach out for help. You're not alone."}
                        </p>

                        {/* Show resources inline for critical/high */}
                        {isCritical && resources.length > 0 && (
                            <div className="bg-white/50 rounded-lg p-2.5 mb-3 space-y-1.5">
                                {resources.map((r, i) => (
                                    <div key={i} className="flex items-center gap-2">
                                        <PhoneIcon className="w-3.5 h-3.5 text-neutral-500" />
                                        <a
                                            href={`tel:${r.number}`}
                                            className={cn('text-sm font-medium hover:underline', config.titleColor)}
                                        >
                                            {r.name}: {r.number}
                                        </a>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex items-center gap-2">
                            <Button
                                variant={config.btnVariant}
                                size="sm"
                                onClick={handleGetHelp}
                            >
                                Get Support Now
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onDismiss}
                                className={config.textColor}
                            >
                                I'm okay
                            </Button>
                        </div>
                    </div>

                    {!isCritical && (
                        <button
                            onClick={onDismiss}
                            className={cn('p-1 transition-colors', config.textColor, 'hover:opacity-70')}
                        >
                            <XMarkIcon className="w-5 h-5" />
                        </button>
                    )}
                </div>
            </div>

            <CrisisModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}

export default CrisisDetectionAlert;
