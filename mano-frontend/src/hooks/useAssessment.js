import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import assessmentService from '../services/assessmentService';
import { ASSESSMENT_TYPES, calculateScore } from '../config/assessments';
import { useAuth } from '../contexts/AuthContext';

export function useAssessment(assessmentType) {
    const queryClient = useQueryClient();
    const assessment = ASSESSMENT_TYPES[assessmentType];

    const [currentQuestion, setCurrentQuestion] = useState(1);
    const [answers, setAnswers] = useState(
        new Array(assessment?.questions?.length || 0).fill(undefined)
    );
    const [isComplete, setIsComplete] = useState(false);
    const [result, setResult] = useState(null);

    // Fetch history
    const {
        data: history = [],
        isLoading: historyLoading,
    } = useQuery({
        queryKey: ['assessmentHistory', assessmentType],
        queryFn: () => assessmentService.getHistory(assessmentType),
        enabled: !!assessmentType,
    });

    // Submit mutation
    const submitMutation = useMutation({
        mutationFn: ({ type, answers }) => assessmentService.submit(type, answers),
        onSuccess: (data) => {
            setResult(data);
            setIsComplete(true);
            queryClient.invalidateQueries(['assessmentHistory']);
            queryClient.invalidateQueries(['latestAssessments']);
        },
    });

    // Select answer
    const selectAnswer = useCallback((value) => {
        setAnswers((prev) => {
            const newAnswers = [...prev];
            newAnswers[currentQuestion - 1] = value;
            return newAnswers;
        });
    }, [currentQuestion]);

    // Navigation
    const goToQuestion = useCallback((questionNumber) => {
        if (questionNumber >= 1 && questionNumber <= assessment?.questions?.length) {
            setCurrentQuestion(questionNumber);
        }
    }, [assessment]);

    const goNext = useCallback(() => {
        if (currentQuestion < assessment?.questions?.length) {
            setCurrentQuestion((prev) => prev + 1);
        }
    }, [currentQuestion, assessment]);

    const goPrevious = useCallback(() => {
        if (currentQuestion > 1) {
            setCurrentQuestion((prev) => prev - 1);
        }
    }, [currentQuestion]);

    // Check if can proceed
    const canGoNext = answers[currentQuestion - 1] !== undefined;
    const canGoPrevious = currentQuestion > 1;
    const isLastQuestion = currentQuestion === assessment?.questions?.length;
    const allAnswered = answers.every((a) => a !== undefined);

    // Submit assessment
    const submitAssessment = useCallback(async () => {
        if (!allAnswered) return;
        await submitMutation.mutateAsync({
            type: assessmentType,
            answers,
        });
    }, [assessmentType, answers, allAnswered, submitMutation]);

    // Reset assessment
    const resetAssessment = useCallback(() => {
        setCurrentQuestion(1);
        setAnswers(new Array(assessment?.questions?.length || 0).fill(undefined));
        setIsComplete(false);
        setResult(null);
    }, [assessment]);

    // Calculate current score (for progress/preview)
    const currentScore = calculateScore(assessmentType, answers.filter((a) => a !== undefined));

    return {
        // Assessment config
        assessment,
        questions: assessment?.questions || [],
        options: assessment?.options || [],

        // State
        currentQuestion,
        answers,
        isComplete,
        result,
        history,

        // Loading states
        historyLoading,
        isSubmitting: submitMutation.isPending,
        submitError: submitMutation.error,

        // Computed
        canGoNext,
        canGoPrevious,
        isLastQuestion,
        allAnswered,
        currentScore,
        progress: (answers.filter((a) => a !== undefined).length / (assessment?.questions?.length || 1)) * 100,

        // Actions
        selectAnswer,
        goToQuestion,
        goNext,
        goPrevious,
        submitAssessment,
        resetAssessment,
    };
}

export function useAssessmentHistory() {
    const { user } = useAuth();
    const userId = user?.id;

    return useQuery({
        queryKey: ['assessmentHistory', userId],
        queryFn: () => assessmentService.getHistory(userId),
        enabled: !!userId,
    });
}

export function useLatestAssessments() {
    const { user } = useAuth();
    const userId = user?.id; // Must be the real logged-in user's ID

    return useQuery({
        queryKey: ['latestAssessments', userId],
        queryFn: () => assessmentService.getLatest(userId),
        enabled: !!userId, // Only fetch when a real userId is present
    });
}

export function useRecommendedAssessment() {
    return useQuery({
        queryKey: ['recommendedAssessment'],
        queryFn: () => assessmentService.getRecommended(),
    });
}

export default useAssessment;