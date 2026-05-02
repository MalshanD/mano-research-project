import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { cn } from '../../utils/helpers';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { STORAGE_KEYS } from '../../config/constants';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';

function MainLayout({ showFooter = false }) {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage(
        STORAGE_KEYS.SIDEBAR_COLLAPSED,
        false
    );

    return (
        <div className="min-h-screen bg-ivory relative overflow-hidden">
            {/* Organic background blobs */}
            <div className="blob blob-terracotta w-96 h-96 -top-48 -right-48 opacity-10 fixed" />
            <div className="blob blob-sage w-80 h-80 bottom-20 -left-40 opacity-10 fixed" />
            <div className="blob blob-lavender w-64 h-64 top-1/2 right-1/4 opacity-[0.06] fixed" />

            {/* Sidebar */}
            <Sidebar
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                collapsed={sidebarCollapsed}
                setCollapsed={setSidebarCollapsed}
            />

            {/* Main Content Area */}
            <div
                className={cn(
                    'flex flex-col min-h-screen transition-all duration-300 relative z-10',
                    sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'
                )}
            >
                {/* Header */}
                <Header
                    onMenuClick={() => setSidebarOpen(true)}
                    showMenuButton={true}
                />

                {/* Page Content */}
                <main className="flex-1">
                    <div className="p-4 lg:p-6">
                        <Outlet />
                    </div>
                </main>

                {/* Footer */}
                {showFooter && <Footer minimal />}
            </div>
        </div>
    );
}

export default MainLayout;