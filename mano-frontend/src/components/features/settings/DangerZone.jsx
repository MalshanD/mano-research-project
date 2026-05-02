import { useState } from 'react';
import { cn } from '../../../utils/helpers';
import { Card, Button, Input, Modal, Alert } from '../../common';
import {
    ExclamationTriangleIcon,
    TrashIcon,
    ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';

function DangerZone({
                        onExportData,
                        onDeleteAccount,
                        isExporting = false,
                        isDeleting = false,
                    }) {
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState('');
    const [password, setPassword] = useState('');

    const handleExportData = async () => {
        await onExportData();
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirmation !== 'DELETE') return;
        await onDeleteAccount(password);
        setShowDeleteModal(false);
    };

    return (
        <Card className="border-crisis-200">
            <div className="flex items-start gap-4 mb-6">
                <div className="w-10 h-10 rounded-xl bg-crisis-50 flex items-center justify-center flex-shrink-0">
                    <ExclamationTriangleIcon className="w-5 h-5 text-crisis-600" />
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-crisis-900">Danger Zone</h3>
                    <p className="text-sm text-neutral-500 mt-1">
                        Irreversible and destructive actions
                    </p>
                </div>
            </div>

            <div className="space-y-4">
                {/* Export Data */}
                <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-xl">
                    <div>
                        <p className="font-medium text-neutral-900">Export Your Data</p>
                        <p className="text-sm text-neutral-500 mt-0.5">
                            Download a copy of all your data
                        </p>
                    </div>
                    <Button
                        variant="outline"
                        onClick={handleExportData}
                        loading={isExporting}
                        leftIcon={<ArrowDownTrayIcon className="w-4 h-4" />}
                    >
                        Export
                    </Button>
                </div>

                {/* Delete Account */}
                <div className="flex items-center justify-between p-4 bg-crisis-50 rounded-xl border border-crisis-200">
                    <div>
                        <p className="font-medium text-crisis-900">Delete Account</p>
                        <p className="text-sm text-crisis-700 mt-0.5">
                            Permanently delete your account and all data
                        </p>
                    </div>
                    <Button
                        variant="danger"
                        onClick={() => setShowDeleteModal(true)}
                        leftIcon={<TrashIcon className="w-4 h-4" />}
                    >
                        Delete
                    </Button>
                </div>
            </div>

            {/* Delete Account Modal */}
            <Modal
                isOpen={showDeleteModal}
                onClose={() => setShowDeleteModal(false)}
                title="Delete Account"
                size="md"
            >
                <div className="space-y-4">
                    <Alert variant="danger">
                        <div className="flex items-start gap-3">
                            <ExclamationTriangleIcon className="w-5 h-5 text-crisis-600 flex-shrink-0" />
                            <div>
                                <p className="font-medium text-crisis-900">This action cannot be undone</p>
                                <p className="text-sm text-crisis-700 mt-1">
                                    Deleting your account will permanently remove all your data, including:
                                </p>
                                <ul className="text-sm text-crisis-700 mt-2 list-disc list-inside">
                                    <li>Your profile and settings</li>
                                    <li>All chat history with Manō</li>
                                    <li>Assessment results and predictions</li>
                                    <li>Activity history and progress</li>
                                    <li>Community connections and messages</li>
                                </ul>
                            </div>
                        </div>
                    </Alert>

                    <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Type <span className="font-bold">DELETE</span> to confirm
                        </label>
                        <Input
                            value={deleteConfirmation}
                            onChange={(e) => setDeleteConfirmation(e.target.value)}
                            placeholder="DELETE"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Enter your password
                        </label>
                        <Input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Your password"
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <Button
                            variant="ghost"
                            onClick={() => setShowDeleteModal(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            onClick={handleDeleteAccount}
                            disabled={deleteConfirmation !== 'DELETE' || !password}
                            loading={isDeleting}
                        >
                            Delete My Account
                        </Button>
                    </div>
                </div>
            </Modal>
        </Card>
    );
}

export default DangerZone;