import { httpClient } from './api';
import { API_ENDPOINTS } from '../config/api.config';

// ─── Shape adapters ──────────────────────────────────────────────────────────

/** API session → frontend conversation */
function normalizeSession(s) {
    return {
        id: s.session_id,
        title: s.title || 'New Chat',
        createdAt: s.created_at,
        updatedAt: s.created_at,
        lastMessage: s.last_message || null,
        lastMessageSender: s.last_message_sender || null,
    };
}

/** Map DB role_type string → PERSONAS id */
const ROLE_TYPE_TO_PERSONA = {
    FRIEND:         'friend',
    COUNSELOR:      'counselor',
    MEDICAL_OFFICER:'medical_officer',
};

/** API message → frontend message */
function normalizeMessage(m) {
    return {
        id: m.id,
        content: m.message,
        senderId: m.sender === 'USER' ? 'user' : 'ai',
        senderType: m.sender,          // 'USER' | 'MODEL'
        timestamp: m.created_at,
        status: 'read',
        metadata: m.sender === 'MODEL' && m.role_type
            ? { persona: ROLE_TYPE_TO_PERSONA[m.role_type] || null }
            : undefined,
    };
}

// ─── Service ─────────────────────────────────────────────────────────────────

const chatService = {
    /** List sessions for a user  GET /chat/session/{user_id} */
    getConversations: async (userId) => {
        if (!userId) return [];
        const response = await httpClient.get(`${API_ENDPOINTS.CHAT.SESSIONS}/${userId}`);
        return (response.data || []).map(normalizeSession);
    },

    /** Get messages for a session  GET /chat/message/{session_id} */
    getMessages: async (sessionId) => {
        const response = await httpClient.get(`${API_ENDPOINTS.CHAT.MESSAGES}/${sessionId}`);
        return (response.data || []).map(normalizeMessage);
    },

    /** Create a new session  POST /chat/session/create/{user_id} */
    createConversation: async (userId) => {
        const response = await httpClient.post(
            `${API_ENDPOINTS.CHAT.CREATE_SESSION}/${userId}`
        );
        return normalizeSession({
            title: 'New Chat',
            created_at: new Date().toISOString(),
            ...response.data,
        });
    },

    /**
     * Send a message  POST /chat/message
     * Returns { userMessage, botMessage } so the hook can show both.
     */
    sendMessage: async (sessionId, content, persona = 'friend') => {
        const response = await httpClient.post(API_ENDPOINTS.CHAT.MESSAGE, {
            session_id: sessionId,
            message: content,
            persona,
        });
        const data = response.data;

        const userMessage = {
            id: `user-${Date.now()}`,
            content,
            senderId: 'user',
            senderType: 'USER',
            timestamp: data.timestamp || new Date().toISOString(),
            status: 'sent',
        };

        const botMessage = {
            id: `bot-${Date.now() + 1}`,
            content: data.bot_response,
            senderId: 'ai',
            senderType: 'MODEL',
            timestamp: data.timestamp || new Date().toISOString(),
            status: 'sent',
            metadata: {
                intent: data.intent,
                confidence: data.confidence,
                persona: data.persona_used,
            },
        };

        return { userMessage, botMessage };
    },

    /** Delete a session  DELETE /chat/session/{session_id} */
    deleteConversation: async (sessionId) => {
        const response = await httpClient.delete(
            `${API_ENDPOINTS.CHAT.DELETE_SESSION}/${sessionId}`
        );
        return response.data;
    },

    /** Placeholder — not yet in API */
    sendFeedback: async () => {},
};

export default chatService;