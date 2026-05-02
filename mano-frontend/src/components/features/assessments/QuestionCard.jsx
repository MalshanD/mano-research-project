import { cn } from '../../../utils/helpers';
import { Card } from '../../common';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

function QuestionCard({
                          question,
                          questionNumber,
                          totalQuestions,
                          options,
                          selectedValue,
                          onSelect,
                          timeframe,
                          className,
                      }) {
    return (
        <Card className={cn('', className)}>
            {/* Question Header */}
            <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-primary-600">
          Question {questionNumber} of {totalQuestions}
        </span>
                {question.isCritical && (
                    <div className="flex items-center gap-1 text-warning-600">
                        <ExclamationTriangleIcon className="w-4 h-4" />
                        <span className="text-xs font-medium">Important Question</span>
                    </div>
                )}
            </div>

            {/* Timeframe */}
            {timeframe && (
                <p className="text-sm text-neutral-500 mb-2">{timeframe}, how often have you been bothered by:</p>
            )}

            {/* Question Text */}
            <h3 className="text-lg font-medium text-neutral-900 mb-6">
                {question.text}
            </h3>

            {/* Options */}
            <div className="space-y-3">
                {options.map((option) => (
                    <button
                        key={option.value}
                        onClick={() => onSelect(option.value)}
                        className={cn(
                            'w-full flex items-center gap-4 p-4 rounded-xl border-2 transition-all text-left',
                            selectedValue === option.value
                                ? 'border-primary-500 bg-primary-50'
                                : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50'
                        )}
                    >
                        {/* Radio Circle */}
                        <div
                            className={cn(
                                'w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                                selectedValue === option.value
                                    ? 'border-primary-500'
                                    : 'border-neutral-300'
                            )}
                        >
                            {selectedValue === option.value && (
                                <div className="w-2.5 h-2.5 rounded-full bg-primary-500" />
                            )}
                        </div>

                        {/* Option Content */}
                        <div className="flex-1">
                            <p
                                className={cn(
                                    'font-medium',
                                    selectedValue === option.value
                                        ? 'text-primary-900'
                                        : 'text-neutral-700'
                                )}
                            >
                                {option.label}
                            </p>
                            {option.description && (
                                <p className="text-sm text-neutral-500 mt-0.5">
                                    {option.description}
                                </p>
                            )}
                        </div>

                        {/* Score indicator */}
                        <span
                            className={cn(
                                'text-sm font-medium',
                                selectedValue === option.value
                                    ? 'text-primary-600'
                                    : 'text-neutral-400'
                            )}
                        >
              {option.value}
            </span>
                    </button>
                ))}
            </div>
        </Card>
    );
}

export default QuestionCard;