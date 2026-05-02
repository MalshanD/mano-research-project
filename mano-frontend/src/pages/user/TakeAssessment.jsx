import { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { cn } from '../../utils/helpers';
import { useAssessment } from '../../hooks/useAssessment';
import { Button, Card, Alert, Modal } from '../../components/common';
import {
    QuestionCard,
    AssessmentProgress,
    AssessmentResults,
} from '../../components/features/assessments';
import { CrisisModal } from '../../components/features/crisis';
import { ASSESSMENT_TYPES } from '../../config/assessments';
import {
    ArrowLeftIcon,
    ArrowRightIcon,
    CheckIcon,
    XMarkIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useState } from 'react';

function TakeAssessment() {
    const { type } = useParams();
    const navigate = useNavigate();
    const assessmentType = type?.toUpperCase();

    const [showExitConfirm, setShowExitConfirm] = useState(false);
    const [showCrisisModal, setShowCrisisModal] = useState(false);

    const {
        assessment,
        questions,
        options,
        currentQuestion,
        answers,
        isComplete,
        result,
        canGoNext,
        canGoPrevious,
        isLastQuestion,
        allAnswered,
        isSubmitting,
        submitError,
        progress,
        selectAnswer,
        goToQuestion,
        goNext,
        goPrevious,
        submitAssessment,
        resetAssessment,
    } = useAssessment(assessmentType);

    // Validate assessment type
    useEffect(() => {
        if (!ASSESSMENT_TYPES[assessmentType]) {
            navigate('/assessments', { replace: true });
        }
    }, [assessmentType, navigate]);

    // Check for critical question responses (suicidal ideation)
    useEffect(() => {
        if (assessmentType === 'PHQ9' && currentQuestion === 9 && answers[8] > 0) {
            setShowCrisisModal(true);
        }
    }, [assessmentType, currentQuestion, answers]);

    if (!assessment) {
        return null;
    }

    const currentQuestionData = questions[currentQuestion - 1];

    // Show results
    if (isComplete && result) {
        return (
            <div className="min-h-screen bg-neutral-50 py-8 px-4">
                <AssessmentResults
                    assessmentType={assessmentType}
                    score={result.score}
                    answers={result.answers}
                    onRetake={resetAssessment}
                />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-neutral-50">
            {/* Header */}
            <div className="bg-white border-b border-neutral-100 sticky top-0 z-10">
                <div className="max-w-3xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <button
                            onClick={() => setShowExitConfirm(true)}
                            className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 transition-colors"
                        >
                            <ArrowLeftIcon className="w-5 h-5" />
                            <span className="text-sm font-medium">Exit</span>
                        </button>

                        <div className="text-center">
                            <h1 className="font-semibold text-neutral-900">{assessment.name}</h1>
                            <p className="text-xs text-neutral-500">{assessment.fullName}</p>
                        </div>

                        <div className="w-16" /> {/* Spacer */}
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-4">
                        <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary-500 rounded-full transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-3xl mx-auto px-4 py-8">
                {/* Error Alert */}
                {submitError && (
                    <Alert variant="danger" className="mb-6">
                        Failed to submit assessment. Please try again.
                    </Alert>
                )}

                {/* Question */}
                <QuestionCard
                    question={currentQuestionData}
                    questionNumber={currentQuestion}
                    totalQuestions={questions.length}
                    options={options}
                    selectedValue={answers[currentQuestion - 1]}
                    onSelect={selectAnswer}
                    timeframe={assessment.timeframe}
                    className="mb-6"
                />

                {/* Navigation */}
                <div className="flex items-center justify-between">
                    <Button
                        variant="ghost"
                        onClick={goPrevious}
                        disabled={!canGoPrevious}
                        leftIcon={<ArrowLeftIcon className="w-4 h-4" />}
                    >
                        Previous
                    </Button>

                    {isLastQuestion ? (
                        <Button
                            variant="primary"
                            onClick={submitAssessment}
                            disabled={!allAnswered}
                            loading={isSubmitting}
                            leftIcon={<CheckIcon className="w-4 h-4" />}
                        >
                            Submit Assessment
                        </Button>
                    ) : (
                        <Button
                            variant="primary"
                            onClick={goNext}
                            disabled={!canGoNext}
                            rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                        >
                            Next
                        </Button>
                    )}
                </div>

                {/* Question Navigator */}
                <div className="mt-8">
                    <AssessmentProgress
                        current={currentQuestion}
                        total={questions.length}
                        answers={answers}
                        onJumpTo={goToQuestion}
                    />
                </div>
            </div>

            {/* Exit Confirmation Modal */}
            <Modal
                isOpen={showExitConfirm}
                onClose={() => setShowExitConfirm(false)}
                title="Exit Assessment?"
                size="sm"
                footer={
                    <div className="flex justify-end gap-3">
                        <Button variant="ghost" onClick={() => setShowExitConfirm(false)}>
                            Continue Assessment
                        </Button>
                        <Button
                            variant="danger"
                            onClick={() => navigate('/assessments')}
                        >
                            Exit
                        </Button>
                    </div>
                }
            >
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-full bg-warning-100 flex items-center justify-center flex-shrink-0">
                        <ExclamationTriangleIcon className="w-5 h-5 text-warning-600" />
                    </div>
                    <div>
                        <p className="text-neutral-600">
                            Your progress will be lost if you exit now. Are you sure you want to leave?
                        </p>
                    </div>
                </div>
            </Modal>

            {/* Crisis Modal */}
            <CrisisModal
                isOpen={showCrisisModal}
                onClose={() => setShowCrisisModal(false)}
            />
        </div>
    );
}

export default TakeAssessment;