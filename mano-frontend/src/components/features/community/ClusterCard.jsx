import { cn } from '../../../utils/helpers';
import { Card, Badge } from '../../common';
import { UserGroupIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

const clusterColors = {
    success: {
        bg: 'bg-success-50',
        border: 'border-success-200',
        text: 'text-success-700',
        badge: 'success',
    },
    primary: {
        bg: 'bg-primary-50',
        border: 'border-primary-200',
        text: 'text-primary-700',
        badge: 'primary',
    },
    warning: {
        bg: 'bg-warning-50',
        border: 'border-warning-200',
        text: 'text-warning-700',
        badge: 'warning',
    },
    accent: {
        bg: 'bg-accent-50',
        border: 'border-accent-200',
        text: 'text-accent-700',
        badge: 'warning',
    },
    danger: {
        bg: 'bg-crisis-50',
        border: 'border-crisis-200',
        text: 'text-crisis-700',
        badge: 'danger',
    },
};

function ClusterCard({
                         cluster,
                         isUserCluster = false,
                         onClick,
                         compact = false,
                         className,
                     }) {
    const colors = clusterColors[cluster.color] || clusterColors.primary;

    if (compact) {
        return (
            <div
                onClick={onClick}
                className={cn(
                    'flex items-center gap-3 p-3 rounded-xl border transition-all',
                    colors.bg,
                    colors.border,
                    onClick && 'cursor-pointer hover:shadow-soft',
                    className
                )}
            >
                <span className="text-2xl">{cluster.icon}</span>
                <div className="flex-1 min-w-0">
                    <p className={cn('font-medium', colors.text)}>{cluster.name}</p>
                    <p className="text-xs text-neutral-500">{cluster.memberCount} members</p>
                </div>
                {isUserCluster && (
                    <CheckCircleIcon className={cn('w-5 h-5', colors.text)} />
                )}
            </div>
        );
    }

    return (
        <Card
            onClick={onClick}
            hover={!!onClick}
            className={cn(
                'relative overflow-hidden',
                isUserCluster && `border-2 ${colors.border}`,
                className
            )}
        >
            {isUserCluster && (
                <div className={cn('absolute top-0 right-0 px-3 py-1 text-xs font-medium rounded-bl-xl', colors.bg, colors.text)}>
                    Your Community
                </div>
            )}

            <div className="flex items-start gap-4">
                <div className={cn('w-14 h-14 rounded-2xl flex items-center justify-center text-2xl', colors.bg)}>
                    {cluster.icon}
                </div>

                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-neutral-900">{cluster.name}</h3>
                        <Badge variant={colors.badge} size="sm">
                            <UserGroupIcon className="w-3 h-3 mr-1" />
                            {cluster.memberCount?.toLocaleString()}
                        </Badge>
                    </div>

                    <p className="text-sm text-neutral-600 mb-3">{cluster.description}</p>

                    {cluster.characteristics && (
                        <div className="flex flex-wrap gap-2">
                            {cluster.characteristics.map((char, index) => (
                                <span
                                    key={index}
                                    className={cn('px-2 py-0.5 text-xs rounded-full', colors.bg, colors.text)}
                                >
                  {char}
                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </Card>
    );
}

export default ClusterCard;