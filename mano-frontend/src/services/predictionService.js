import { httpClient } from './api';
import { API_ENDPOINTS } from '../config/api.config';
import { buildUrlWithQuery } from '../config/api.config';

const predictionService = {
    /**
     * Create new prediction with full data
     */
    createPrediction: async (predictionData) => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.BASE, predictionData);
        return response.data;
    },

    /**
     * Create prediction with direct scores
     */
    createDirectPrediction: async (stressScore, depressionScore, anxietyScore, dataSource = 'manual') => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.DIRECT, null, {
            params: { stressScore, depressionScore, anxietyScore, dataSource },
        });
        return response.data;
    },

    /**
     * Create prediction from PHQ-9 questionnaire
     */
    createFromPHQ9: async (responses) => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.PHQ9, responses);
        return response.data;
    },

    /**
     * Create prediction from GAD-7 questionnaire
     */
    createFromGAD7: async (responses) => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.GAD7, responses);
        return response.data;
    },

    /**
     * Create prediction from PSS questionnaire
     */
    createFromPSS: async (responses) => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.PSS, responses);
        return response.data;
    },

    /**
     * Create prediction from all questionnaires
     */
    createFromAllQuestionnaires: async (phq9, gad7, pss) => {
        const response = await httpClient.post(API_ENDPOINTS.PREDICTIONS.ALL_QUESTIONNAIRES, {
            phq9,
            gad7,
            pss,
        });
        return response.data;
    },

    /**
     * Get prediction by ID
     */
    getPredictionById: async (id) => {
        const response = await httpClient.get(`${API_ENDPOINTS.PREDICTIONS.BASE}/${id}`);
        return response.data;
    },

    /**
     * Get prediction history
     */
    getPredictionHistory: async (params = {}) => {
        const { page = 0, size = 10, sort = 'createdAt,desc' } = params;
        const url = buildUrlWithQuery(API_ENDPOINTS.PREDICTIONS.HISTORY, { page, size, sort });
        const response = await httpClient.get(url);
        return response.data;
    },

    /**
     * Get prediction trends
     */
    getPredictionTrends: async (days = 30) => {
        const response = await httpClient.get(API_ENDPOINTS.PREDICTIONS.TRENDS, {
            params: { days },
        });
        return response.data;
    },

    /**
     * Get latest prediction
     */
    getLatestPrediction: async () => {
        const response = await httpClient.get(`${API_ENDPOINTS.PREDICTIONS.BASE}/latest`);
        return response.data;
    },
};

export default predictionService;