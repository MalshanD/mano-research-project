import { Fragment } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import {
    XMarkIcon,
    HomeIcon,
    ChatBubbleLeftRightIcon,
    ChartBarIcon,
    ClipboardDocumentListIcon,
    UserGroupIcon,
    SparklesIcon,
    UserCircleIcon,
    Cog6ToothIcon,
    ShieldCheckIcon,
    BeakerIcon,
    ExclamationTriangleIcon,
    HeartIcon,
    BookOpenIcon,
    PuzzlePieceIcon,
    LightBulbIcon,
    Squares2X2Icon,
    ArrowTrendingUpIcon,
    ListBulletIcon,
    CpuChipIcon,
    QuestionMarkCircleIcon,
    ChatBubbleBottomCenterTextIcon,
    AdjustmentsHorizontalIcon,
    DocumentTextIcon,
    ServerIcon,
} from '@heroicons/react/24/outline';
import {
    HomeIcon as HomeIconSolid,
    ChatBubbleLeftRightIcon as ChatIconSolid,
    ChartBarIcon as ChartIconSolid,
    UserGroupIcon as UserGroupIconSolid,
} from '@heroicons/react/24/solid';
import { cn } from '../../utils/helpers';
import { useAuth } from '../../contexts/AuthContext';
import logoImg from '../../assets/images/logo.png';
import { ROLES } from '../../config/constants';

// Navigation items configuration
const navigationItems = {
    main: [
        {
            name: 'Dashboard',
            href: '/dashboard',
            icon: HomeIcon,
            activeIcon: HomeIconSolid,
        },
        {
            name: 'Chat',
            href: '/chat',
            icon: ChatBubbleLeftRightIcon,
            activeIcon: ChatIconSolid,
        },
        {
            name: 'Assessments',
            href: '/assessments',
            icon: ClipboardDocumentListIcon,
        },
        {
            name: 'Activities',
            href: '/activities',
            icon: SparklesIcon,
        },
        {
            name: 'Thought Journal',
            href: '/journal',
            icon: BookOpenIcon,
        },
        {
            name: 'Predictions',
            href: '/predictions',
            icon: ChartBarIcon,
            activeIcon: ChartIconSolid,
        },
        {
            name: 'Community',
            href: '/community',
            icon: UserGroupIcon,
            activeIcon: UserGroupIconSolid,
        },
        {
            name: 'Games',
            href: '/games',
            icon: PuzzlePieceIcon,
            emoji: '\uD83C\uDFAE',
        },
        {
            name: 'Insights',
            href: '/insights',
            icon: LightBulbIcon,
        },
        {
            name: 'Therapy',
            href: '/therapy',
            icon: HeartIcon,
        },
    ],
    professional: [
        {
            name: 'Patient Monitoring',
            href: '/professional/patients',
            icon: HeartIcon,
            roles: [ROLES.PROFESSIONAL],
        },
        {
            name: 'Crisis Alerts',
            href: '/professional/alerts',
            icon: ExclamationTriangleIcon,
            roles: [ROLES.PROFESSIONAL],
            badgeColor: 'danger',
        },
    ],
    admin: [
        {
            name: 'User Management',
            href: '/admin/users',
            icon: ShieldCheckIcon,
            roles: [ROLES.ADMIN],
        },
        {
            name: 'System Health',
            href: '/admin/system',
            icon: BeakerIcon,
            roles: [ROLES.ADMIN],
        },
    ],
    // ── Component-1 (revamp) consumer pages — visible to every signed-in user
    c1: [
        { name: 'My Summary',          href: '/c1/summary',        icon: Squares2X2Icon },
        { name: 'See My Future',       href: '/c1/future',         icon: ArrowTrendingUpIcon },
        { name: 'AI Recommendation',   href: '/c1/recommendation', icon: ListBulletIcon },
        { name: 'Digital Twin',        href: '/c1/twin',           icon: CpuChipIcon },
        { name: 'Understand My Risk',  href: '/c1/risk',           icon: QuestionMarkCircleIcon },
        { name: 'Guided Therapy',      href: '/c1/therapy',        icon: ChatBubbleBottomCenterTextIcon },
    ],
    // ── Researcher-only Component-1 tools
    c1Researcher: [
        { name: 'Simulation Lab',          href: '/c1/researcher/simulation-lab',     icon: BeakerIcon,                roles: [ROLES.RESEARCHER, ROLES.ADMIN] },
        { name: 'Intervention Sequencer',  href: '/c1/researcher/sequencer',          icon: AdjustmentsHorizontalIcon, roles: [ROLES.RESEARCHER, ROLES.ADMIN] },
        { name: 'Uncertainty Explorer',    href: '/c1/researcher/uncertainty',        icon: ChartBarIcon,              roles: [ROLES.RESEARCHER, ROLES.ADMIN] },
        { name: 'Clinical + Batch Report', href: '/c1/researcher/clinical-report',    icon: DocumentTextIcon,          roles: [ROLES.RESEARCHER, ROLES.ADMIN] },
        { name: 'Model Diagnostics',       href: '/c1/researcher/model-diagnostics',  icon: ServerIcon,                roles: [ROLES.RESEARCHER, ROLES.ADMIN] },
    ],
    secondary: [
        {
            name: 'Profile',
            href: '/profile',
            icon: UserCircleIcon,
        },
        {
            name: 'Settings',
            href: '/settings',
            icon: Cog6ToothIcon,
        },
    ],
};

