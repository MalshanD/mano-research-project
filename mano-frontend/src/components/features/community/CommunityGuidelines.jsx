import { useState, useEffect } from 'react';
import { cn } from '../../../utils/helpers';
import { Modal, Button, Checkbox } from '../../common';
import communityService from '../../../services/communityService';
import {
    ShieldCheckIcon,
    HeartIcon,
    LockClosedIcon,
    ExclamationTriangleIcon,
    SparklesIcon,
} from '@heroicons/react/24/outline';

const guidelineIcons = [
    HeartIcon,
    LockClosedIcon,
    ExclamationTriangleIcon,
    ShieldCheckIcon,
    SparklesIcon,
];

function CommunityGuidelines({
                                 isOpen,
                                 onClose,
                                 onAccept,
                                 requireAccept = false,
                             }) {
    const [guidelines, setGuidelines] = useState([]);
    const [accepted, setAccepted] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            loadGuidelines();
        }
    }, [isOpen]);

    const loadGuidelines = async () => {
        try {
            const data = await communityService.getGuidelines();
            setGuidelines(data.guidelines);
        } catch (err) {
            console.error('Failed to load guidelines:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAccept = () => {
        onAccept?.();
        onClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={requireAccept ? undefined : onClose}
            title="Community Guidelines"
            size="lg"
            footer={
                requireAccept ? (
                    <div className="space-y-4">
                        <Checkbox
                            label="I have read and agree to follow the community guidelines"
                            checked={accepted}
                            onChange={(e) => setAccepted(e.target.checked)}
                        />
                        <div className="flex justify-end gap-3">
                            <Button variant="ghost" onClick={onClose}>
                                Maybe Later
                            </Button>
                            <Button
                                variant="primary"
                                onClick={handleAccept}
                                disabled={!accepted}
                            >
                                Accept & Continue
                            </Button>
                        </div>
                    </div>
                ) : (
                    <Button variant="primary" onClick={onClose} fullWidth>
                        Got it
                    </Button>
                )
            }
        >
            <div className="space-y-4">
                {/* Header */}
                <div className="text-center pb-4 border-b border-neutral-100">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-100 flex items-center justify-center">
                        <ShieldCheckIcon className="w-8 h-8 text-primary-600" />
                    </div>
                    <p className="text-neutral-600">
                        Our community is a safe space for everyone. Please follow these guidelines to help us maintain a supportive environment.
                    </p>
                </div>

                {/* Guidelines List */}
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="animate-pulse flex items-start gap-4">
                                <div className="w-10 h-10 bg-neutral-200 rounded-lg" />
                                <div className="flex-1">
                                    <div className="h-4 bg-neutral-200 rounded w-1/3 mb-2" />
                                    <div className="h-3 bg-neutral-200 rounded w-full" />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {guidelines.map((guideline, index) => {
                            const Icon = guidelineIcons[index % guidelineIcons.length];
                            return (
                                <div key={index} className="flex items-start gap-4 p-4 bg-neutral-50 rounded-xl">
                                    <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
                                        <Icon className="w-5 h-5 text-primary-600" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-neutral-900">{guideline.title}</h4>
                                        <p className="text-sm text-neutral-600 mt-1">{guideline.description}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Footer Note */}
                <div className="p-4 bg-warning-50 rounded-xl">
                    <p className="text-sm text-warning-800">
                        <strong>Note:</strong> Violations of these guidelines may result in temporary or permanent removal from the community. If you see content that violates these guidelines, please report it.
                    </p>
                </div>
            </div>
        </Modal>
    );
}

export default CommunityGuidelines;