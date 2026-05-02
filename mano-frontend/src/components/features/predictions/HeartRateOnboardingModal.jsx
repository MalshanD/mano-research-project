import { useState } from 'react';
import Modal from '../../common/Modal';
import Button from '../../common/Button';
import { HeartIcon } from '@heroicons/react/24/outline';

function HeartRateOnboardingModal({ isOpen, onSubmit, isLoading }) {
    const [heartRate, setHeartRate] = useState(72);
    const [error, setError] = useState('');

    const validate = (val) => {
        if (val < 40 || val > 200) return 'Please enter a value between 40 and 200 BPM.';
        return '';
    };

    const handleChange = (e) => {
        const val = Number(e.target.value);
        setHeartRate(val);
        setError(validate(val));
    };

    const handleContinue = () => {
        const err = validate(heartRate);
        if (err) { setError(err); return; }
        onSubmit(heartRate);
    };

    const handleSkip = () => {
        onSubmit(72);
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={() => {}}          /* prevent outside-click dismiss */
            showCloseButton={false}
            closeOnOverlayClick={false}
            title=""
            size="sm"
        >
            <div className="text-center px-2 pb-2">
                {/* Icon */}
                <div className="mx-auto w-14 h-14 rounded-full bg-primary-50 flex items-center justify-center mb-4">
                    <HeartIcon className="w-7 h-7 text-primary-600" />
                </div>

                {/* Heading */}
                <h2 className="text-xl font-semibold text-neutral-900 mb-1">
                    Setting up your AI Profile
                </h2>
                <p className="text-sm text-neutral-500 mb-6">
                    One quick question to personalise your predictions.
                </p>

                {/* Input */}
                <label className="block text-left text-sm font-medium text-neutral-700 mb-1">
                    What is your resting heart rate?
                </label>
                <div className="flex items-center gap-2 mb-1">
                    <input
                        type="number"
                        min={40}
                        max={200}
                        value={heartRate}
                        onChange={handleChange}
                        className="flex-1 border border-neutral-300 rounded-xl px-4 py-2.5 text-neutral-900 text-sm focus:outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition"
                    />
                    <span className="text-sm text-neutral-500 flex-shrink-0">BPM</span>
                </div>
                <p className="text-xs text-neutral-400 text-left mb-1">
                    Normal resting range: 60–100 BPM
                </p>
                {error && (
                    <p className="text-xs text-crisis-600 text-left mb-2">{error}</p>
                )}

                {/* Actions */}
                <div className="flex gap-3 mt-5">
                    <Button
                        variant="ghost"
                        size="sm"
                        fullWidth
                        onClick={handleSkip}
                        disabled={isLoading}
                    >
                        Skip — use default
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        fullWidth
                        onClick={handleContinue}
                        disabled={isLoading || !!error}
                        loading={isLoading}
                    >
                        Continue →
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

export default HeartRateOnboardingModal;
