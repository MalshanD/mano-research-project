import api from './api';

// Mock delay
const mockDelay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock user profile data
let mockProfile = {
    id: 'user-1',
    username: 'demo_user',
    email: 'demo@mano.app',
    firstName: 'Demo',
    lastName: 'User',
    avatar: null,
    phone: '+1 (555) 123-4567',
    dateOfBirth: '1990-05-15',
    gender: 'prefer_not_to_say',
    bio: 'Taking it one day at a time. Believer in the power of small steps. 🌱',
    location: 'San Francisco, CA',
    timezone: 'America/Los_Angeles',
    joinedDate: '2024-01-15',
    emergencyContact: {
        name: 'Jane Doe',
        phone: '+1 (555) 987-6543',
        relationship: 'Sister',
    },
    preferences: {
        emailNotifications: true,
        pushNotifications: true,
        smsNotifications: false,
        weeklyReport: true,
        reminderTime: '09:00',
        language: 'en',
        theme: 'system',
    },
    privacy: {
        profileVisibility: 'community', // public, community, private
        showOnlineStatus: true,
        allowMessages: true,
        shareProgress: true,
        anonymousInCommunity: false,
    },
    stats: {
        daysActive: 45,
        assessmentsCompleted: 12,
        chatSessions: 28,
        activitiesCompleted: 67,
        currentStreak: 7,
        longestStreak: 14,
    },
};

// Mock settings
let mockSettings = {
    notifications: {
        email: {
            assessmentReminders: true,
            weeklyReport: true,
            communityActivity: true,
            productUpdates: false,
        },
        push: {
            chatMessages: true,
            crisisAlerts: true,
            activityReminders: true,
            peerMessages: true,
        },
        sms: {
            crisisAlerts: true,
            appointmentReminders: false,
        },
    },
    privacy: {
        profileVisibility: 'community',
        showOnlineStatus: true,
        allowMessages: true,
        shareDataForResearch: false,
        allowAnalytics: true,
    },
    display: {
        theme: 'system',
        fontSize: 'medium',
        reducedMotion: false,
        highContrast: false,
    },
    accessibility: {
        screenReaderOptimized: false,
        keyboardNavigation: true,
        captions: false,
    },
};

const profileService = {
    // Get user profile
    getProfile: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return { ...mockProfile };
        }
        const response = await api.get('/users/profile');
        return response.data;
    },

    // Update user profile
    updateProfile: async (data) => {
        if (import.meta.env.DEV) {
            await mockDelay(800);
            mockProfile = { ...mockProfile, ...data };
            return { ...mockProfile };
        }
        const response = await api.put('/users/profile', data);
        return response.data;
    },

    // Update avatar
    updateAvatar: async (file) => {
        if (import.meta.env.DEV) {
            await mockDelay(1000);
            // Create a fake URL for the uploaded image
            const fakeUrl = URL.createObjectURL(file);
            mockProfile.avatar = fakeUrl;
            return { avatar: fakeUrl };
        }
        const formData = new FormData();
        formData.append('avatar', file);
        const response = await api.post('/users/profile/avatar', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    // Delete avatar
    deleteAvatar: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            mockProfile.avatar = null;
            return { success: true };
        }
        const response = await api.delete('/users/profile/avatar');
        return response.data;
    },

    // Get settings
    getSettings: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return { ...mockSettings };
        }
        const response = await api.get('/users/settings');
        return response.data;
    },

    // Update settings
    updateSettings: async (category, data) => {
        if (import.meta.env.DEV) {
            await mockDelay(500);
            mockSettings[category] = { ...mockSettings[category], ...data };
            return { ...mockSettings };
        }
        const response = await api.put(`/users/settings/${category}`, data);
        return response.data;
    },

    // Change password
    changePassword: async (currentPassword, newPassword) => {
        if (import.meta.env.DEV) {
            await mockDelay(800);
            if (currentPassword !== 'demo') {
                throw new Error('Current password is incorrect');
            }
            return { success: true };
        }
        const response = await api.post('/users/change-password', {
            currentPassword,
            newPassword,
        });
        return response.data;
    },

    // Delete account
    deleteAccount: async (password) => {
        if (import.meta.env.DEV) {
            await mockDelay(1000);
            return { success: true };
        }
        const response = await api.delete('/users/account', {
            data: { password },
        });
        return response.data;
    },

    // Export data
    exportData: async () => {
        if (import.meta.env.DEV) {
            await mockDelay(2000);
            return {
                downloadUrl: '#',
                expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
            };
        }
        const response = await api.post('/users/export-data');
        return response.data;
    },

    // Get activity log
    getActivityLog: async (page = 0, size = 20) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return {
                content: [
                    { id: 1, action: 'login', timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), details: 'Logged in from Chrome on MacOS' },
                    { id: 2, action: 'assessment', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), details: 'Completed PHQ-9 assessment' },
                    { id: 3, action: 'chat', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), details: 'Chat session with Manō' },
                    { id: 4, action: 'profile_update', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), details: 'Updated profile information' },
                    { id: 5, action: 'activity', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(), details: 'Completed breathing exercise' },
                ],
                totalElements: 5,
                totalPages: 1,
            };
        }
        const response = await api.get('/users/activity-log', { params: { page, size } });
        return response.data;
    },

    // Get connected devices/sessions
    getSessions: async () => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return [
                {
                    id: 'session-1',
                    device: 'Chrome on MacOS',
                    location: 'San Francisco, CA',
                    lastActive: new Date().toISOString(),
                    isCurrent: true,
                },
                {
                    id: 'session-2',
                    device: 'Safari on iPhone',
                    location: 'San Francisco, CA',
                    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
                    isCurrent: false,
                },
            ];
        }
        const response = await api.get('/users/sessions');
        return response.data;
    },

    // Revoke session
    revokeSession: async (sessionId) => {
        if (import.meta.env.DEV) {
            await mockDelay();
            return { success: true };
        }
        const response = await api.delete(`/users/sessions/${sessionId}`);
        return response.data;
    },
};

export default profileService;