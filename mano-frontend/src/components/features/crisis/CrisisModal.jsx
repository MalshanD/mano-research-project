import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
    XMarkIcon,
    PhoneIcon,
    ChatBubbleLeftRightIcon,
    HeartIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Button } from '../../common';
import { EMERGENCY_RESOURCES } from '../../../config/constants';

function CrisisModal({ isOpen, onClose }) {
    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-[100]" onClose={onClose}>
                {/* Backdrop */}
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                                {/* Header */}
                                <div className="bg-crisis-600 px-6 py-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                                                <HeartIcon className="w-6 h-6 text-white" />
                                            </div>
                                            <div>
                                                <Dialog.Title className="text-lg font-semibold text-white">
                                                    We're Here For You
                                                </Dialog.Title>
                                                <p className="text-sm text-crisis-100">
                                                    You're not alone
                                                </p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={onClose}
                                            className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                        >
                                            <XMarkIcon className="w-5 h-5" />
                                        </button>
                                    </div>
                                </div>

                                {/* Content */}
                                <div className="p-6">
                                    <p className="text-neutral-600 mb-6">
                                        If you're experiencing a crisis or having thoughts of self-harm, please reach out to one of these resources. They're available 24/7.
                                    </p>

                                    {/* Emergency Resources */}
                                    <div className="space-y-3 mb-6">
                                        {EMERGENCY_RESOURCES.map((resource, index) => (

                                            <a key={index}
                                            href={resource.type === 'call' ? `tel:${resource.phone}` : `sms:${resource.phone}`}
                                            className="flex items-center gap-4 p-4 bg-neutral-50 rounded-xl hover:bg-neutral-100 transition-colors group"
                                            >
                                            <div className="w-12 h-12 rounded-xl bg-crisis-100 flex items-center justify-center group-hover:bg-crisis-200 transition-colors">
                                        {resource.type === 'call' ? (
                                            <PhoneIcon className="w-6 h-6 text-crisis-600" />
                                            ) : (
                                            <ChatBubbleLeftRightIcon className="w-6 h-6 text-crisis-600" />
                                            )}
                                            </div>
                                            <div className="flex-1">
                                            <p className="font-semibold text-neutral-900">
                                        {resource.name}
                                    </p>
                                    <p className="text-sm text-neutral-500">
                                        {resource.description}
                                    </p>
                                </div>
                                <span className="text-lg font-bold text-crisis-600">
                          {resource.phone}
                        </span>
                            </a>
                            ))}
                    </div>

                    {/* Additional Help */}
                    <div className="p-4 bg-primary-50 rounded-xl">
                        <div className="flex items-start gap-3">
                            <ExclamationTriangleIcon className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-primary-900">
                                    You can also talk to us
                                </p>
                                <p className="text-sm text-primary-700 mt-1">
                                    Our AI companion is here to listen and provide support anytime you need it.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
                    <Button variant="ghost" onClick={onClose}>
                        I'm Okay
                    </Button>
                    <Button
                        variant="primary"
                        onClick={() => window.location.href = '/chat'}
                    >
                        Talk to Manō
                    </Button>
                </div>
            </Dialog.Panel>
        </Transition.Child>
</div>
</div>
</Dialog>
</Transition>
);
}

export default CrisisModal;