import { Link } from 'react-router-dom';
import { cn } from '../../../utils/helpers';
import { Card, CardHeader, CardTitle, Button, EmptyState } from '../../common';
import { ActivityCard } from '../community';
import { ArrowRightIcon, CalendarDaysIcon } from '@heroicons/react/24/outline';

function UpcomingActivities({
                                activities = [],
                                loading = false,
                                onStartActivity,
                                onCompleteActivity,
                                className,
                            }) {
    if (loading) {
        return (
            <Card className={className}>
                <CardHeader>
                    <CardTitle>Recommended Activities</CardTitle>
                </CardHeader>
                <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="animate-pulse flex items-center gap-3 p-3 bg-neutral-50 rounded-xl">
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
                    <CardTitle>Recommended Activities</CardTitle>
                </CardHeader>
                <EmptyState
                    icon={<CalendarDaysIcon className="w-8 h-8" />}
                    title="No activities yet"
                    description="Complete an assessment to get personalized activity recommendations"
                    actionLabel="Take Assessment"
                    onAction={() => window.location.href = '/assessments'}
                />
            </Card>
        );
    }

    return (
        <Card className={className}>
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                    <span>{'\uD83C\uDF3F'}</span> Recommended
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

            <div className="space-y-3">
                {activities.slice(0, 3).map((activity) => (
                    <ActivityCard
                        key={activity.id}
                        activity={activity}
                        compact
                        onStart={onStartActivity}
                        onComplete={onCompleteActivity}
                    />
                ))}
            </div>
        </Card>
    );
}

export default UpcomingActivities;