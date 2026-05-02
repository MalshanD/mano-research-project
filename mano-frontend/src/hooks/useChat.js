import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import chatService from '../services/chatService';
import { useAuth } from '../contexts/AuthContext';

// Crisis keywords for detection
const CRISIS_KEYWORDS = [
    'suicide', 'kill myself', 'end my life', 'want to die',
    'self-harm', 'hurt myself', 'cutting', 'overdose',
    'hopeless', 'no reason to live', 'better off dead',
    'can\'t go on', 'give up', 'end it all',
];

export function useChat(conversationId = null) {
    const { user } = useAuth();
    const { subscribe, unsubscribe, isConnected } = useWebSocket();

    const [messages, setMessages] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [activeConversation, setActiveConversation] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const [error, setError] = useState(null);
    const [crisisDetected, setCrisisDetected] = useState(false);
    const [crisisAlert, setCrisisAlert] = useState(null);  // Server-side crisis data

    const typingTimeoutRef = useRef(null);

    // Check for crisis keywords (client-side fallback)
    const checkForCrisis = useCallback((text) => {
        const lowerText = text.toLowerCase();
        return CRISIS_KEYWORDS.some((keyword) => lowerText.includes(keyword));
    }, []);

    // Load conversations
    const loadConversations = useCallback(async () => {
        if (!user?.id) return;
        try {
            setIsLoading(true);
            const data = await chatService.getConversations(user.id);
            setConversations(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [user]);

    // Load messages for a conversation
    const loadMessages = useCallback(async (convId) => {
        if (!convId) return;

        try {
            setIsLoading(true);
            const data = await chatService.getMessages(convId);
            setMessages(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Create new conversation
    const createConversation = useCallback(async () => {
        try {
            setIsLoading(true);
            const newConv = await chatService.createConversation(user?.id);
            setConversations((prev) => [newConv, ...prev]);
            setActiveConversation(newConv);
            setMessages([]);
            return newConv;
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setIsLoading(false);
        }
    }, [user]);

    // Send message
    const sendMessage = useCallback(async (content, persona = null, convId = null) => {
        const targetConvId = convId || activeConversation?.id;

        // Check for crisis
        if (checkForCrisis(content)) {
            setCrisisDetected(true);
        }

        // Optimistic user message
        const optimisticMessage = {
            id: `temp-${Date.now()}`,
            content,
            senderId: 'user',
            senderType: 'USER',
            timestamp: new Date().toISOString(),
            status: 'sending',
        };

        setMessages((prev) => [...prev, optimisticMessage]);

        try {
            // If no conversation exists, create one
            let conversationId = targetConvId;
            if (!conversationId) {
                const newConv = await createConversation();
                conversationId = newConv?.id;
            }

            if (!conversationId) {
                throw new Error('Failed to create conversation');
            }

            // Single API call — returns confirmed user msg + bot response
            const { userMessage, botMessage } = await chatService.sendMessage(
                conversationId,
                content,
                persona?.id || 'friend',
            );

            // Replace optimistic with confirmed user message
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === optimisticMessage.id
                        ? { ...userMessage, status: 'sent' }
                        : msg
                )
            );

            // Brief typing indicator for natural feel
            setIsTyping(true);
            await new Promise((r) => setTimeout(r, 700));
            setIsTyping(false);

            // Add bot response
            setMessages((prev) => [...prev, botMessage]);

            // Check for server-side crisis alert in the response
            if (botMessage?.crisis_alert?.crisis_detected) {
                setCrisisDetected(true);
                setCrisisAlert(botMessage.crisis_alert);
            }

            // Update conversation list
            setConversations((prev) =>
                prev.map((conv) =>
                    conv.id === conversationId
                        ? { ...conv, lastMessage: content, lastMessageSender: 'USER', updatedAt: new Date().toISOString() }
                        : conv
                )
            );

            return userMessage;
        } catch (err) {
            setIsTyping(false);

            // Update message status to error
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === optimisticMessage.id
                        ? { ...msg, status: 'error' }
                        : msg
                )
            );

            setError(err.message);
            return null;
        }
    }, [activeConversation, checkForCrisis, createConversation]);

    // Delete conversation
    const deleteConversation = useCallback(async (convId) => {
        try {
            await chatService.deleteConversation(convId);
            setConversations((prev) => prev.filter((c) => c.id !== convId));

            if (activeConversation?.id === convId) {
                setActiveConversation(null);
                setMessages([]);
            }
        } catch (err) {
            setError(err.message);
        }
    }, [activeConversation]);

    // Clear chat
    const clearChat = useCallback(() => {
        setMessages([]);
        setCrisisDetected(false);
        setCrisisAlert(null);
    }, []);

    // Select conversation
    const selectConversation = useCallback((conv) => {
        setActiveConversation(conv);
        setCrisisDetected(false);
        setCrisisAlert(null);
        loadMessages(conv.id);
    }, [loadMessages]);

    // Dismiss crisis alert
    const dismissCrisis = useCallback(() => {
        setCrisisDetected(false);
        setCrisisAlert(null);
    }, []);

    // Send feedback
    const sendFeedback = useCallback(async (messageId, feedback) => {
        try {
            await chatService.sendFeedback(messageId, feedback);
        } catch (err) {
            console.error('Failed to send feedback:', err);
        }
    }, []);

    // WebSocket subscription for real-time messages
    useEffect(() => {
        if (!isConnected || !activeConversation?.id) return;

        const handleNewMessage = (message) => {
            if (message.conversationId === activeConversation.id) {
                setMessages((prev) => [...prev, message]);
            }
        };

        const handleTyping = (data) => {
            if (data.conversationId === activeConversation.id && data.senderId !== user?.id) {
                setIsTyping(true);
                clearTimeout(typingTimeoutRef.current);
                typingTimeoutRef.current = setTimeout(() => setIsTyping(false), 3000);
            }
        };

        subscribe(`/topic/chat/${activeConversation.id}`, handleNewMessage);
        subscribe(`/topic/chat/${activeConversation.id}/typing`, handleTyping);

        return () => {
            unsubscribe(`/topic/chat/${activeConversation.id}`);
            unsubscribe(`/topic/chat/${activeConversation.id}/typing`);
        };
    }, [isConnected, activeConversation, user, subscribe, unsubscribe]);

    // Load conversations on mount
    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    // Load initial conversation if provided
    useEffect(() => {
        if (conversationId) {
            const conv = conversations.find((c) => c.id === conversationId);
            if (conv) {
                selectConversation(conv);
            }
        }
    }, [conversationId, conversations, selectConversation]);

    return {
        messages,
        conversations,
        activeConversation,
        isLoading,
        isTyping,
        error,
        crisisDetected,
        crisisAlert,
        sendMessage,
        createConversation,
        deleteConversation,
        selectConversation,
        clearChat,
        dismissCrisis,
        sendFeedback,
        loadConversations,
    };
}

export default useChat;