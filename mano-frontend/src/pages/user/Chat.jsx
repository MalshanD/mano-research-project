import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { cn } from '../../utils/helpers';
import { useAuth } from '../../contexts/AuthContext';
import { useChat } from '../../hooks/useChat';
import { usePersona } from '../../components/features/chat/PersonaSelector';
import { Button, Modal, Alert } from '../../components/common';
import {
    ChatBubble,
    ChatInput,
    ChatWindow,
    ChatHeader,
    ChatSidebar,
    CrisisDetectionAlert,
    SuggestedPrompts,
} from '../../components/features/chat';
import { CrisisModal } from '../../components/features/crisis';
import {
    Bars3Icon,
    XMarkIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

function Chat() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user } = useAuth();

    const [showSidebar, setShowSidebar] = useState(false);
    const [showCrisisModal, setShowCrisisModal] = useState(false);
    const [showClearConfirm, setShowClearConfirm] = useState(false);
    const [showInfoModal, setShowInfoModal] = useState(false);
    const [personaToast, setPersonaToast] = useState(null);

    // ── Persona ──────────────────────────────────────────────────────────────
    const { persona, setPersona } = usePersona();

    const handlePersonaChange = (newPersona) => {
        setPersona(newPersona);
        // Show a brief inline toast
        setPersonaToast(newPersona);
        setTimeout(() => setPersonaToast(null), 2500);
    };

    const {
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
    } = useChat(searchParams.get('conversation'));

    // Show suggested prompts only for new/empty conversations
    const showSuggestions = messages.length === 0 && !isLoading;

    const handleSend = async (content) => {
        await sendMessage(content, persona);
    };

    const handleSelectPrompt = (prompt) => {
        handleSend(prompt);
    };

    const handleNewConversation = async () => {
        await createConversation();
        setShowSidebar(false);
    };

    const handleSelectConversation = (conv) => {
        selectConversation(conv);
        setShowSidebar(false);
    };

    const handleDeleteConversation = async (conv) => {
        await deleteConversation(conv.id);
    };

    const handleClearChat = () => {
        setShowClearConfirm(true);
    };

    const confirmClearChat = () => {
        clearChat();
        setShowClearConfirm(false);
    };

    const handleCrisisHelp = () => {
        setShowCrisisModal(true);
    };

    return (
        <div className="flex h-[calc(100vh-4rem)] -m-4 lg:-m-6">
            {/* Sidebar - Desktop */}
            <div className="hidden lg:block w-80 border-r border-sand/30 bg-white/60 backdrop-blur-sm">
                <ChatSidebar
                    conversations={conversations}
                    activeConversationId={activeConversation?.id}
                    onSelectConversation={handleSelectConversation}
                    onNewConversation={handleNewConversation}
                    onDeleteConversation={handleDeleteConversation}
                />
            </div>

            {/* Sidebar - Mobile */}
            {showSidebar && (
                <div className="fixed inset-0 z-50 lg:hidden">
                    <div
                        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
                        onClick={() => setShowSidebar(false)}
                    />
                    <div className="absolute left-0 top-0 bottom-0 w-80 bg-white/95 backdrop-blur-sm shadow-organic-lg animate-slide-in-left">
                        <div className="flex items-center justify-between p-4 border-b border-sand/30">
                            <h2 className="font-semibold text-terracotta-dark">{'\uD83D\uDCAC'} Conversations</h2>
                            <button
                                onClick={() => setShowSidebar(false)}
                                className="p-2 text-terracotta-light hover:text-terracotta hover:bg-cream rounded-xl"
                            >
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>
                        <ChatSidebar
                            conversations={conversations}
                            activeConversationId={activeConversation?.id}
                            onSelectConversation={handleSelectConversation}
                            onNewConversation={handleNewConversation}
                            onDeleteConversation={handleDeleteConversation}
                            className="border-none"
                        />
                    </div>
                </div>
            )}

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-ivory">
                {/* Header */}
                <ChatHeader
                    title="Manō"
                    subtitle={activeConversation?.title || 'AI Companion'}
                    status="online"
                    persona={persona}
                    onPersonaChange={handlePersonaChange}
                    showBackButton
                    onBack={() => setShowSidebar(true)}
                    onInfo={() => setShowInfoModal(true)}
                    onClear={handleClearChat}
                    onCrisis={handleCrisisHelp}
                />

                {/* Error Alert */}
                {error && (
                    <Alert variant="danger" className="mx-4 mt-2" dismissible>
                        {error}
                    </Alert>
                )}

                {/* Persona changed toast */}
                {personaToast && (
                    <div className={cn(
                        'mx-4 mt-2 px-4 py-2.5 rounded-xl border text-sm font-semibold flex items-center gap-2',
                        'animate-fade-in-down transition-all',
                        personaToast.pill
                    )}>
                        <span className="text-base">{personaToast.emoji}</span>
                        Switched to <strong>{personaToast.label}</strong> — {personaToast.description}
                    </div>
                )}

                {/* Crisis Detection Alert */}
                <CrisisDetectionAlert
                    show={crisisDetected}
                    crisisAlert={crisisAlert}
                    onDismiss={dismissCrisis}
                    onGetHelp={handleCrisisHelp}
                />

                {/* Chat Window */}
                <ChatWindow
                    messages={messages}
                    user={user}
                    isLoading={isLoading}
                    isTyping={isTyping}
                    onFeedback={sendFeedback}
                    className="flex-1"
                />

                {/* Suggested Prompts */}
                {showSuggestions && (
                    <SuggestedPrompts persona={persona} onSelect={handleSelectPrompt} />
                )}

                {/* Input */}
                <div className="p-4 bg-white/70 backdrop-blur-sm border-t border-sand/30">
                    <ChatInput
                        onSend={handleSend}
                        disabled={isLoading}
                        placeholder={
                            activeConversation
                                ? 'Type your message...'
                                : 'Start a new conversation...'
                        }
                    />
                </div>
            </div>

            {/* Crisis Modal */}
            <CrisisModal
                isOpen={showCrisisModal}
                onClose={() => setShowCrisisModal(false)}
            />

            {/* Clear Chat Confirmation */}
            <Modal
                isOpen={showClearConfirm}
                onClose={() => setShowClearConfirm(false)}
                title="Clear Chat"
                size="sm"
                footer={
                    <div className="flex justify-end gap-3">
                        <Button variant="ghost" onClick={() => setShowClearConfirm(false)}>
                            Cancel
                        </Button>
                        <Button variant="danger" onClick={confirmClearChat}>
                            Clear Chat
                        </Button>
                    </div>
                }
            >
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-2xl bg-butter flex items-center justify-center flex-shrink-0">
                        <ExclamationTriangleIcon className="w-5 h-5 text-terracotta" />
                    </div>
                    <div>
                        <p className="text-neutral-600">
                            Are you sure you want to clear this conversation? This action cannot be undone.
                        </p>
                    </div>
                </div>
            </Modal>

            {/* Info Modal */}
            <Modal
                isOpen={showInfoModal}
                onClose={() => setShowInfoModal(false)}
                title="About Manō Chat"
                size="md"
            >
                <div className="space-y-4">
                    <div className="flex items-center gap-4 p-4 bg-cream rounded-2xl border border-sand/30">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-terracotta to-terracotta-light flex items-center justify-center">
                            <span className="text-xl font-bold text-white font-display">M</span>
                        </div>
                        <div>
                            <h3 className="font-semibold text-terracotta-dark">{'\uD83C\uDF3F'} Manō AI Companion</h3>
                            <p className="text-sm text-terracotta/80">Always here to listen and support</p>
                        </div>
                    </div>

                    <div>
                        <h4 className="font-medium text-neutral-900 mb-2">What Manō Can Help With</h4>
                        <ul className="space-y-2 text-sm text-neutral-600">
                            <li className="flex items-start gap-2">
                                <span className="text-sage">{'\uD83C\uDF31'}</span>
                                Listening to your thoughts and feelings
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="text-sage">{'\uD83C\uDF3F'}</span>
                                Guiding breathing and relaxation exercises
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="text-sage">{'\uD83E\uDDE0'}</span>
                                Providing coping strategies for stress and anxiety
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="text-sage">{'\uD83D\uDC9A'}</span>
                                Offering emotional support 24/7
                            </li>
                        </ul>
                    </div>

                    <div className="p-4 bg-cream/60 rounded-2xl border border-sand/30">
                        <h4 className="font-medium text-neutral-900 mb-2">Important Note</h4>
                        <p className="text-sm text-neutral-600">
                            Manō is an AI assistant and not a replacement for professional mental health care.
                            If you're in crisis, please use the Crisis Help button to access emergency resources.
                        </p>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

export default Chat;