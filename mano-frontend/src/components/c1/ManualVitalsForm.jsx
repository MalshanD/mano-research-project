import { useState } from 'react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import { updatePatient } from '../../api/client';
import { usePatientState } from '../../lib/c1/usePatientState';

export default function ManualVitalsForm({ isOpen, onClose }) {
    const { patientId, patientState, refresh } = usePatientState();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Initialize with existing dynamic history or defaults
    const [vitals, setVitals] = useState(() => {
        if (patientState?.dynamic_history?.length === 7) {
            return [...patientState.dynamic_history];
        }
        // Default placeholder for 7 days
        return Array(7).fill({
            sleep_hours: 7.0,
            sleep_quality: 0.8,
            heart_rate: 72,
            stress_level: 0.3
        });
    });

    const handleChange = (index, field, value) => {
        const numValue = parseFloat(value) || 0;
        setVitals(prev => {
            const next = [...prev];
            next[index] = { ...next[index], [field]: numValue };
            return next;
        });
    };

    const handleSave = async () => {
        if (!patientId) return;
        setLoading(true);
        setError(null);
        
        // Ensure values are clamped to the schema constraints before sending
        const payload = vitals.map(v => ({
            sleep_hours: Math.max(0, Math.min(24, v.sleep_hours)),
            sleep_quality: Math.max(0, Math.min(1, v.sleep_quality)),
            heart_rate: Math.max(40, Math.min(200, v.heart_rate)),
            stress_level: Math.max(0, Math.min(1, v.stress_level)),
        }));

        const { error: apiError } = await updatePatient(patientId, { latest_vitals: payload });
        setLoading(false);

        if (apiError) {
            setError(apiError);
        } else {
            refresh(); // Triggers usePatientState to refetch
            onClose(); // Close the modal
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Log Weekly Vitals"
            description="Manually record your last 7 days of wearable data."
            size="lg"
            footer={
                <>
                    <Button variant="ghost" onClick={onClose} disabled={loading}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSave} loading={loading}>
                        Save Vitals
                    </Button>
                </>
            }
        >
            {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm">
                    {error}
                </div>
            )}
            
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-slate-500 uppercase bg-slate-50 dark:bg-slate-800">
                        <tr>
                            <th className="px-4 py-3">Day</th>
                            <th className="px-4 py-3">Sleep (hrs)</th>
                            <th className="px-4 py-3">Quality (0-1)</th>
                            <th className="px-4 py-3">Heart Rate</th>
                            <th className="px-4 py-3">Stress (0-1)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {vitals.map((day, i) => (
                            <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                                <td className="px-4 py-2 font-medium text-slate-900 dark:text-slate-100">
                                    {i === 6 ? 'Today' : `Day ${i + 1}`}
                                </td>
                                <td className="px-4 py-2">
                                    <input
                                        type="number"
                                        min="0" max="24" step="0.5"
                                        value={day.sleep_hours}
                                        onChange={(e) => handleChange(i, 'sleep_hours', e.target.value)}
                                        className="w-20 rounded-md border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 sm:text-sm px-2 py-1"
                                    />
                                </td>
                                <td className="px-4 py-2">
                                    <input
                                        type="number"
                                        min="0" max="1" step="0.1"
                                        value={day.sleep_quality}
                                        onChange={(e) => handleChange(i, 'sleep_quality', e.target.value)}
                                        className="w-20 rounded-md border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 sm:text-sm px-2 py-1"
                                    />
                                </td>
                                <td className="px-4 py-2">
                                    <input
                                        type="number"
                                        min="40" max="200" step="1"
                                        value={day.heart_rate}
                                        onChange={(e) => handleChange(i, 'heart_rate', e.target.value)}
                                        className="w-20 rounded-md border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 sm:text-sm px-2 py-1"
                                    />
                                </td>
                                <td className="px-4 py-2">
                                    <input
                                        type="number"
                                        min="0" max="1" step="0.1"
                                        value={day.stress_level}
                                        onChange={(e) => handleChange(i, 'stress_level', e.target.value)}
                                        className="w-20 rounded-md border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 sm:text-sm px-2 py-1"
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <p className="mt-4 text-xs text-slate-500">
                Note: Updating these values will immediately recalculate your AI predictions.
            </p>
        </Modal>
    );
}
