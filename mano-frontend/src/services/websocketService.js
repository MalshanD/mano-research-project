import { Client } from '@stomp/stompjs';
import SockJS from 'sockjs-client';
import { WS_BASE_URL, TOKEN_KEY } from '../config/constants';

class WebSocketService {
    constructor() {
        this.client = null;
        this.subscriptions = new Map();
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.listeners = new Map();
    }

    /**
     * Connect to WebSocket server
     */
    connect(onConnect, onError) {
        const token = localStorage.getItem(TOKEN_KEY);

        this.client = new Client({
            webSocketFactory: () => new SockJS(`${WS_BASE_URL}?token=${token}`),
            connectHeaders: {
                Authorization: `Bearer ${token}`,
            },
            debug: (str) => {
                if (import.meta.env.DEV) {
                    console.log('[WebSocket]', str);
                }
            },
            reconnectDelay: this.reconnectDelay,
            heartbeatIncoming: 4000,
            heartbeatOutgoing: 4000,
            onConnect: () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                console.log('[WebSocket] Connected');

                // Resubscribe to all topics
                this.subscriptions.forEach((callback, topic) => {
                    this._subscribe(topic, callback);
                });

                if (onConnect) onConnect();
                this._notifyListeners('connect');
            },
            onDisconnect: () => {
                this.isConnected = false;
                console.log('[WebSocket] Disconnected');
                this._notifyListeners('disconnect');
            },
            onStompError: (frame) => {
                console.error('[WebSocket] STOMP Error:', frame);
                if (onError) onError(frame);
                this._notifyListeners('error', frame);
            },
            onWebSocketError: (event) => {
                console.error('[WebSocket] WebSocket Error:', event);
                this._handleReconnect();
            },
        });

        this.client.activate();
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.client) {
            this.subscriptions.clear();
            this.client.deactivate();
            this.isConnected = false;
            console.log('[WebSocket] Manually disconnected');
        }
    }

    /**
     * Subscribe to a topic
     */
    subscribe(topic, callback) {
        this.subscriptions.set(topic, callback);

        if (this.isConnected && this.client) {
            this._subscribe(topic, callback);
        }
    }

    /**
     * Internal subscribe method
     */
    _subscribe(topic, callback) {
        if (!this.client || !this.isConnected) return;

        const subscription = this.client.subscribe(topic, (message) => {
            try {
                const data = JSON.parse(message.body);
                callback(data);
            } catch (error) {
                console.error('[WebSocket] Failed to parse message:', error);
                callback(message.body);
            }
        });

        return subscription;
    }

    /**
     * Unsubscribe from a topic
     */
    unsubscribe(topic) {
        this.subscriptions.delete(topic);
    }

    /**
     * Send message to a destination
     */
    send(destination, body) {
        if (!this.client || !this.isConnected) {
            console.warn('[WebSocket] Cannot send - not connected');
            return false;
        }

        this.client.publish({
            destination,
            body: typeof body === 'string' ? body : JSON.stringify(body),
        });

        return true;
    }

    /**
     * Handle reconnection
     */
    _handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[WebSocket] Reconnecting... Attempt ${this.reconnectAttempts}`);
            setTimeout(() => {
                if (!this.isConnected) {
                    this.client?.activate();
                }
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('[WebSocket] Max reconnection attempts reached');
            this._notifyListeners('maxReconnectAttempts');
        }
    }

    /**
     * Add connection state listener
     */
    addListener(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }

    /**
     * Remove connection state listener
     */
    removeListener(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

    /**
     * Notify all listeners
     */
    _notifyListeners(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach((callback) => callback(data));
        }
    }

    /**
     * Check connection status
     */
    getConnectionStatus() {
        return this.isConnected;
    }
}

// Singleton instance
const websocketService = new WebSocketService();

export default websocketService;