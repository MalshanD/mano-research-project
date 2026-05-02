import { createContext, useContext, useState, useCallback } from 'react';
import toast from 'react-hot-toast';

// Create context
const NotificationContext = createContext(null);

// Notification types
const NOTIFICATION_TYPES = {
    SUCCESS: 'success',
    ERROR: 'error',
    INFO: 'info',
    WARNING: 'warning',
    CRISIS: 'crisis',
};

// Notification Provider component
export function NotificationProvider({ children }) {
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);

    // Add notification to list
    const addNotification = useCallback((notification) => {
        const id = `notification-${Date.now()}`;
        const newNotification = {
            id,
            timestamp: new Date().toISOString(),
            read: false,
            ...notification,
        };

        setNotifications((prev) => [newNotification, ...prev].slice(0, 50)); // Keep last 50
        setUnreadCount((prev) => prev + 1);

        return id;
    }, []);

    // Show toast notification
    const showToast = useCallback((message, type = NOTIFICATION_TYPES.INFO, options = {}) => {
        const toastOptions = {
            duration: options.duration || 4000,
            ...options,
        };

        switch (type) {
            case NOTIFICATION_TYPES.SUCCESS:
                toast.success(message, toastOptions);
                break;
            case NOTIFICATION_TYPES.ERROR:
                toast.error(message, toastOptions);
                break;
            case NOTIFICATION_TYPES.WARNING:
                toast(message, {
                    ...toastOptions,
                    icon: '⚠️',
                    style: {
                        background: '#fef3c7',
                        color: '#92400e',
                    },
                });
                break;
            case NOTIFICATION_TYPES.CRISIS:
                toast.error(message, {
                    ...toastOptions,
                    duration: 10000,
                    icon: '🆘',
                    style: {
                        background: '#fee2e2',
                        color: '#991b1b',
                        fontWeight: '600',
                    },
                });
                break;
            default:
                toast(message, toastOptions);
        }
    }, []);

    // Success notification
    const success = useCallback(
        (message, options) => {
            showToast(message, NOTIFICATION_TYPES.SUCCESS, options);
            addNotification({ type: NOTIFICATION_TYPES.SUCCESS, message });
        },
        [showToast, addNotification]
    );

    // Error notification
    const error = useCallback(
        (message, options) => {
            showToast(message, NOTIFICATION_TYPES.ERROR, options);
            addNotification({ type: NOTIFICATION_TYPES.ERROR, message });
        },
        [showToast, addNotification]
    );

    // Info notification
    const info = useCallback(
        (message, options) => {
            showToast(message, NOTIFICATION_TYPES.INFO, options);
            addNotification({ type: NOTIFICATION_TYPES.INFO, message });
        },
        [showToast, addNotification]
    );

    // Warning notification
    const warning = useCallback(
        (message, options) => {
            showToast(message, NOTIFICATION_TYPES.WARNING, options);
            addNotification({ type: NOTIFICATION_TYPES.WARNING, message });
        },
        [showToast, addNotification]
    );

    // Crisis notification
    const crisis = useCallback(
        (message, options) => {
            showToast(message, NOTIFICATION_TYPES.CRISIS, options);
            addNotification({ type: NOTIFICATION_TYPES.CRISIS, message, priority: 'high' });
        },
        [showToast, addNotification]
    );

    // Mark notification as read
    const markAsRead = useCallback((id) => {
        setNotifications((prev) =>
            prev.map((notif) =>
                notif.id === id ? { ...notif, read: true } : notif
            )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
    }, []);

    // Mark all as read
    const markAllAsRead = useCallback(() => {
        setNotifications((prev) => prev.map((notif) => ({ ...notif, read: true })));
        setUnreadCount(0);
    }, []);

    // Remove notification
    const removeNotification = useCallback((id) => {
        setNotifications((prev) => {
            const notification = prev.find((n) => n.id === id);
            if (notification && !notification.read) {
                setUnreadCount((count) => Math.max(0, count - 1));
            }
            return prev.filter((n) => n.id !== id);
        });
    }, []);

    // Clear all notifications
    const clearAll = useCallback(() => {
        setNotifications([]);
        setUnreadCount(0);
    }, []);

    const value = {
        notifications,
        unreadCount,
        success,
        error,
        info,
        warning,
        crisis,
        addNotification,
        markAsRead,
        markAllAsRead,
        removeNotification,
        clearAll,
        types: NOTIFICATION_TYPES,
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
}

// Custom hook to use notification context
export function useNotification() {
    const context = useContext(NotificationContext);

    if (!context) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }

    return context;
}

export default NotificationContext;