import { cn } from '../../../utils/helpers';
import { Card, CardHeader, CardTitle } from '../../common';
import {
    CalendarDaysIcon,
    FireIcon,
    ChatBubbleLeftRightIcon,
    ClipboardDocumentCheckIcon,
    SparklesIcon,
    TrophyIcon,
} from '@heroicons/react/24/outline';

function ProfileStats({ stats, className }) {
    const statItems = [
        {
            icon: CalendarDaysIcon,
            label: 'Days Active',
            value: stats?.daysActive || 0,
            color: 'text-primary-600',
            bg: 'bg-primary-50',
        },
        {
            icon: FireIcon,
            label: 'Current Streak',
            value: stats?.currentStreak || 0,
            suffix: 'days',
            color: 'text-accent-600',
            bg: 'bg-accent-50',
        },
        {
            icon: TrophyIcon,
            label: 'Longest Streak',
            value: stats?.longestStreak || 0,
            suffix: 'days',
            color: 'text-warning-600',
            bg: 'bg-warning-50',
        },
        {
            icon: ClipboardDocumentCheckIcon,
            label: 'Assessments',
            value: stats?.assessmentsCompleted || 0,
            color: 'text-purple-600',
            bg: 'bg-purple-50',
        },
        {
            icon: ChatBubbleLeftRightIcon,
            label: 'Chat Sessions',
            value: stats?.chatSessions || 0,
            color: 'text-success-600',
            bg: 'bg-success-50',
        },
        {
            icon: SparklesIcon,
            label: 'Activities',
            value: stats?.activitiesCompleted || 0,
            color: 'text-crisis-600',
            bg: 'bg-crisis-50',
        },
    ];

    return (
        <Card className={className}>
            <CardHeader>
                <CardTitle>Your Progress</CardTitle>
            </CardHeader>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {statItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <div
                            key={item.label}
                            className="flex items-center gap-3 p-3 rounded-xl bg-neutral-50"
                        >
                            <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', item.bg)}>
                                <Icon className={cn('w-5 h-5', item.color)} />
                            </div>
                            <div>
                                <p className="text-lg font-bold text-neutral-900">
                                    {item.value}
                                    {item.suffix && (
                                        <span className="text-sm font-normal text-neutral-500 ml-1">
                      {item.suffix}
                    </span>
                                    )}
                                </p>
                                <p className="text-xs text-neutral-500">{item.label}</p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}

export default ProfileStats;