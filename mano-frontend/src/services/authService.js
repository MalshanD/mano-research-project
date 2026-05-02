import { httpClient } from './api';
import { API_ENDPOINTS } from '../config/api.config';
import { TOKEN_KEY, REFRESH_TOKEN_KEY, TOKEN_EXPIRY_KEY } from '../config/constants';

const authService = {
    /**
     * Unified login or register via POST /users/create/
     * Backend logic: if user exists with matching password → login;
     * if user does not exist → create new user and return token.
     * Response (201): a token string.
     */
    loginOrRegister: async ({ guest_name, password }) => {
        const response = await httpClient.post(API_ENDPOINTS.AUTH.CREATE_OR_LOGIN, {
            guest_name,
            password,
        });

        // Backend returns { message, user_id, guest_name }
        const { user_id, guest_name: returnedName, message } = response.data;

        // Use guest_name as a session token (no JWT from this backend yet)
        const sessionToken = returnedName || guest_name;
        localStorage.setItem(TOKEN_KEY, sessionToken);

        // Build user object from the response
        const user = {
            id: user_id,
            username: returnedName || guest_name,
            guest_name: returnedName || guest_name,
        };

        return { user, token: sessionToken, message };
    },


    /**
     * Login user (legacy endpoint)
     */
    login: async (credentials) => {
        const response = await httpClient.post(API_ENDPOINTS.AUTH.LOGIN, {
            usernameOrEmail: credentials.usernameOrEmail,
            password: credentials.password,
        });

        const { accessToken, refreshToken, expiresIn, user } = response.data;

        // Store tokens
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        localStorage.setItem(TOKEN_EXPIRY_KEY, Date.now() + expiresIn);

        return { user, accessToken };
    },

    /**
     * Register new user
     */
    register: async (userData) => {
        const response = await httpClient.post(API_ENDPOINTS.AUTH.REGISTER, {
            username: userData.username,
            email: userData.email,
            password: userData.password,
            firstName: userData.firstName,
            lastName: userData.lastName,
            phone: userData.phone || null,
            gender: userData.gender || null,
            dateOfBirth: userData.dateOfBirth || null,
            privacyConsent: userData.privacyConsent || false,
            dataSharingConsent: userData.dataSharingConsent || false,
        });

        return response.data;
    },

    /**
     * Logout user
     */
    logout: async () => {
        try {
            await httpClient.post(API_ENDPOINTS.AUTH.LOGOUT);
        } catch (error) {
            // Continue with local logout even if API fails
            console.warn('Logout API call failed:', error);
        } finally {
            // Clear local storage
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem(TOKEN_EXPIRY_KEY);
        }
    },

    /**
     * Get current user
     */
    getCurrentUser: async () => {
        const response = await httpClient.get(API_ENDPOINTS.AUTH.ME);
        return response.data;
    },

    /**
     * Verify email
     */
    verifyEmail: async (token) => {
        const response = await httpClient.get(`${API_ENDPOINTS.AUTH.VERIFY_EMAIL}/${token}`);
        return response.data;
    },

    /**
     * Forgot password - request reset
     */
    forgotPassword: async (email) => {
        const response = await httpClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email });
        return response.data;
    },

    /**
     * Change password
     */
    changePassword: async (currentPassword, newPassword) => {
        const response = await httpClient.post(API_ENDPOINTS.AUTH.CHANGE_PASSWORD, {
            currentPassword,
            newPassword,
        });
        return response.data;
    },

    /**
     * Refresh token
     */
    refreshToken: async () => {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await httpClient.post(API_ENDPOINTS.AUTH.REFRESH, { refreshToken });
        const { accessToken, refreshToken: newRefreshToken, expiresIn } = response.data;

        localStorage.setItem(TOKEN_KEY, accessToken);
        if (newRefreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
        }
        localStorage.setItem(TOKEN_EXPIRY_KEY, Date.now() + expiresIn);

        return { accessToken };
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated: () => {
        const token = localStorage.getItem(TOKEN_KEY);
        const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

        if (!token) return false;
        if (expiry && Date.now() > parseInt(expiry)) return false;

        return true;
    },

    /**
     * Get stored token
     */
    getToken: () => {
        return localStorage.getItem(TOKEN_KEY);
    },
};

export default authService;