import { cn } from '../../../utils/helpers';

function AssessmentProgress({
                                current,
                                total,
                                answers = [],
                                onJumpTo,
                                className,
                            }) {
    const percentage = (current / total) * 100;

    return (
        <div className={cn('', className)}>
            {/* Progress Bar */}
            <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-neutral-700">
            Progress
          </span>
                    <span className="text-sm text-neutral-500">
            {current} / {total}
          </span>
                </div>
                <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary-500 rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%` }}
                    />
                </div>
            </div>

            {/* Question Dots */}
            <div className="flex flex-wrap gap-2">
                {Array.from({ length: total }).map((_, index) => {
                    const isAnswered = answers[index] !== undefined;
                    const isCurrent = index + 1 === current;

                    return (
                        <button
                            key={index}
                            onClick={() => onJumpTo?.(index + 1)}
                            disabled={!onJumpTo}
                            className={cn(
                                'w-8 h-8 rounded-lg text-xs font-medium transition-all',
                                isCurrent && 'ring-2 ring-primary-500 ring-offset-2',
                                isAnswered
                                    ? 'bg-primary-500 text-white'
                                    : 'bg-neutral-100 text-neutral-500 hover:bg-neutral-200',
                                onJumpTo && 'cursor-pointer',
                                !onJumpTo && 'cursor-default'
                            )}
                        >
                            {index + 1}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default AssessmentProgress;