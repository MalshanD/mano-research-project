import { httpClient } from './api';
import { API_ENDPOINTS } from '../config/api.config';

const clusterService = {
    /**
     * Assign user to cluster
     */
    assignToCluster: async (scores) => {
        const response = await httpClient.post(API_ENDPOINTS.CLUSTERS.ASSIGN, {
            stressScore: scores.stress,
            depressionScore: scores.depression,
            anxietyScore: scores.anxiety,
        });
        return response.data;
    },

    /**
     * Get current cluster
     */
    getCurrentCluster: async () => {
        const response = await httpClient.get(API_ENDPOINTS.CLUSTERS.CURRENT);
        return response.data;
    },

    /**
     * Get peer group members
     */
    getPeers: async (limit = 10) => {
        const response = await httpClient.get(API_ENDPOINTS.CLUSTERS.PEERS, {
            params: { limit },
        });
        return response.data;
    },

    /**
     * Get recommended activities
     */
    getActivities: async () => {
        const response = await httpClient.get(API_ENDPOINTS.CLUSTERS.ACTIVITIES);
        return response.data;
    },

    /**
     * Get cluster transitions history
     */
    getTransitions: async () => {
        const response = await httpClient.get(API_ENDPOINTS.CLUSTERS.TRANSITIONS);
        return response.data;
    },

    /**
     * Get cluster statistics (admin/professional)
     */
    getStatistics: async () => {
        const response = await httpClient.get(API_ENDPOINTS.CLUSTERS.STATISTICS);
        return response.data;
    },

    /**
     * Preview cluster assignment (without saving)
     */
    previewAssignment: async (scores) => {
        const response = await httpClient.post(`${API_ENDPOINTS.CLUSTERS.ASSIGN}/preview`, {
            stressScore: scores.stress,
            depressionScore: scores.depression,
            anxietyScore: scores.anxiety,
        });
        return response.data;
    },
};

export default clusterService;