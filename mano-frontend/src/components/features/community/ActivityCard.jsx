import { cn } from '../../../utils/helpers';
import { Card, Badge, Button } from '../../common';
import {
    ClockIcon,
    SparklesIcon,
    CheckCircleIcon,
    PlayIcon,
} from '@heroicons/react/24/outline';

const categoryIcons = {
    // UI-facing labels
    mindfulness: '🧘',
    exercise: '🏃',
    social: '👥',
    creative: '🎨',
    nature: '🌿',
    relaxation: '😌',
    cognitive: '🧠',
    sleep: '😴',
    // DB category names from activities.py
    stress_relief: '🌬️',
    anxiety_relief: '💆',
    depression_relief: '☀️',
    physical: '🏃',
    emotional: '❤️',
    routine: '📋',
    social_connection: '👥',
    breathing: '🌬️',
    journaling: '📝',
    meditation: '🧘',
};

const difficultyColors = {
    easy: 'success',
    moderate: 'warning',
    challenging: 'accent',
};

function ActivityCard({
                          activity,
                          onStart,
                          onComplete,
                          completed = false,
                          compact = false,
                          className,
                      }) {
    const {
        id,
        title,
        description,
        category = 'mindfulness',
        duration = 10,
        difficulty = 'easy',
        benefits = [],
    } = activity || {};

    const icon = categoryIcons[category] || '✨';

    if (compact) {
        return (
            <div
                className={cn(
                    'flex items-center gap-3 p-3 bg-white rounded-xl border border-neutral-100 hover:shadow-soft transition-all',
                    completed && 'opacity-60',
                    className
                )}
            >
                <div className="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center text-xl">
                    {icon}
                </div>
                <div className="flex-1 min-w-0">
                    <p className={cn('text-sm font-medium text-neutral-900', completed && 'line-through')}>
                        {title}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                        <ClockIcon className="w-3.5 h-3.5 text-neutral-400" />
                        <span className="text-xs text-neutral-500">{duration} min</span>
                    </div>
                </div>
                {completed ? (
                    <CheckCircleIcon className="w-6 h-6 text-success-500" />
                ) : (
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => onStart?.(activity)}
                    >
                        <PlayIcon className="w-4 h-4" />
                    </Button>
                )}
            </div>
        );
    }

    return (
        <Card className={cn('', className)}>
            <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center text-2xl">
                    {icon}
                </div>
                <div className="flex-1">
                    <div className="flex items-start justify-between">
                        <div>
                            <h3 className="font-semibold text-neutral-900">{title}</h3>
                            <div className="flex items-center gap-3 mt-1">
                                <div className="flex items-center gap-1 text-neutral-500">
                                    <ClockIcon className="w-4 h-4" />
                                    <span className="text-sm">{duration} min</span>
                                </div>
                                <Badge variant={difficultyColors[difficulty]} size="sm">
                                    {difficulty}
                                </Badge>
                            </div>
                        </div>
                        {completed && (
                            <Badge variant="success" size="sm">
                                <CheckCircleIcon className="w-3.5 h-3.5 mr-1" />
                                Completed
                            </Badge>
                        )}
                    </div>

                    <p className="text-sm text-neutral-600 mt-3">{description}</p>

                    {/* Benefits */}
                    {benefits.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                            {benefits.map((benefit, index) => (
                                <span
                                    key={index}
                                    className="inline-flex items-center gap-1 px-2 py-1 bg-success-50 text-success-700 text-xs rounded-lg"
                                >
                  <SparklesIcon className="w-3 h-3" />
                                    {benefit}
                </span>
                            ))}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-3 mt-4">
                        {!completed ? (
                            <>
                                <Button
                                    variant="primary"
                                    size="sm"
                                    onClick={() => onStart?.(activity)}
                                    leftIcon={<PlayIcon className="w-4 h-4" />}
                                >
                                    Start Activity
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => onComplete?.(activity)}
                                >
                                    Mark Complete
                                </Button>
                            </>
                        ) : (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => onStart?.(activity)}
                            >
                                Do Again
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}

export default ActivityCard;