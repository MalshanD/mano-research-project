import { useState } from 'react';
import { XMarkIcon, PhoneIcon } from '@heroicons/react/24/outline';
import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import CrisisModal from './CrisisModal';

function EmergencyBanner({ show = false, onDismiss, className }) {
    const [showModal, setShowModal] = useState(false);

    if (!show) return null;

    return (
        <>
            <div
                className={cn(
                    'bg-crisis-600 text-white px-4 py-3 animate-fade-in-down',
                    className
                )}
            >
                <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center animate-pulse">
                            <PhoneIcon className="w-4 h-4" />
                        </div>
                        <div>
                            <p className="font-medium">Need immediate support?</p>
                            <p className="text-sm text-crisis-100">
                                Crisis resources are available 24/7. You're not alone.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setShowModal(true)}
                            className="bg-white text-crisis-700 hover:bg-crisis-50"
                        >
                            Get Help Now
                        </Button>
                        {onDismiss && (
                            <button
                                onClick={onDismiss}
                                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <CrisisModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}

export default EmergencyBanner;