function NavItem({ item, collapsed }) {
    const location = useLocation();
    const isActive = location.pathname === item.href || location.pathname.startsWith(`${item.href}/`);
    const Icon = isActive && item.activeIcon ? item.activeIcon : item.icon;

    return (
        <NavLink
            to={item.href}
            className={({ isActive }) =>
                cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-2xl text-sm font-medium transition-all duration-200',
                    'hover:bg-cream group',
                    isActive
                        ? 'bg-cream text-terracotta shadow-organic hover:bg-cream'
                        : 'text-neutral-600 hover:text-terracotta-dark',
                    collapsed && 'justify-center px-2'
                )
            }
        >
            {item.emoji && !collapsed ? (
                <span className="text-lg flex-shrink-0">{item.emoji}</span>
            ) : (
                <Icon className={cn('w-5 h-5 flex-shrink-0', isActive ? 'text-terracotta' : 'text-neutral-400 group-hover:text-terracotta-light')} />
            )}
            {!collapsed && (
                <>
                    <span className="flex-1">{item.name}</span>
                    {item.badge && (
                        <span
                            className={cn(
                                'px-2 py-0.5 text-xs font-medium rounded-full',
                                item.badgeColor === 'danger'
                                    ? 'bg-crisis-100 text-crisis-700'
                                    : 'bg-peach text-terracotta-dark'
                            )}
                        >
              {item.badge}
            </span>
                    )}
                </>
            )}
        </NavLink>
    );
}

