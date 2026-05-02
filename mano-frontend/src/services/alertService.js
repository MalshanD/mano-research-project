import { httpClient } from './api';
import { API_ENDPOINTS } from '../config/api.config';
import { buildUrlWithQuery } from '../config/api.config';

const alertService = {
    /**
     * Get all alerts
     */
    getAlerts: async (params = {}) => {
        const { page = 0, size = 20, status, severity } = params;
        const url = buildUrlWithQuery(API_ENDPOINTS.ALERTS.BASE, { page, size, status, severity });
        const response = await httpClient.get(url);
        return response.data;
    },

    /**
     * Get crisis alerts
     */
    getCrisisAlerts: async () => {
        const response = await httpClient.get(API_ENDPOINTS.ALERTS.CRISIS);
        return response.data;
    },

    /**
     * Get alert by ID
     */
    getAlertById: async (id) => {
        const response = await httpClient.get(`${API_ENDPOINTS.ALERTS.BASE}/${id}`);
        return response.data;
    },

    /**
     * Resolve alert
     */
    resolveAlert: async (id, resolutionData) => {
        const response = await httpClient.put(
            API_ENDPOINTS.ALERTS.RESOLVE.replace('{id}', id),
            resolutionData
        );
        return response.data;
    },

    /**
     * Assign alert to professional
     */
    assignAlert: async (id, assignedTo) => {
        const response = await httpClient.put(
            API_ENDPOINTS.ALERTS.ASSIGN.replace('{id}', id),
            { assignedTo }
        );
        return response.data;
    },

    /**
     * Get unresolved alerts count
     */
    getUnresolvedCount: async () => {
        const response = await httpClient.get(`${API_ENDPOINTS.ALERTS.BASE}/unresolved/count`);
        return response.data;
    },
};

export default alertService;