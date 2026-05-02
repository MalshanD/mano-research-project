import { Link } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Card, CardHeader, CardTitle, Badge, Button, EmptyState } from '../../common';
import {
    ChatBubbleLeftRightIcon,
    ClipboardDocumentCheckIcon,
    SparklesIcon,
    UserGroupIcon,
    ArrowRightIcon,
} from '@heroicons/react/24/outline';

const activityIcons = {
    chat: ChatBubbleLeftRightIcon,
    assessment: ClipboardDocumentCheckIcon,
    activity: SparklesIcon,
    community: UserGroupIcon,
};

const activityColors = {
    chat: 'bg-peach/40 text-terracotta',
    assessment: 'bg-cream text-terracotta-light',
    activity: 'bg-mint/40 text-sage-dark',
    community: 'bg-blush/40 text-lavender-dark',
};

function RecentActivity({ activities = [], loading = false, className }) {
    if (loading) {
        return (
            <Card className={className}>
                <CardHeader>
                    <CardTitle>Recent Activity</CardTitle>
                </CardHeader>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="animate-pulse flex items-center gap-4">
                            <div className="w-10 h-10 bg-neutral-200 rounded-lg" />
                            <div className="flex-1">
                                <div className="h-4 bg-neutral-200 rounded w-3/4 mb-2" />
                                <div className="h-3 bg-neutral-200 rounded w-1/2" />
                            </div>
                        </div>
                    ))}
                </div>
            </Card>
        );
    }

    if (activities.length === 0) {
        return (
            <Card className={className}>
                <CardHeader>
                    <CardTitle>Recent Activity</CardTitle>
                </CardHeader>
                <EmptyState
                    title="No activity yet"
                    description="Start chatting or take an assessment to see your activity here"
                    actionLabel="Get Started"
                    onAction={() => window.location.href = '/chat'}
                />
            </Card>
        );
    }

    return (
        <Card className={className}>
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                    <span>{'\uD83D\uDCDD'}</span> Recent Activity
                </CardTitle>
                <Button
                    as={Link}
                    to="/activities"
                    variant="ghost"
                    size="sm"
                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                    className="text-terracotta hover:bg-cream"
                >
                    View All
                </Button>
            </CardHeader>

            <div className="space-y-4">
                {activities.slice(0, 5).map((activity, index) => {
                    const Icon = activityIcons[activity.type] || SparklesIcon;
                    const colorClass = activityColors[activity.type] || 'bg-neutral-100 text-neutral-600';

                    return (
                        <div
                            key={activity.id || index}
                            className="flex items-start gap-4 p-3 rounded-2xl hover:bg-cream/50 transition-colors"
                        >
                            <div className={cn('w-10 h-10 rounded-2xl flex items-center justify-center', colorClass)}>
                                <Icon className="w-5 h-5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2">
                                    <p className="text-sm font-medium text-neutral-900">
                                        {activity.title}
                                    </p>
                                    <span className="text-xs text-neutral-400 whitespace-nowrap">
                    {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                  </span>
                                </div>
                                <p className="text-sm text-neutral-500 truncate mt-0.5">
                                    {activity.description}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}

export default RecentActivity;