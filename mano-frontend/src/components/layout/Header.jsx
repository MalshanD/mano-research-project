import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
    Bars3Icon,
    BellIcon,
    MagnifyingGlassIcon,
    Cog6ToothIcon,
    UserCircleIcon,
    ArrowRightOnRectangleIcon,
    MoonIcon,
    SunIcon,
    QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';
import { BellIcon as BellSolidIcon } from '@heroicons/react/24/solid';
import { cn } from '../../utils/helpers';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import logoImg from '../../assets/images/logo.png';
import { useNotification } from '../../contexts/NotificationContext';
import Avatar from '../common/Avatar';
import Badge from '../common/Badge';
import IconButton from '../common/IconButton';

function Header({ onMenuClick, showMenuButton = true }) {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { isDark, toggleTheme } = useTheme();
    const { notifications, unreadCount, markAllAsRead } = useNotification();
    const [searchOpen, setSearchOpen] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const userMenuItems = [
        {
            label: 'My Profile',
            icon: <UserCircleIcon className="w-5 h-5" />,
            onClick: () => navigate('/profile'),
        },
        {
            label: 'Settings',
            icon: <Cog6ToothIcon className="w-5 h-5" />,
            onClick: () => navigate('/settings'),
        },
        {
            label: 'Help & Support',
            icon: <QuestionMarkCircleIcon className="w-5 h-5" />,
            onClick: () => navigate('/help'),
        },
        { type: 'divider' },
        {
            label: 'Sign Out',
            icon: <ArrowRightOnRectangleIcon className="w-5 h-5" />,
            onClick: handleLogout,
            danger: true,
        },
    ];

    return (
        <header className="sticky top-0 z-40 bg-white/70 backdrop-blur-lg border-b border-sand/30">
            <div className="flex items-center justify-between h-16 px-4 lg:px-6">
                {/* Left Section */}
                <div className="flex items-center gap-4">
                    {showMenuButton && (
                        <IconButton
                            icon={<Bars3Icon className="w-6 h-6" />}
                            variant="ghost"
                            onClick={onMenuClick}
                            tooltip="Toggle menu"
                            className="lg:hidden"
                        />
                    )}

                    {/* Logo - Mobile */}
                    <Link to="/" className="flex items-center gap-2 lg:hidden">
                        <img src={logoImg} alt="Manō" className="w-8 h-8 rounded-2xl object-cover shadow-organic" />
                    </Link>

                    {/* Search Bar - Desktop */}
                    {/* <div className="hidden md:flex items-center">
                        <div className="relative">
                            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-terracotta-light/60" />
                            <input
                                type="text"
                                placeholder="Search..."
                                className="w-64 lg:w-80 pl-10 pr-4 py-2 bg-cream/50 border border-sand/40 rounded-2xl text-sm placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-peach/50 focus:border-terracotta-light transition-all"
                            />
                            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden lg:inline-flex items-center px-2 py-0.5 text-xs text-terracotta-light/60 bg-cream rounded-lg">
                                \u2318K
                            </kbd>
                        </div>
                    </div> */}
                </div>

                {/* Right Section */}
                <div className="flex items-center gap-2">
                    {/* Search - Mobile */}
                    <IconButton
                        icon={<MagnifyingGlassIcon className="w-5 h-5" />}
                        variant="ghost"
                        onClick={() => setSearchOpen(!searchOpen)}
                        className="md:hidden"
                        tooltip="Search"
                    />

                    {/* Theme Toggle */}
                    <IconButton
                        icon={isDark ? <SunIcon className="w-5 h-5" /> : <MoonIcon className="w-5 h-5" />}
                        variant="ghost"
                        onClick={toggleTheme}
                        tooltip={isDark ? 'Light mode' : 'Dark mode'}
                    />

                    {/* Notifications */}
                    <Menu as="div" className="relative">
                        <Menu.Button className="relative p-2 text-neutral-600 hover:bg-cream rounded-xl transition-colors">
                            {unreadCount > 0 ? (
                                <>
                                    <BellSolidIcon className="w-5 h-5 text-terracotta" />
                                    <span className="absolute top-1 right-1 w-4 h-4 bg-coral text-white text-xs font-medium rounded-full flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                                </>
                            ) : (
                                <BellIcon className="w-5 h-5" />
                            )}
                        </Menu.Button>

                        <Transition
                            as={Fragment}
                            enter="transition ease-out duration-100"
                            enterFrom="transform opacity-0 scale-95"
                            enterTo="transform opacity-100 scale-100"
                            leave="transition ease-in duration-75"
                            leaveFrom="transform opacity-100 scale-100"
                            leaveTo="transform opacity-0 scale-95"
                        >
                            <Menu.Items className="absolute right-0 mt-2 w-80 origin-top-right rounded-2xl bg-white shadow-organic-lg border border-sand/30 focus:outline-none overflow-hidden">
                                <div className="px-4 py-3 border-b border-sand/30 flex items-center justify-between">
                                    <h3 className="font-semibold text-neutral-900">Notifications</h3>
                                    {unreadCount > 0 && (
                                        <button
                                            onClick={markAllAsRead}
                                            className="text-xs text-terracotta hover:text-terracotta-dark"
                                        >
                                            Mark all as read
                                        </button>
                                    )}
                                </div>
                                <div className="max-h-96 overflow-y-auto">
                                    {notifications.length === 0 ? (
                                        <div className="px-4 py-8 text-center">
                                            <BellIcon className="w-8 h-8 text-sand mx-auto mb-2" />
                                            <p className="text-sm text-neutral-500">No notifications yet</p>
                                        </div>
                                    ) : (
                                        notifications.slice(0, 5).map((notif) => (
                                            <Menu.Item key={notif.id}>
                                                {({ active }) => (
                                                    <div
                                                        className={cn(
                                                            'px-4 py-3 cursor-pointer transition-colors',
                                                            active && 'bg-cream/60',
                                                            !notif.read && 'bg-peach/20'
                                                        )}
                                                    >
                                                        <p className="text-sm text-neutral-800">{notif.message}</p>
                                                        <p className="text-xs text-neutral-400 mt-1">
                                                            {new Date(notif.timestamp).toLocaleTimeString()}
                                                        </p>
                                                    </div>
                                                )}
                                            </Menu.Item>
                                        ))
                                    )}
                                </div>
                                {notifications.length > 0 && (
                                    <div className="px-4 py-3 border-t border-sand/30">
                                        <Link
                                            to="/notifications"
                                            className="text-sm text-terracotta hover:text-terracotta-dark font-medium"
                                        >
                                            View all notifications
                                        </Link>
                                    </div>
                                )}
                            </Menu.Items>
                        </Transition>
                    </Menu>

                    {/* User Menu Button */}
                    <Menu as="div" className="relative">
                        <Menu.Button className="flex items-center gap-3 p-1.5 hover:bg-cream rounded-2xl transition-colors">
                            <Avatar
                                src={user?.avatar}
                                firstName={user?.guest_name}
                                size="sm"
                                status="online"
                            />
                            <div className="hidden lg:block text-left">
                                <p className="text-sm font-medium text-neutral-800 truncate max-w-[140px]">
                                    {user?.guest_name || 'Guest'}
                                </p>
                                <p className="text-xs text-neutral-500">
                                    Guest User
                                </p>
                            </div>
                        </Menu.Button>

                        <Transition
                            as={Fragment}
                            enter="transition ease-out duration-100"
                            enterFrom="transform opacity-0 scale-95"
                            enterTo="transform opacity-100 scale-100"
                            leave="transition ease-in duration-75"
                            leaveFrom="transform opacity-100 scale-100"
                            leaveTo="transform opacity-0 scale-95"
                        >
                            <Menu.Items className="absolute right-0 mt-2 w-56 origin-top-right rounded-2xl bg-white shadow-organic-lg border border-sand/30 focus:outline-none overflow-hidden">
                                {/* User Info Header — visible on mobile in dropdown */}
                                <div className="px-4 py-3 border-b border-sand/30 lg:hidden">
                                    <p className="text-sm font-semibold text-neutral-800">
                                        {user?.guest_name || 'Guest'}
                                    </p>
                                    <p className="text-xs text-neutral-500">Guest User</p>
                                </div>

                                <div className="py-1">
                                    {userMenuItems.map((item, index) => {
                                        if (item.type === 'divider') {
                                            return <div key={index} className="my-1 border-t border-neutral-100" />;
                                        }

                                        return (
                                            <Menu.Item key={index}>
                                                {({ active }) => (
                                                    <button
                                                        onClick={item.onClick}
                                                        className={cn(
                                                            'w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors rounded-xl mx-1',
                                                            active ? 'bg-cream/60' : '',
                                                            item.danger ? 'text-coral-dark' : 'text-neutral-700'
                                                        )}
                                                    >
                            <span className={item.danger ? 'text-coral' : 'text-terracotta-light'}>
                              {item.icon}
                            </span>
                                                        {item.label}
                                                    </button>
                                                )}
                                            </Menu.Item>
                                        );
                                    })}
                                </div>
                            </Menu.Items>
                        </Transition>
                    </Menu>
                </div>
            </div>

            {/* Mobile Search Bar */}
            {searchOpen && (
                <div className="px-4 pb-4 md:hidden animate-fade-in-down">
                    <div className="relative">
                        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-terracotta-light/60" />
                        <input
                            type="text"
                            placeholder="Search..."
                            autoFocus
                            className="w-full pl-10 pr-4 py-2.5 bg-cream/50 border border-sand/40 rounded-2xl text-sm placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-peach/50 focus:border-terracotta-light"
                        />
                    </div>
                </div>
            )}
        </header>
    );
}

export default Header;