function SidebarContent({ collapsed, onClose }) {
    const { hasRole, hasAnyRole } = useAuth();

    const filterByRole = (items) => {
        return items.filter((item) => {
            if (!item.roles) return true;
            return hasAnyRole(item.roles);
        });
    };

    return (
        <div className="flex flex-col h-full">
            {/* Logo */}
            <div className={cn('flex items-center h-16 px-4 border-b border-sand/40', collapsed && 'justify-center px-2')}>
                <NavLink to="/" className="flex items-center gap-3" onClick={onClose}>
                    <img src={logoImg} alt="Manō" className="w-10 h-10 rounded-2xl object-cover shadow-organic" />
                    {!collapsed && (
                        <div>
                            <h1 className="text-xl font-bold font-display text-organic-gradient">Manō</h1>
                            <p className="text-xs text-neutral-400 font-hand text-base">Mental Wellness</p>
                        </div>
                    )}
                </NavLink>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
                {/* Main Navigation */}
                <div>
                    {!collapsed && (
                        <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                            Main Menu
                        </h2>
                    )}
                    <div className="space-y-1">
                        {navigationItems.main.map((item) => (
                            <NavItem key={item.href} item={item} collapsed={collapsed} />
                        ))}
                    </div>
                </div>

                {/* ── Component-1 consumer pages ───────────── */}
                <div>
                    {!collapsed && (
                        <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                            Wellness Engine
                        </h2>
                    )}
                    <div className="space-y-1">
                        {navigationItems.c1.map((item) => (
                            <NavItem key={item.href} item={item} collapsed={collapsed} />
                        ))}
                    </div>
                </div>

                {/* ── Component-1 researcher tools (role-gated) ── */}
                {hasAnyRole([ROLES.RESEARCHER, ROLES.ADMIN]) && (
                    <div>
                        {!collapsed && (
                            <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                                Research Tools
                            </h2>
                        )}
                        <div className="space-y-1">
                            {filterByRole(navigationItems.c1Researcher).map((item) => (
                                <NavItem key={item.href} item={item} collapsed={collapsed} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Professional Navigation */}
                {hasAnyRole([ROLES.PROFESSIONAL, ROLES.ADMIN]) && (
                    <div>
                        {!collapsed && (
                            <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                                Professional
                            </h2>
                        )}
                        <div className="space-y-1">
                            {filterByRole(navigationItems.professional).map((item) => (
                                <NavItem key={item.href} item={item} collapsed={collapsed} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Admin Navigation */}
                {hasRole(ROLES.ADMIN) && (
                    <div>
                        {!collapsed && (
                            <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                                Administration
                            </h2>
                        )}
                        <div className="space-y-1">
                            {filterByRole(navigationItems.admin).map((item) => (
                                <NavItem key={item.href} item={item} collapsed={collapsed} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Secondary Navigation */}
                <div>
                    {!collapsed && (
                        <h2 className="px-3 mb-2 text-xs font-semibold text-terracotta-light/70 uppercase tracking-wider">
                            Account
                        </h2>
                    )}
                    <div className="space-y-1">
                        {navigationItems.secondary.map((item) => (
                            <NavItem key={item.href} item={item} collapsed={collapsed} />
                        ))}
                    </div>
                </div>
            </nav>

            {/* Help Card */}
            {!collapsed && (
                <div className="p-4">
                    <div className="p-4 bg-gradient-to-br from-cream to-peach/40 rounded-2xl border border-sand/30">
                        <h3 className="font-semibold text-terracotta-dark mb-1">Need Help? 🌱</h3>
                        <p className="text-sm text-terracotta/80 mb-3">
                            Our support team is here for you 24/7
                        </p>
                        <button className="w-full px-4 py-2 bg-white text-terracotta text-sm font-medium rounded-2xl hover:bg-ivory transition-colors shadow-organic">
                            Contact Support
                        </button>
                    </div>
                </div>
            )}

            {/* Crisis Hotline */}
            {!collapsed && (
                <div className="px-4 pb-4">
                    <div className="p-3 bg-coral-light/10 border border-coral-light/30 rounded-2xl text-center">
                        <p className="text-xs text-coral-dark font-medium">National Mental Health Helpline</p>

                        <a href="tel:1-800-273-8255" className="text-lg font-bold text-coral-dark hover:text-coral">
                        1926
                            </a>
                    </div>
                </div>

                )}
</div>
);
}

// Desktop Sidebar
function DesktopSidebar({ collapsed, setCollapsed }) {
    return (
        <aside
            className={cn(
                'hidden lg:flex flex-col fixed inset-y-0 left-0 bg-white/90 backdrop-blur-sm border-r border-sand/30 transition-all duration-300 z-30',
                collapsed ? 'w-20' : 'w-64'
            )}
        >
            <SidebarContent collapsed={collapsed} />

            {/* Collapse Toggle */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="absolute -right-3 top-20 w-6 h-6 bg-white border border-sand/50 rounded-full shadow-organic flex items-center justify-center text-terracotta-light hover:text-terracotta hover:border-terracotta-light transition-colors"
            >
                <svg
                    className={cn('w-4 h-4 transition-transform', collapsed && 'rotate-180')}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
            </button>
        </aside>
    );
}

// Mobile Sidebar (Drawer)
function MobileSidebar({ isOpen, onClose }) {
    return (
        <Transition show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50 lg:hidden" onClose={onClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-hidden">
                    <Transition.Child
                        as={Fragment}
                        enter="transform transition ease-in-out duration-300"
                        enterFrom="-translate-x-full"
                        enterTo="translate-x-0"
                        leave="transform transition ease-in-out duration-200"
                        leaveFrom="translate-x-0"
                        leaveTo="-translate-x-full"
                    >
                        <Dialog.Panel className="fixed inset-y-0 left-0 w-72 bg-white shadow-xl">
                            <div className="absolute top-3 right-3">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    aria-label="Close navigation"
                                    className="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-900 hover:bg-cream"
                                >
                                    <XMarkIcon className="w-5 h-5" />
                                </button>
                            </div>
                            <SidebarContent collapsed={false} onClose={onClose} />
                        </Dialog.Panel>
                    </Transition.Child>
                </div>
            </Dialog>
        </Transition>
    );
}

// Public component — composes desktop + mobile.
export default function Sidebar({ isOpen, onClose, collapsed, setCollapsed }) {
    return (
        <>
            <DesktopSidebar collapsed={collapsed} setCollapsed={setCollapsed} />
            <MobileSidebar isOpen={isOpen} onClose={onClose} />
        </>
    );
}
