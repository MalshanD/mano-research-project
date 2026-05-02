import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { STORAGE_KEYS } from '../config/constants';

// Create context
const ThemeContext = createContext(null);

// Theme options
const THEMES = {
    LIGHT: 'light',
    DARK: 'dark',
    SYSTEM: 'system',
};

// Theme Provider component
export function ThemeProvider({ children }) {
    const [theme, setTheme] = useState(() => {
        // Get saved theme or default to system
        const savedTheme = localStorage.getItem(STORAGE_KEYS.THEME);
        return savedTheme || THEMES.LIGHT;
    });

    const [resolvedTheme, setResolvedTheme] = useState('light');

    // Update resolved theme based on system preference
    useEffect(() => {
        const updateResolvedTheme = () => {
            if (theme === THEMES.SYSTEM) {
                const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                setResolvedTheme(systemPrefersDark ? 'dark' : 'light');
            } else {
                setResolvedTheme(theme);
            }
        };

        updateResolvedTheme();

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', updateResolvedTheme);

        return () => mediaQuery.removeEventListener('change', updateResolvedTheme);
    }, [theme]);

    // Apply theme to document
    useEffect(() => {
        const root = window.document.documentElement;

        // Remove old theme class
        root.classList.remove('light', 'dark');

        // Add new theme class
        root.classList.add(resolvedTheme);

        // Update meta theme-color
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute(
                'content',
                resolvedTheme === 'dark' ? '#171717' : '#0ea5e9'
            );
        }
    }, [resolvedTheme]);

    // Change theme
    const changeTheme = useCallback((newTheme) => {
        setTheme(newTheme);
        localStorage.setItem(STORAGE_KEYS.THEME, newTheme);
    }, []);

    // Toggle between light and dark
    const toggleTheme = useCallback(() => {
        const newTheme = resolvedTheme === 'light' ? THEMES.DARK : THEMES.LIGHT;
        changeTheme(newTheme);
    }, [resolvedTheme, changeTheme]);

    const value = {
        theme,
        resolvedTheme,
        isDark: resolvedTheme === 'dark',
        changeTheme,
        toggleTheme,
        themes: THEMES,
    };

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// Custom hook to use theme context
export function useTheme() {
    const context = useContext(ThemeContext);

    if (!context) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }

    return context;
}

export default ThemeContext;