import { useState, useRef, useEffect } from 'react';
import { format } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Modal, Button, Avatar, Input } from '../../common';
import { usePeerMessages } from '../../../hooks/useCommunity';
import { PaperAirplaneIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../../../contexts/AuthContext';

function PeerMessageModal({
                              isOpen,
                              onClose,
                              peer,
                          }) {
    const { user } = useAuth();
    const [message, setMessage] = useState('');
    const messagesEndRef = useRef(null);

    const { messages, isLoading, sendMessage, isSending } = usePeerMessages(peer?.id);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!message.trim() || isSending) return;
        await sendMessage(message);
        setMessage('');
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (!peer) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title=""
            size="lg"
            className="flex flex-col max-h-[80vh]"
        >
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-neutral-100 -mt-2">
                <Avatar
                    src={peer.avatar}
                    firstName={peer.firstName}
                    lastName={peer.lastName}
                    size="md"
                    status={peer.status}
                />
                <div>
                    <p className="font-semibold text-neutral-900">
                        {peer.firstName} {peer.lastName}
                    </p>
                    <p className="text-sm text-neutral-500 capitalize">{peer.status}</p>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-4 min-h-[300px] max-h-[400px]">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full" />
                    </div>
                ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mb-4">
                            <span className="text-2xl">👋</span>
                        </div>
                        <p className="text-neutral-900 font-medium">Start a conversation</p>
                        <p className="text-sm text-neutral-500 mt-1">
                            Say hello to {peer.firstName}!
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((msg) => {
                            const isUser = msg.senderId === 'user';
                            return (
                                <div
                                    key={msg.id}
                                    className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
                                >
                                    <div
                                        className={cn(
                                            'max-w-[70%] px-4 py-2 rounded-2xl',
                                            isUser
                                                ? 'bg-primary-500 text-white rounded-br-md'
                                                : 'bg-neutral-100 text-neutral-900 rounded-bl-md'
                                        )}
                                    >
                                        <p className="text-sm">{msg.content}</p>
                                        <p
                                            className={cn(
                                                'text-xs mt-1',
                                                isUser ? 'text-primary-200' : 'text-neutral-500'
                                            )}
                                        >
                                            {format(new Date(msg.timestamp), 'h:mm a')}
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="pt-4 border-t border-neutral-100">
                <div className="flex items-center gap-2">
                    <Input
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type a message..."
                        disabled={isSending}
                        className="flex-1"
                    />
                    <Button
                        variant="primary"
                        size="icon"
                        onClick={handleSend}
                        disabled={!message.trim() || isSending}
                        loading={isSending}
                    >
                        <PaperAirplaneIcon className="w-5 h-5" />
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

export default PeerMessageModal;