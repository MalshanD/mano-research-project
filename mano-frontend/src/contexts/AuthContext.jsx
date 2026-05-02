import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { TOKEN_KEY } from '../config/constants';

const USER_ID_KEY = 'mano_user_id';

const AuthContext = createContext(null);

// Mock user for development
const MOCK_USER = {
    id: 1,
    username: 'demo_user',
    email: 'demo@mano.app',
    firstName: 'Demo',
    lastName: 'User',
    roles: ['ROLE_USER'],
    avatar: null,
};

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [error, setError] = useState(null);

    const navigate = useNavigate();

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem(TOKEN_KEY);

            if (!token) {
                setIsAuthenticated(false);
                setUser(null);
                return;
            }

            // Mock token for dev testing
            if (import.meta.env.DEV && token === 'mock-token') {
                setUser(MOCK_USER);
                setIsAuthenticated(true);
                return;
            }

            // This backend has no /api/auth/me endpoint.
            // The token IS the guest_name — restore the session from it directly.
            // user_id is separately persisted in localStorage at login time.
            const storedUserId = localStorage.getItem(USER_ID_KEY);
            const restoredUser = {
                id: storedUserId ? Number(storedUserId) : undefined,
                username: token,
                guest_name: token,
            };
            setUser(restoredUser);
            setIsAuthenticated(true);

        } catch (err) {
            console.error('Auth check failed:', err);
            setIsAuthenticated(false);
            setUser(null);
            localStorage.removeItem(TOKEN_KEY);
        } finally {
            setIsLoading(false);
        }
    }, []);


    const loginOrRegister = useCallback(async ({ guest_name, password }) => {
        setIsLoading(true);
        setError(null);

        try {
            const { user: userData, token } = await authService.loginOrRegister({ guest_name, password });
            // Persist the real user_id so it survives page refresh
            if (userData?.id !== undefined) {
                localStorage.setItem(USER_ID_KEY, String(userData.id));
            }
            setUser(userData);
            setIsAuthenticated(true);
            return { success: true, user: userData, token };
        } catch (err) {
            const errorMessage = err.response?.data?.detail?.[0]?.msg
                || err.response?.data?.detail
                || err.message
                || 'Authentication failed. Please try again.';
            setError(errorMessage);
            return { success: false, error: errorMessage };
        } finally {
            setIsLoading(false);
        }
    }, []);

    const login = useCallback(async (credentials) => {
        setIsLoading(true);
        setError(null);

        try {
            // For development, allow mock login
            if (import.meta.env.DEV && credentials.usernameOrEmail === 'demodemodemo' && credentials.password === 'demodemodemo') {
                localStorage.setItem(TOKEN_KEY, 'mock-token');
                setUser(MOCK_USER);
                setIsAuthenticated(true);
                return { success: true, user: MOCK_USER };
            }

            const { user: userData } = await authService.login(credentials);
            setUser(userData);
            setIsAuthenticated(true);
            return { success: true, user: userData };
        } catch (err) {
            const errorMessage = err.message || 'Login failed. Please try again.';
            setError(errorMessage);
            return { success: false, error: errorMessage };
        } finally {
            setIsLoading(false);
        }
    }, []);

    const register = useCallback(async (userData) => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await authService.register(userData);
            return { success: true, message: response.message };
        } catch (err) {
            const errorMessage = err.message || 'Registration failed. Please try again.';
            setError(errorMessage);
            return { success: false, error: errorMessage };
        } finally {
            setIsLoading(false);
        }
    }, []);

    const logout = useCallback(async () => {
        setIsLoading(true);

        try {
            await authService.logout();
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            setUser(null);
            setIsAuthenticated(false);
            setIsLoading(false);
            localStorage.removeItem(USER_ID_KEY);
            navigate('/login');
        }
    }, [navigate]);

    const updateUser = useCallback((userData) => {
        setUser((prev) => ({ ...prev, ...userData }));
    }, []);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    const hasRole = useCallback(
        (role) => {
            if (!user?.roles) return false;
            return user.roles.includes(role);
        },
        [user]
    );

    const hasAnyRole = useCallback(
        (roles) => {
            if (!user?.roles) return false;
            return roles.some((role) => user.roles.includes(role));
        },
        [user]
    );

    const value = {
        user,
        isLoading,
        isAuthenticated,
        error,
        loginOrRegister,
        login,
        register,
        logout,
        updateUser,
        checkAuth,
        clearError,
        hasRole,
        hasAnyRole,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    return context;
}

export default AuthContext;