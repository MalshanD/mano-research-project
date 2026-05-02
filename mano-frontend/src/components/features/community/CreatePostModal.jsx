import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Modal, Button, Textarea, Avatar } from '../../common';
import { useAuth } from '../../../contexts/AuthContext';

const postTypes = [
    { id: 'reflect',    label: '💭 Reflection', description: 'Share your thoughts' },
    { id: 'milestone',  label: '🎉 Milestone',  description: 'Celebrate a win' },
    { id: 'tip',        label: '💡 Tip',         description: 'Share helpful advice' },
    { id: 'discussion', label: '💬 Discussion',  description: 'Start a conversation' },
    { id: 'support',    label: '🤗 Support',     description: 'Offer encouragement' },
];

function CreatePostModal({
                             isOpen,
                             onClose,
                             onSubmit,
                             isSubmitting = false,
                         }) {
    const { user } = useAuth();
    const [content, setContent] = useState('');
    const [selectedType, setSelectedType] = useState('reflect');

    const handleSubmit = async () => {
        if (!content.trim()) return;
        await onSubmit(content, selectedType);
        setContent('');
        setSelectedType('reflect');
        onClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Create Post"
            size="lg"
            footer={
                <div className="flex justify-end gap-3">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        variant="primary"
                        onClick={handleSubmit}
                        disabled={!content.trim()}
                        loading={isSubmitting}
                    >
                        Post
                    </Button>
                </div>
            }
        >
            <div className="space-y-4">
                {/* User Info */}
                <div className="flex items-center gap-3">
                    <Avatar
                        src={user?.avatar}
                        firstName={user?.firstName}
                        lastName={user?.lastName}
                        size="md"
                    />
                    <div>
                        <p className="font-medium text-neutral-900">
                            {user?.firstName} {user?.lastName}
                        </p>
                        <p className="text-sm text-neutral-500">Posting to your community</p>
                    </div>
                </div>

                {/* Post Type Selection */}
                <div>
                    <p className="text-sm font-medium text-neutral-700 mb-2">Post Type</p>
                    <div className="flex flex-wrap gap-2">
                        {postTypes.map((type) => (
                            <button
                                key={type.id}
                                onClick={() => setSelectedType(type.id)}
                                className={cn(
                                    'px-3 py-2 rounded-xl text-sm font-medium transition-all',
                                    selectedType === type.id
                                        ? 'bg-primary-100 text-primary-700 ring-2 ring-primary-500'
                                        : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                                )}
                            >
                                {type.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="What's on your mind? Share your thoughts, experiences, or words of encouragement..."
                    rows={5}
                    maxLength={1000}
                />

                {/* Character Count */}
                <div className="text-right">
          <span className={cn('text-sm', content.length > 900 ? 'text-warning-600' : 'text-neutral-400')}>
            {content.length}/1000
          </span>
                </div>

                {/* Guidelines Reminder */}
                <div className="p-3 bg-primary-50 rounded-xl">
                    <p className="text-sm text-primary-700">
                        💙 Remember: Be kind, supportive, and respect others' privacy.
                        This is a safe space for everyone.
                    </p>
                </div>
            </div>
        </Modal>
    );
}

export default CreatePostModal;