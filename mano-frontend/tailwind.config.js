/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Primary - Therapeutic Sky Blue (kept for compatibility)
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                    950: '#082f49',
                },
                // Accent - Warm Encouragement (kept for compatibility)
                accent: {
                    50: '#fff7ed',
                    100: '#ffedd5',
                    200: '#fed7aa',
                    300: '#fdba74',
                    400: '#fb923c',
                    500: '#f97316',
                    600: '#ea580c',
                    700: '#c2410c',
                    800: '#9a3412',
                    900: '#7c2d12',
                },
                // Success - Growth
                success: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    200: '#bbf7d0',
                    300: '#86efac',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    700: '#15803d',
                    800: '#166534',
                    900: '#14532d',
                },
                // Warning
                warning: {
                    50: '#fefce8',
                    100: '#fef9c3',
                    200: '#fef08a',
                    300: '#fde047',
                    400: '#facc15',
                    500: '#eab308',
                    600: '#ca8a04',
                    700: '#a16207',
                    800: '#854d0e',
                    900: '#713f12',
                },
                // Crisis/Danger
                crisis: {
                    50: '#fef2f2',
                    100: '#fee2e2',
                    200: '#fecaca',
                    300: '#fca5a5',
                    400: '#f87171',
                    500: '#ef4444',
                    600: '#dc2626',
                    700: '#b91c1c',
                    800: '#991b1b',
                    900: '#7f1d1d',
                },
                // Neutral - Grounding
                neutral: {
                    50: '#fafafa',
                    100: '#f5f5f5',
                    200: '#e5e5e5',
                    300: '#d4d4d4',
                    400: '#a3a3a3',
                    500: '#737373',
                    600: '#525252',
                    700: '#404040',
                    800: '#262626',
                    900: '#171717',
                    950: '#0a0a0a',
                },
                // Risk level semantic colors
                risk: {
                    low: '#22c55e',
                    medium: '#eab308',
                    high: '#f97316',
                    severe: '#ef4444',
                    critical: '#dc2626',
                },

                /* ──── Organic Flow palette ──── */
                ivory: '#fff8ef',
                cream: '#fff3e0',
                butter: '#fff9e6',
                sand: '#f5e6d3',
                terracotta: {
                    light: '#e8926e',
                    DEFAULT: '#c0735a',
                    dark: '#a35d47',
                },
                coral: {
                    light: '#ff8a80',
                    DEFAULT: '#e07065',
                    dark: '#c25650',
                },
                sage: {
                    light: '#b5c9a8',
                    DEFAULT: '#8fae7e',
                    dark: '#6d8c60',
                },
                lavender: {
                    light: '#d4bde6',
                    DEFAULT: '#b49ad0',
                    dark: '#8e6eb5',
                },
                sky: {
                    light: '#a8d8ea',
                    DEFAULT: '#7ec8e3',
                    dark: '#5aafcf',
                },
                peach: '#ffd5c2',
                blush: '#ffe0e6',
                mint: '#d4f5e9',
            },
            fontFamily: {
                display: ['DM Sans', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'],
                body: ['DM Sans', 'Inter', 'system-ui', 'sans-serif'],
                hand: ['Caveat', 'cursive'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            fontSize: {
                '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
            },
            spacing: {
                '18': '4.5rem',
                '88': '22rem',
                '128': '32rem',
            },
            borderRadius: {
                '4xl': '2rem',
                'blob': '60% 40% 50% 50% / 50% 60% 40% 50%',
            },
            boxShadow: {
                'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
                'soft-lg': '0 10px 40px -10px rgba(0, 0, 0, 0.1), 0 2px 10px -2px rgba(0, 0, 0, 0.04)',
                'inner-soft': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
                'glow': '0 0 20px rgba(14, 165, 233, 0.3)',
                'glow-success': '0 0 20px rgba(34, 197, 94, 0.3)',
                'glow-warning': '0 0 20px rgba(234, 179, 8, 0.3)',
                'glow-crisis': '0 0 20px rgba(239, 68, 68, 0.3)',
                'organic': '0 4px 24px rgba(192, 115, 90, 0.10)',
                'organic-lg': '0 8px 40px rgba(192, 115, 90, 0.15)',
                'organic-hover': '0 12px 48px rgba(192, 115, 90, 0.20)',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'fade-in-up': 'fadeInUp 0.5s ease-out',
                'fade-in-down': 'fadeInDown 0.5s ease-out',
                'slide-in-right': 'slideInRight 0.3s ease-out',
                'slide-in-left': 'slideInLeft 0.3s ease-out',
                'scale-in': 'scaleIn 0.2s ease-out',
                'pulse-soft': 'pulseSoft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'bounce-soft': 'bounceSoft 1s infinite',
                'spin-slow': 'spin 3s linear infinite',
                'gradient': 'gradient 8s ease infinite',
                'float': 'float 6s ease-in-out infinite',
                'shake': 'shake 0.5s ease-in-out',
                // Organic Flow animations
                'blob-morph': 'blobMorph 8s ease-in-out infinite',
                'wobble': 'wobble 3s ease-in-out infinite',
                'sway': 'sway 4s ease-in-out infinite',
                'bounce-in': 'bounceIn 0.6s cubic-bezier(0.68, -0.55, 0.27, 1.55)',
                'grow-bar': 'growBar 1s ease-out forwards',
                'breathe': 'breathe 8s ease-in-out infinite',
                'float-slow': 'float 8s ease-in-out infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                fadeInUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                fadeInDown: {
                    '0%': { opacity: '0', transform: 'translateY(-10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(20px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                slideInLeft: {
                    '0%': { opacity: '0', transform: 'translateX(-20px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                scaleIn: {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
                pulseSoft: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.7' },
                },
                bounceSoft: {
                    '0%, 100%': { transform: 'translateY(-5%)' },
                    '50%': { transform: 'translateY(0)' },
                },
                gradient: {
                    '0%, 100%': { backgroundPosition: '0% 50%' },
                    '50%': { backgroundPosition: '100% 50%' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-20px)' },
                },
                shake: {
                    '0%, 100%': { transform: 'translateX(0)' },
                    '15%': { transform: 'translateX(-6px)' },
                    '30%': { transform: 'translateX(6px)' },
                    '45%': { transform: 'translateX(-4px)' },
                    '60%': { transform: 'translateX(4px)' },
                    '75%': { transform: 'translateX(-2px)' },
                    '90%': { transform: 'translateX(2px)' },
                },
                // Organic Flow keyframes
                blobMorph: {
                    '0%, 100%': { borderRadius: '60% 40% 50% 50% / 50% 60% 40% 50%' },
                    '25%': { borderRadius: '40% 60% 55% 45% / 55% 40% 60% 45%' },
                    '50%': { borderRadius: '55% 45% 40% 60% / 45% 55% 50% 50%' },
                    '75%': { borderRadius: '45% 55% 60% 40% / 60% 45% 55% 40%' },
                },
                wobble: {
                    '0%, 100%': { transform: 'rotate(-2deg)' },
                    '50%': { transform: 'rotate(2deg)' },
                },
                sway: {
                    '0%, 100%': { transform: 'translateX(0px)' },
                    '50%': { transform: 'translateX(10px)' },
                },
                bounceIn: {
                    '0%': { opacity: '0', transform: 'scale(0.3)' },
                    '50%': { opacity: '1', transform: 'scale(1.05)' },
                    '70%': { transform: 'scale(0.95)' },
                    '100%': { transform: 'scale(1)' },
                },
                growBar: {
                    '0%': { width: '0%' },
                    '100%': { width: 'var(--bar-width, 100%)' },
                },
                breathe: {
                    '0%, 100%': { transform: 'scale(1)', opacity: '0.8' },
                    '50%': { transform: 'scale(1.15)', opacity: '1' },
                },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'mesh-gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'calm-gradient': 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #bae6fd 100%)',
                // Organic Flow gradients
                'organic-warm': 'linear-gradient(135deg, #fff8ef 0%, #ffe0b2 50%, #ffd5c2 100%)',
                'organic-sage': 'linear-gradient(135deg, #d4f5e9 0%, #b5c9a8 100%)',
                'organic-sunset': 'linear-gradient(135deg, #ffd5c2 0%, #e8926e 50%, #c0735a 100%)',
                'organic-lavender': 'linear-gradient(135deg, #ffe0e6 0%, #d4bde6 100%)',
            },
            transitionDuration: {
                '400': '400ms',
            },
            zIndex: {
                '60': '60',
                '70': '70',
                '80': '80',
                '90': '90',
                '100': '100',
            },
        },
    },
    plugins: [],
}