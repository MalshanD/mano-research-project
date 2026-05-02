import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import websocketService from '../services/websocketService';
import { useAuth } from './AuthContext';
import { useNotification } from './NotificationContext';
import { WS_TOPICS } from '../config/api.config';

// Create context
const WebSocketContext = createContext(null);

// WebSocket Provider component
export function WebSocketProvider({ children }) {
    const { isAuthenticated } = useAuth();
    const { crisis, info } = useNotification();

    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState(null);
    const messageHandlers = useRef(new Map());

    // Connect when authenticated
    useEffect(() => {
        // WebSocket is disabled — backend does not have a STOMP/SockJS endpoint yet.
        // Re-enable when the backend supports WebSocket connections.
        // if (isAuthenticated) {
        //     connectWebSocket();
        // } else {
        //     disconnectWebSocket();
        // }
        return () => {};
    }, [isAuthenticated]);

    // Connect to WebSocket
    const connectWebSocket = useCallback(() => {
        websocketService.connect(
            () => {
                setIsConnected(true);
                setConnectionError(null);
                subscribeToDefaultTopics();
            },
            (error) => {
                setConnectionError(error);
                setIsConnected(false);
            }
        );

        // Listen for connection state changes
        websocketService.addListener('disconnect', () => setIsConnected(false));
        websocketService.addListener('connect', () => setIsConnected(true));
        websocketService.addListener('error', (err) => setConnectionError(err));
    }, []);

    // Disconnect from WebSocket
    const disconnectWebSocket = useCallback(() => {
        websocketService.disconnect();
        setIsConnected(false);
    }, []);

    // Subscribe to default topics
    const subscribeToDefaultTopics = useCallback(() => {
        // Subscribe to user predictions
        websocketService.subscribe(WS_TOPICS.USER_PREDICTIONS, (data) => {
            handleMessage('prediction', data);
            info('New prediction result available');
        });

        // Subscribe to cluster updates
        websocketService.subscribe(WS_TOPICS.USER_CLUSTER_UPDATES, (data) => {
            handleMessage('clusterUpdate', data);
            info('Your peer group has been updated');
        });

        // Subscribe to interventions
        websocketService.subscribe(WS_TOPICS.USER_INTERVENTIONS, (data) => {
            handleMessage('intervention', data);
            info('New activity recommendation available');
        });

        // Subscribe to chat notifications
        websocketService.subscribe(WS_TOPICS.USER_CHAT_NOTIFICATIONS, (data) => {
            handleMessage('chatNotification', data);
        });

        // Subscribe to crisis alerts (for all users to show resources)
        websocketService.subscribe(WS_TOPICS.CRISIS_ALERTS, (data) => {
            handleMessage('crisisAlert', data);
            if (data.userId === 'self' || data.broadcast) {
                crisis('Crisis support resources are available. You are not alone.');
            }
        });
    }, [info, crisis]);

    // Handle incoming message
    const handleMessage = useCallback((type, data) => {
        const handlers = messageHandlers.current.get(type);
        if (handlers) {
            handlers.forEach((handler) => handler(data));
        }
    }, []);

    // Register message handler
    const onMessage = useCallback((type, handler) => {
        if (!messageHandlers.current.has(type)) {
            messageHandlers.current.set(type, new Set());
        }
        messageHandlers.current.get(type).add(handler);

        // Return unsubscribe function
        return () => {
            messageHandlers.current.get(type)?.delete(handler);
        };
    }, []);

    // Subscribe to custom topic
    const subscribe = useCallback((topic, callback) => {
        websocketService.subscribe(topic, callback);
    }, []);

    // Unsubscribe from topic
    const unsubscribe = useCallback((topic) => {
        websocketService.unsubscribe(topic);
    }, []);

    // Send message
    const send = useCallback((destination, message) => {
        return websocketService.send(destination, message);
    }, []);

    // Send chat message
    const sendChatMessage = useCallback((message, sessionId) => {
        return send(WS_TOPICS.CHAT, { message, sessionId });
    }, [send]);

    const value = {
        isConnected,
        connectionError,
        connect: connectWebSocket,
        disconnect: disconnectWebSocket,
        subscribe,
        unsubscribe,
        send,
        sendChatMessage,
        onMessage,
    };

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    );
}

// Custom hook to use WebSocket context
export function useWebSocket() {
    const context = useContext(WebSocketContext);

    if (!context) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }

    return context;
}

export default WebSocketContext;