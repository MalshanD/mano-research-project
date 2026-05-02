import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import { CrisisModal } from './index';
import { runSafetyCheck, resolveCrisisAlert } from '../../../api/client';
import {
    ShieldExclamationIcon,
    HeartIcon,
    XMarkIcon,
    PhoneIcon,
    CheckCircleIcon,
} from '@heroicons/react/24/outline';

const SEVERITY_STYLES = {
    critical: {
        bg: 'bg-red-50',
        border: 'border-red-300',
        icon: 'bg-red-100 text-red-600',
        title: 'text-red-900',
        text: 'text-red-700',
        badge: 'bg-red-500 text-white',
        badgeLabel: 'Critical',
    },
    high: {
        bg: 'bg-crisis-50',
        border: 'border-crisis-300',
        icon: 'bg-crisis-100 text-crisis-600',
        title: 'text-crisis-900',
        text: 'text-crisis-700',
        badge: 'bg-crisis-500 text-white',
        badgeLabel: 'High',
    },
    medium: {
        bg: 'bg-warning-50',
        border: 'border-warning-300',
        icon: 'bg-warning-100 text-warning-600',
        title: 'text-warning-900',
        text: 'text-warning-700',
        badge: 'bg-warning-500 text-white',
        badgeLabel: 'Moderate',
    },
    low: {
        bg: 'bg-primary-50',
        border: 'border-primary-200',
        icon: 'bg-primary-100 text-primary-600',
        title: 'text-primary-900',
        text: 'text-primary-700',
        badge: 'bg-primary-500 text-white',
        badgeLabel: 'Notice',
    },
};

function CrisisSafetyBanner({ userId, className }) {
    const [dismissed, setDismissed] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const queryClient = useQueryClient();

    const { data: safetyData } = useQuery({
        queryKey: ['safetyCheck', userId],
        queryFn: async () => {
            const { data, error } = await runSafetyCheck(userId);
            if (error) throw new Error(error);
            return data;
        },
        enabled: !!userId,
        staleTime: 5 * 60 * 1000,
        refetchInterval: 5 * 60 * 1000,
    });

    const resolveMutation = useMutation({
        mutationFn: async (alertId) => {
            const { data, error } = await resolveCrisisAlert(alertId);
            if (error) throw new Error(error);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['safetyCheck', userId]);
        },
    });

    // Don't render if safe, no data, or dismissed
    if (dismissed || !safetyData || safetyData.safety_status === 'safe' || safetyData.overall_risk_level === 'none') {
        return null;
    }

    const severity = safetyData.overall_risk_level;
    const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.low;
    const isCritical = severity === 'critical' || severity === 'high';

    return (
        <>
            <div
                className={cn(
                    'rounded-2xl border-2 overflow-hidden animate-fade-in',
                    style.bg,
                    style.border,
                    className
                )}
            >
                {/* Severity bar */}
                <div className={cn('px-4 py-1.5 flex items-center justify-between', style.badge)}>
                    <div className="flex items-center gap-1.5">
                        <ShieldExclamationIcon className="w-4 h-4" />
                        <span className="text-xs font-semibold">{style.badgeLabel} Safety Alert</span>
                    </div>
                    <span className="text-xs opacity-80">
                        {safetyData.active_alerts} active alert{safetyData.active_alerts !== 1 ? 's' : ''}
                    </span>
                </div>

                <div className="p-4">
                    <div className="flex items-start gap-3">
                        <div className={cn('w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0', style.icon)}>
                            <HeartIcon className="w-5 h-5" />
                        </div>

                        <div className="flex-1">
                            <h4 className={cn('font-semibold mb-1', style.title)}>
                                {isCritical ? "We're concerned about you" : "We've noticed something"}
                            </h4>
                            <p className={cn('text-sm mb-3', style.text)}>
                                {safetyData.support_message || "We're here to support you. You don't have to go through this alone."}
                            </p>

                            {/* Resources (for critical/high) */}
                            {isCritical && safetyData.resources?.length > 0 && (
                                <div className="bg-white/60 rounded-xl p-3 mb-3 space-y-2">
                                    <p className={cn('text-xs font-semibold', style.title)}>Immediate Support</p>
                                    {safetyData.resources.map((r, i) => (
                                        <div key={i} className="flex items-center gap-2">
                                            <PhoneIcon className="w-3.5 h-3.5 text-neutral-500" />
                                            <a
                                                href={`tel:${r.number}`}
                                                className={cn('text-sm font-medium hover:underline', style.title)}
                                            >
                                                {r.name}: {r.number}
                                            </a>
                                            <span className="text-xs text-neutral-500">({r.available})</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex items-center gap-2 flex-wrap">
                                <Button
                                    variant={isCritical ? 'danger' : 'primary'}
                                    size="sm"
                                    onClick={() => setShowModal(true)}
                                >
                                    <PhoneIcon className="w-4 h-4 mr-1" />
                                    Get Support
                                </Button>

                                {!isCritical && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setDismissed(true)}
                                        className={style.text}
                                    >
                                        I'm doing okay
                                    </Button>
                                )}

                                {safetyData.recent_alerts?.length > 0 && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            // Resolve all active alerts
                                            safetyData.recent_alerts
                                                .filter(a => a.is_active)
                                                .forEach(a => resolveMutation.mutate(a.id));
                                            setDismissed(true);
                                        }}
                                        className="text-neutral-500"
                                    >
                                        <CheckCircleIcon className="w-4 h-4 mr-1" />
                                        Mark Resolved
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Close (only for non-critical) */}
                        {!isCritical && (
                            <button
                                onClick={() => setDismissed(true)}
                                className={cn('p-1 transition-colors', style.text, 'hover:opacity-70')}
                            >
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <CrisisModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}

export default CrisisSafetyBanner;
