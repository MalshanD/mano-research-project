import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import predictionService from '../services/predictionService';
import { useNotification } from '../contexts/NotificationContext';

// Query keys
const PREDICTION_KEYS = {
    all: ['predictions'],
    history: (params) => ['predictions', 'history', params],
    trends: (days) => ['predictions', 'trends', days],
    single: (id) => ['predictions', id],
    latest: ['predictions', 'latest'],
};

/**
 * Hook for prediction history
 */
export function usePredictionHistory(params = {}) {
    return useQuery({
        queryKey: PREDICTION_KEYS.history(params),
        queryFn: () => predictionService.getPredictionHistory(params),
        staleTime: 2 * 60 * 1000, // 2 minutes
    });
}

/**
 * Hook for prediction trends
 */
export function usePredictionTrends(days = 30) {
    return useQuery({
        queryKey: PREDICTION_KEYS.trends(days),
        queryFn: () => predictionService.getPredictionTrends(days),
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}

/**
 * Hook for single prediction
 */
export function usePrediction(id) {
    return useQuery({
        queryKey: PREDICTION_KEYS.single(id),
        queryFn: () => predictionService.getPredictionById(id),
        enabled: !!id,
    });
}

/**
 * Hook for latest prediction
 */
export function useLatestPrediction() {
    return useQuery({
        queryKey: PREDICTION_KEYS.latest,
        queryFn: () => predictionService.getLatestPrediction(),
        staleTime: 1 * 60 * 1000, // 1 minute
    });
}

/**
 * Hook for creating predictions
 */
export function useCreatePrediction() {
    const queryClient = useQueryClient();
    const { success, error } = useNotification();

    return useMutation({
        mutationFn: (data) => predictionService.createPrediction(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: PREDICTION_KEYS.all });
            success('Prediction created successfully');
        },
        onError: (err) => {
            error(err.message || 'Failed to create prediction');
        },
    });
}

/**
 * Hook for PHQ-9 prediction
 */
export function useCreatePHQ9Prediction() {
    const queryClient = useQueryClient();
    const { success, error } = useNotification();

    return useMutation({
        mutationFn: (responses) => predictionService.createFromPHQ9(responses),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: PREDICTION_KEYS.all });
            success('PHQ-9 assessment completed');
        },
        onError: (err) => {
            error(err.message || 'Failed to submit PHQ-9 assessment');
        },
    });
}

/**
 * Hook for GAD-7 prediction
 */
export function useCreateGAD7Prediction() {
    const queryClient = useQueryClient();
    const { success, error } = useNotification();

    return useMutation({
        mutationFn: (responses) => predictionService.createFromGAD7(responses),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: PREDICTION_KEYS.all });
            success('GAD-7 assessment completed');
        },
        onError: (err) => {
            error(err.message || 'Failed to submit GAD-7 assessment');
        },
    });
}

/**
 * Hook for PSS prediction
 */
export function useCreatePSSPrediction() {
    const queryClient = useQueryClient();
    const { success, error } = useNotification();

    return useMutation({
        mutationFn: (responses) => predictionService.createFromPSS(responses),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: PREDICTION_KEYS.all });
            success('PSS assessment completed');
        },
        onError: (err) => {
            error(err.message || 'Failed to submit PSS assessment');
        },
    });
}

/**
 * Hook for all questionnaires prediction
 */
export function useCreateFullAssessment() {
    const queryClient = useQueryClient();
    const { success, error } = useNotification();

    return useMutation({
        mutationFn: ({ phq9, gad7, pss }) =>
            predictionService.createFromAllQuestionnaires(phq9, gad7, pss),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: PREDICTION_KEYS.all });
            success('Full assessment completed');
        },
        onError: (err) => {
            error(err.message || 'Failed to submit assessment');
        },
    });
}

export default {
    usePredictionHistory,
    usePredictionTrends,
    usePrediction,
    useLatestPrediction,
    useCreatePrediction,
    useCreatePHQ9Prediction,
    useCreateGAD7Prediction,
    useCreatePSSPrediction,
    useCreateFullAssessment,
};