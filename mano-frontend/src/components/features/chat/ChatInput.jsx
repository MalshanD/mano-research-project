import { useState, useRef, useEffect } from 'react';
import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import {
    PaperAirplaneIcon,
    FaceSmileIcon,
    PaperClipIcon,
    MicrophoneIcon,
    XMarkIcon,
} from '@heroicons/react/24/outline';

// Simple emoji picker data
const quickEmojis = ['😊', '😔', '😰', '😤', '🙏', '❤️', '👍', '💪'];

function ChatInput({
                       onSend,
                       onTyping,
                       disabled = false,
                       placeholder = 'Type your message...',
                       maxLength = 2000,
                       showAttachment = false,
                       showVoice = false,
                       className,
                   }) {
    const [message, setMessage] = useState('');
    const [showEmoji, setShowEmoji] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const textareaRef = useRef(null);
    const typingTimeoutRef = useRef(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
        }
    }, [message]);

    const handleChange = (e) => {
        const value = e.target.value;
        if (value.length <= maxLength) {
            setMessage(value);

            // Typing indicator debounce
            if (onTyping) {
                onTyping(true);
                clearTimeout(typingTimeoutRef.current);
                typingTimeoutRef.current = setTimeout(() => {
                    onTyping(false);
                }, 1000);
            }
        }
    };

    const handleSend = () => {
        const trimmedMessage = message.trim();
        if (trimmedMessage && !disabled) {
            onSend(trimmedMessage);
            setMessage('');
            setShowEmoji(false);
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleEmojiSelect = (emoji) => {
        setMessage((prev) => prev + emoji);
        textareaRef.current?.focus();
    };

    const handleVoiceRecord = () => {
        setIsRecording(!isRecording);
        // Voice recording implementation would go here
    };

    return (
        <div className={cn('relative', className)}>
            {/* Emoji Picker */}
            {showEmoji && (
                <div className="absolute bottom-full left-0 mb-2 p-3 bg-white rounded-xl shadow-lg border border-neutral-100 animate-fade-in">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-neutral-500">Quick reactions</span>
                        <button
                            onClick={() => setShowEmoji(false)}
                            className="ml-auto p-1 text-neutral-400 hover:text-neutral-600"
                        >
                            <XMarkIcon className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="flex gap-2">
                        {quickEmojis.map((emoji) => (
                            <button
                                key={emoji}
                                onClick={() => handleEmojiSelect(emoji)}
                                className="text-xl hover:scale-125 transition-transform p-1"
                            >
                                {emoji}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input Container */}
            <div
                className={cn(
                    'flex items-end gap-2 p-3 bg-white rounded-2xl border border-neutral-200',
                    'transition-all duration-200 focus-within:outline-none focus-within:ring-0 focus-within:border-neutral-200',
                    disabled && 'opacity-50 cursor-not-allowed'
                )}
            >
                {/* Emoji Toggle */}
                <button
                    onClick={() => setShowEmoji(!showEmoji)}
                    disabled={disabled}
                    className={cn(
                        'p-2 rounded-lg transition-colors',
                        showEmoji ? 'bg-primary-50 text-primary-600' : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50'
                    )}
                >
                    <FaceSmileIcon className="w-5 h-5" />
                </button>

                {/* Attachment */}
                {showAttachment && (
                    <button
                        disabled={disabled}
                        className="p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 rounded-lg transition-colors"
                    >
                        <PaperClipIcon className="w-5 h-5" />
                    </button>
                )}

                {/* Text Input */}
                <div className="flex-1 relative">
          <textarea
              ref={textareaRef}
              value={message}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={placeholder}
              rows={1}
              className={cn(
                  'w-full resize-none bg-transparent text-neutral-900 placeholder-neutral-400',
                  'focus:outline-none focus:ring-0 focus:shadow-none text-sm leading-relaxed',
                  'disabled:cursor-not-allowed'
              )}
              style={{ maxHeight: '150px' }}
          />
                </div>

                {/* Character Count */}
                {message.length > maxLength * 0.8 && (
                    <span
                        className={cn(
                            'text-xs',
                            message.length >= maxLength ? 'text-crisis-500' : 'text-neutral-400'
                        )}
                    >
            {message.length}/{maxLength}
          </span>
                )}

                {/* Voice Recording */}
                {showVoice && !message && (
                    <button
                        onClick={handleVoiceRecord}
                        disabled={disabled}
                        className={cn(
                            'p-2 rounded-lg transition-colors',
                            isRecording
                                ? 'bg-crisis-50 text-crisis-600 animate-pulse'
                                : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50'
                        )}
                    >
                        <MicrophoneIcon className="w-5 h-5" />
                    </button>
                )}

                {/* Send Button */}
                <Button
                    onClick={handleSend}
                    disabled={disabled || !message.trim()}
                    variant="primary"
                    size="icon"
                    className="flex-shrink-0"
                >
                    <PaperAirplaneIcon className="w-5 h-5" />
                </Button>
            </div>

            {/* Helper Text */}
            <p className="text-xs text-neutral-400 mt-2 text-center">
                Press Enter to send, Shift+Enter for new line
            </p>
        </div>
    );
}

export default ChatInput;