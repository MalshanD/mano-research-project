/**
 * ResearcherRoute — frontend half of the role guard.
 *
 * Backend enforcement lives in core/role_guard.py — that's the
 * authoritative line of defence. This component just keeps the SPA
 * out of pages it can't usefully render for non-researchers, so the
 * UX is "you see what you can use" rather than "you get a 403".
 *
 * Roles come from the existing AuthContext.
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { ROLES } from '../../config/constants';
import { Lock } from 'lucide-react';

export default function ResearcherRoute({ children }) {
    const { user } = useAuth() || {};
    const roles = (user?.roles || (user?.role ? [user.role] : [])).map((r) => r?.toLowerCase?.() || '');
    const isResearcher = roles.some((r) => r.includes('researcher'));

    if (!user) return <Navigate to="/?auth=open" replace />;
    if (!isResearcher) {
        return (
            <main className="max-w-2xl mx-auto px-4 py-16 text-center">
                <Lock aria-hidden="true" className="w-10 h-10 mx-auto text-slate-400" />
                <h1 className="mt-4 text-xl font-semibold text-slate-900 dark:text-slate-100">
                    Researcher view
                </h1>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                    These tools are for users with the <code className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-xs">{ROLES.RESEARCHER}</code> role.
                    If you believe this is in error, contact your administrator.
                </p>
            </main>
        );
    }

    return children;
}
