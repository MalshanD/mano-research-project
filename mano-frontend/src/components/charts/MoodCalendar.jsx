import { useMemo } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isToday } from 'date-fns';
import { cn } from '../../utils/helpers';
import Tooltip from '../common/Tooltip';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function MoodCalendar({
                          data = [],
                          month = new Date(),
                          onDayClick,
                          className,
                      }) {
    const calendarDays = useMemo(() => {
        const start = startOfMonth(month);
        const end = endOfMonth(month);
        const days = eachDayOfInterval({ start, end });

        // Add padding for days before the first of month
        const paddingStart = start.getDay();
        const paddedDays = Array(paddingStart).fill(null).concat(days);

        return paddedDays;
    }, [month]);

    const getMoodForDay = (day) => {
        if (!day) return null;
        return data.find((d) => isSameDay(new Date(d.date), day));
    };

    const getMoodColor = (score) => {
        if (score === null || score === undefined) return 'bg-neutral-100';
        if (score >= 0.8) return 'bg-success-400';
        if (score >= 0.6) return 'bg-success-300';
        if (score >= 0.4) return 'bg-warning-300';
        if (score >= 0.2) return 'bg-accent-300';
        return 'bg-crisis-300';
    };

    return (
        <div className={cn('', className)}>
            {/* Month Header */}
            <div className="text-center mb-4">
                <h3 className="text-lg font-semibold text-neutral-900">
                    {format(month, 'MMMM yyyy')}
                </h3>
            </div>

            {/* Day Headers */}
            <div className="grid grid-cols-7 gap-1 mb-2">
                {DAYS.map((day) => (
                    <div key={day} className="text-center text-xs font-medium text-neutral-400 py-1">
                        {day}
                    </div>
                ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
                {calendarDays.map((day, index) => {
                    if (!day) {
                        return <div key={`empty-${index}`} className="aspect-square" />;
                    }

                    const mood = getMoodForDay(day);
                    const moodScore = mood?.averageMood;
                    const hasData = moodScore !== undefined && moodScore !== null;

                    return (
                        <Tooltip
                            key={day.toISOString()}
                            content={
                                hasData
                                    ? `${format(day, 'MMM d')}: ${(moodScore * 100).toFixed(0)}% wellness`
                                    : `${format(day, 'MMM d')}: No data`
                            }
                        >
                            <button
                                onClick={() => onDayClick?.(day, mood)}
                                className={cn(
                                    'aspect-square rounded-lg flex items-center justify-center text-xs font-medium transition-all',
                                    'hover:ring-2 hover:ring-primary-300 hover:ring-offset-1',
                                    hasData ? getMoodColor(moodScore) : 'bg-neutral-50',
                                    isToday(day) && 'ring-2 ring-primary-500',
                                    hasData ? 'text-white' : 'text-neutral-400'
                                )}
                            >
                                {format(day, 'd')}
                            </button>
                        </Tooltip>
                    );
                })}
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center justify-center gap-4">
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-success-400" />
                    <span className="text-xs text-neutral-500">Great</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-warning-300" />
                    <span className="text-xs text-neutral-500">Okay</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-crisis-300" />
                    <span className="text-xs text-neutral-500">Difficult</span>
                </div>
            </div>
        </div>
    );
}

export default MoodCalendar;