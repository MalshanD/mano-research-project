import { useState, useEffect } from 'react';
import { BREAKPOINTS } from '../config/constants';

/**
 * Hook for responsive media queries
 */
export function useMediaQuery(query) {
    const [matches, setMatches] = useState(() => {
        if (typeof window !== 'undefined') {
            return window.matchMedia(query).matches;
        }
        return false;
    });

    useEffect(() => {
        if (typeof window === 'undefined') return;

        const mediaQuery = window.matchMedia(query);
        setMatches(mediaQuery.matches);

        const handler = (event) => setMatches(event.matches);

        // Use addEventListener for modern browsers
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handler);
        } else {
            // Fallback for older browsers
            mediaQuery.addListener(handler);
        }

        return () => {
            if (mediaQuery.removeEventListener) {
                mediaQuery.removeEventListener('change', handler);
            } else {
                mediaQuery.removeListener(handler);
            }
        };
    }, [query]);

    return matches;
}

/**
 * Preset breakpoint hooks
 */
export function useIsMobile() {
    return useMediaQuery(`(max-width: ${BREAKPOINTS.SM - 1}px)`);
}

export function useIsTablet() {
    return useMediaQuery(
        `(min-width: ${BREAKPOINTS.SM}px) and (max-width: ${BREAKPOINTS.LG - 1}px)`
    );
}

export function useIsDesktop() {
    return useMediaQuery(`(min-width: ${BREAKPOINTS.LG}px)`);
}

export function useBreakpoint() {
    const isMobile = useMediaQuery(`(max-width: ${BREAKPOINTS.SM - 1}px)`);
    const isTablet = useMediaQuery(
        `(min-width: ${BREAKPOINTS.SM}px) and (max-width: ${BREAKPOINTS.LG - 1}px)`
    );
    const isDesktop = useMediaQuery(`(min-width: ${BREAKPOINTS.LG}px)`);
    const isLargeDesktop = useMediaQuery(`(min-width: ${BREAKPOINTS.XL}px)`);

    if (isLargeDesktop) return 'xl';
    if (isDesktop) return 'lg';
    if (isTablet) return 'md';
    if (isMobile) return 'sm';
    return 'xs';
}

export default useMediaQuery;