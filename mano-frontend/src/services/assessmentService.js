import api from './api';

// Mock delay
const mockDelay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock assessment history
let mockHistory = [
    {
        id: 'assess-1',
        assessmentType: 'PHQ9',
        score: 8,
        answers: [1, 1, 1, 1, 1, 1, 1, 1, 0],
        completedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'assess-2',
        assessmentType: 'PHQ9',
        score: 12,
        answers: [2, 1, 2, 1, 1, 2, 1, 1, 1],
        completedAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'assess-3',
        assessmentType: 'GAD7',
        score: 10,
        answers: [2, 1, 2, 1, 1, 2, 1],
        completedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
        id: 'assess-4',
        assessmentType: 'PSS10',
        score: 18,
        answers: [2, 2, 3, 2, 2, 2, 2, 2, 2, 1],
        completedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    },
];

const assessmentService = {
    // Get full session history for a user
    // Returns raw array: [{ user_id, stress, anxiety, depression, created_at }, ...]
    getHistory: async (userId) => {
        if (!userId) return [];
        try {
            const response = await api.get(`/response/response/history/${userId}`);
            return response.data || [];
        } catch (error) {
            return [];
        }
    },

    // Get single assessment result
    getResult: async (assessmentId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return mockHistory.find((h) => h.id === assessmentId);
        }
        const response = await api.get(`/assessments/${assessmentId}`);
        return response.data;
    },

    // Submit assessment
    submit: async (assessmentType, answers) => {
        if (import.meta.env.DEV) {
            await mockDelay(1000);

            // Calculate score based on type
            let score;
            if (assessmentType === 'PSS10') {
                // PSS-10 has reversed questions
                const reversedIndices = [3, 4, 6, 7]; // 0-indexed
                score = answers.reduce((total, answer, index) => {
                    if (reversedIndices.includes(index)) {
                        return total + (4 - answer);
                    }
                    return total + answer;
                }, 0);
            } else {
                score = answers.reduce((sum, val) => sum + (val || 0), 0);
            }

            const result = {
                id: `assess-${Date.now()}`,
                assessmentType,
                score,
                answers,
                completedAt: new Date().toISOString(),
            };

            mockHistory = [result, ...mockHistory];
            return result;
        }

        const response = await api.post('/assessments/submit', {
            type: assessmentType,
            answers,
        });
        // Return raw result — preserve float scores from the backend (e.g. 49.9, 50.4)
        return response.data;
    },

    // Get latest assessment for each type
    getLatest: async (userId = 1) => {
        try {
            const response = await api.get(`/response/response/last/${userId}`);
            const data = response.data;

            // Map backend response: { stress: {score, risk_level}, anxiety: {...}, depression: {...}, created_at }
            if (data && (data.depression || data.anxiety || data.stress)) {
                const mapped = {};
                if (data.depression) {
                    mapped['PHQ9'] = {
                        assessmentType: 'PHQ9',
                        score: data.depression.score ?? 0,
                        risk_level: data.depression.risk_level,
                        completedAt: data.created_at || new Date().toISOString(),
                    };
                }
                if (data.anxiety) {
                    mapped['GAD7'] = {
                        assessmentType: 'GAD7',
                        score: data.anxiety.score ?? 0,
                        risk_level: data.anxiety.risk_level,
                        completedAt: data.created_at || new Date().toISOString(),
                    };
                }
                if (data.stress) {
                    mapped['PSS10'] = {
                        assessmentType: 'PSS10',
                        score: data.stress.score ?? 0,
                        risk_level: data.stress.risk_level,
                        completedAt: data.created_at || new Date().toISOString(),
                    };
                }
                return mapped;
            }

            // Fallback object map — keep raw float scores as-is
            if (data && typeof data === 'object') {
                return data;
            }

            return data;
        } catch (error) {
            // Return empty object on error (e.g. 404 Not Found)
            return {};
        }
    },

    // Get recommended assessment
    getRecommended: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            // Simple logic: recommend the one not taken recently
            const phq9 = mockHistory.find((h) => h.assessmentType === 'PHQ9');
            const gad7 = mockHistory.find((h) => h.assessmentType === 'GAD7');
            const pss10 = mockHistory.find((h) => h.assessmentType === 'PSS10');

            if (!phq9) return 'PHQ9';
            if (!gad7) return 'GAD7';
            if (!pss10) return 'PSS10';

            // Return oldest
            const oldest = [phq9, gad7, pss10].sort(
                (a, b) => new Date(a.completedAt) - new Date(b.completedAt)
            )[0];
            return oldest.assessmentType;
        }
        const response = await api.get('/assessments/recommended');
        return response.data;
    },
};

export default assessmentService;