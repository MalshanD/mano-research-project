/**
 * C1SidebarNav — collapsible left rail for the Component-1 revamp.
 *
 * Renders the 6 consumer pages always; renders the 10 researcher
 * pages only when the authenticated user has the researcher role.
 * Active route is visually + aria highlighted.
 */

import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
    LayoutDashboard, Sparkles, ListTree, BrainCircuit,
    Lightbulb, MessageSquareHeart, Beaker, ListOrdered,
    Gauge, FileText, Cpu, SlidersHorizontal, ScanSearch,
    Zap, Stethoscope, BarChart3,
} from 'lucide-react';
import clsx from 'clsx';

const USER_ITEMS = [
    { to: '/c1/summary',        label: 'My Summary',           icon: LayoutDashboard },
    { to: '/c1/future',         label: 'See My Future',        icon: Sparkles },
    { to: '/c1/recommendation', label: 'AI Recommendation',    icon: ListTree },
    { to: '/c1/twin',           label: 'Digital Twin',         icon: BrainCircuit },
    { to: '/c1/risk',           label: 'Understand My Risk',   icon: Lightbulb },
    { to: '/c1/therapy',        label: 'Guided Therapy',       icon: MessageSquareHeart },
];

const RESEARCHER_ITEMS = [
    { to: '/c1/researcher/simulation-lab',         label: 'Simulation Lab',       icon: Beaker },
    { to: '/c1/researcher/sequencer',              label: 'Sequencer',            icon: ListOrdered },
    { to: '/c1/researcher/uncertainty',            label: 'Uncertainty Explorer', icon: Gauge },
    { to: '/c1/researcher/clinical-report',        label: 'Clinical + Batch',     icon: FileText },
    { to: '/c1/researcher/model-diagnostics',      label: 'Model Diagnostics',    icon: Cpu },
    { to: '/c1/researcher/what-if',                label: 'What-If Simulator',    icon: SlidersHorizontal },
    { to: '/c1/researcher/xai',                    label: 'XAI Explainer',        icon: ScanSearch },
    { to: '/c1/researcher/next-best-action',       label: 'Next-Best-Action',     icon: Zap },
    { to: '/c1/researcher/prescription',           label: 'AI Prescription',      icon: Stethoscope },
    { to: '/c1/researcher/intervention-compare',   label: 'Intervention Compare', icon: BarChart3 },
];

function Item({ to, label, Icon }) {
    return (
        <NavLink
            to={to}
            className={({ isActive }) =>
                clsx(
                    'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition',
                    isActive
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-100 font-medium'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100',
                )
            }
        >
            {({ isActive }) => (
                <>
                    <Icon aria-hidden="true" className={clsx('w-4 h-4 shrink-0', isActive ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-400')} />
                    <span className="truncate">{label}</span>
                </>
            )}
        </NavLink>
    );
}

export default function C1SidebarNav() {
    const { user } = useAuth() || {};
    const roles = (user?.roles || (user?.role ? [user.role] : [])).map((r) => r?.toLowerCase?.() || '');
    const isResearcher = roles.some((r) => r.includes('researcher'));

    return (
        <nav aria-label="Component 1 navigation" className="flex flex-col gap-1 p-3">
            <p className="px-3 mt-1 mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Your view
            </p>
            {USER_ITEMS.map((it) => (
                <Item key={it.to} to={it.to} label={it.label} Icon={it.icon} />
            ))}

            {isResearcher && (
                <>
                    <p className="px-3 mt-4 mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        Researcher
                    </p>
                    {RESEARCHER_ITEMS.map((it) => (
                        <Item key={it.to} to={it.to} label={it.label} Icon={it.icon} />
                    ))}
                </>
            )}
        </nav>
    );
}
