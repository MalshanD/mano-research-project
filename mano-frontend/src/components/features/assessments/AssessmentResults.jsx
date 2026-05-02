import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../../../utils/helpers';
import { Card, Button, Badge } from '../../common';
import { CircularProgress } from '../../charts';
import {
    CheckCircleIcon,
    ArrowRightIcon,
    ChatBubbleLeftRightIcon,
    CalendarIcon,
    DocumentTextIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { ASSESSMENT_TYPES, getScoreLevel } from '../../../config/assessments';

function AssessmentResults({
                               assessmentType,
                               score,
                               answers,
                               onRetake,
                               onClose,
                               className,
                           }) {
    const assessment = ASSESSMENT_TYPES[assessmentType];
    const scoreLevel = getScoreLevel(assessmentType, score);

    const colorClasses = {
        success: {
            bg: 'bg-success-50',
            text: 'text-success-700',
            border: 'border-success-200',
            progress: '#22c55e',
        },
        warning: {
            bg: 'bg-warning-50',
            text: 'text-warning-700',
            border: 'border-warning-200',
            progress: '#eab308',
        },
        accent: {
            bg: 'bg-accent-50',
            text: 'text-accent-700',
            border: 'border-accent-200',
            progress: '#f97316',
        },
        danger: {
            bg: 'bg-crisis-50',
            text: 'text-crisis-700',
            border: 'border-crisis-200',
            progress: '#ef4444',
        },
    };

    const colors = colorClasses[scoreLevel?.color] || colorClasses.success;
    const percentage = (score / assessment.maxScore) * 100;

    // Check for critical responses (e.g., suicidal ideation in PHQ-9)
    const hasCriticalResponse = useMemo(() => {
        if (assessmentType === 'PHQ9') {
            // Question 9 is about suicidal thoughts
            return answers[8] > 0;
        }
        return false;
    }, [assessmentType, answers]);

    // Recommendations based on score level
    const recommendations = useMemo(() => {
        const baseRecs = [
            {
                icon: ChatBubbleLeftRightIcon,
                title: 'Talk to Manō',
                description: 'Our AI companion is here to listen and support you',
                action: '/chat',
                actionLabel: 'Start Chat',
            },
        ];

        if (scoreLevel?.color === 'danger' || scoreLevel?.color === 'accent') {
            baseRecs.unshift({
                icon: CalendarIcon,
                title: 'Consider Professional Support',
                description: 'Speaking with a mental health professional may be beneficial',
                action: '/resources',
                actionLabel: 'Find Resources',
                highlight: true,
            });
        }

        baseRecs.push({
            icon: DocumentTextIcon,
            title: 'Track Your Progress',
            description: 'Regular assessments help monitor your mental health journey',
            action: '/predictions',
            actionLabel: 'View Trends',
        });

        return baseRecs;
    }, [scoreLevel]);

    return (
        <div className={cn('max-w-2xl mx-auto', className)}>
            {/* Critical Alert */}
            {hasCriticalResponse && (
                <div className="mb-6 p-4 bg-crisis-50 border border-crisis-200 rounded-xl">
                    <div className="flex items-start gap-3">
                        <ExclamationTriangleIcon className="w-6 h-6 text-crisis-600 flex-shrink-0" />
                        <div>
                            <h4 className="font-semibold text-crisis-900">
                                We're Here For You
                            </h4>
                            <p className="text-sm text-crisis-700 mt-1">
                                Your response indicates you may be having thoughts of self-harm.
                                Please know that help is available. If you're in crisis, please call
                                <a href="tel:988" className="font-bold underline mx-1">988</a>
                                (Suicide & Crisis Lifeline) or text HOME to 741741.
                            </p>
                            <Button
                                variant="danger"
                                size="sm"
                                className="mt-3"
                                onClick={() => window.open('tel:988')}
                            >
                                Call Crisis Line
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Results Card */}
            <Card className="text-center mb-6">
                {/* Success Icon */}
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-success-100 flex items-center justify-center">
                    <CheckCircleIcon className="w-8 h-8 text-success-600" />
                </div>

                <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                    Assessment Complete
                </h2>
                <p className="text-neutral-500 mb-6">
                    Thank you for completing the {assessment.name}
                </p>

                {/* Score Display */}
                <div className="flex justify-center mb-6">
                    <CircularProgress
                        value={percentage}
                        size={160}
                        strokeWidth={12}
                        color={colors.progress}
                        showPercentage={false}
                    >
                        <div className="text-center">
                            <span className="text-4xl font-bold text-neutral-900">{score}</span>
                            <span className="text-lg text-neutral-500">/{assessment.maxScore}</span>
                        </div>
                    </CircularProgress>
                </div>

                {/* Score Level */}
                <div className={cn('inline-block px-6 py-3 rounded-xl mb-4', colors.bg, colors.border, 'border')}>
                    <p className={cn('text-lg font-semibold', colors.text)}>
                        {scoreLevel?.label}
                    </p>
                </div>

                <p className="text-neutral-600 max-w-md mx-auto">
                    {scoreLevel?.description}
                </p>
            </Card>

            {/* Score Breakdown */}
            <Card className="mb-6">
                <h3 className="font-semibold text-neutral-900 mb-4">Score Breakdown</h3>
                <div className="space-y-3">
                    {Object.entries(assessment.scoring).map(([key, level]) => {
                        const isActive = score >= level.min && score <= level.max;
                        return (
                            <div
                                key={key}
                                className={cn(
                                    'flex items-center justify-between p-3 rounded-lg',
                                    isActive ? colorClasses[level.color].bg : 'bg-neutral-50'
                                )}
                            >
                <span className={cn('font-medium', isActive ? colorClasses[level.color].text : 'text-neutral-600')}>
                  {level.label}
                </span>
                                <span className={cn('text-sm', isActive ? colorClasses[level.color].text : 'text-neutral-500')}>
                  {level.min} - {level.max} points
                </span>
                            </div>
                        );
                    })}
                </div>
            </Card>

            {/* Recommendations */}
            <Card className="mb-6">
                <h3 className="font-semibold text-neutral-900 mb-4">Recommended Next Steps</h3>
                <div className="space-y-4">
                    {recommendations.map((rec, index) => {
                        const Icon = rec.icon;
                        return (
                            <div
                                key={index}
                                className={cn(
                                    'flex items-start gap-4 p-4 rounded-xl',
                                    rec.highlight ? 'bg-primary-50 border border-primary-200' : 'bg-neutral-50'
                                )}
                            >
                                <div className={cn(
                                    'w-10 h-10 rounded-lg flex items-center justify-center',
                                    rec.highlight ? 'bg-primary-100' : 'bg-white'
                                )}>
                                    <Icon className={cn('w-5 h-5', rec.highlight ? 'text-primary-600' : 'text-neutral-600')} />
                                </div>
                                <div className="flex-1">
                                    <h4 className="font-medium text-neutral-900">{rec.title}</h4>
                                    <p className="text-sm text-neutral-600 mt-0.5">{rec.description}</p>
                                </div>
                                <Button
                                    as={Link}
                                    to={rec.action}
                                    variant={rec.highlight ? 'primary' : 'ghost'}
                                    size="sm"
                                >
                                    {rec.actionLabel}
                                </Button>
                            </div>
                        );
                    })}
                </div>
            </Card>

            {/* Actions */}
            <div className="flex items-center justify-center gap-4">
                <Button variant="outline" onClick={onRetake}>
                    Take Again
                </Button>
                <Button
                    as={Link}
                    to="/assessments"
                    variant="primary"
                    rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                >
                    Back to Assessments
                </Button>
            </div>

            {/* Disclaimer */}
            <p className="text-xs text-neutral-400 text-center mt-6">
                This assessment is for screening purposes only and is not a diagnostic tool.
                Please consult a healthcare professional for proper evaluation and treatment.
            </p>
        </div>
    );
}

export default AssessmentResults;