import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getPatientByUser, createPatientFromUser } from '../api/client';
import { useAuth } from './AuthContext';

const PatientContext = createContext(null);

const patientKey = (userId) => `mano_patient_id_${userId}`;

export function PatientProvider({ children }) {
    const { user } = useAuth();
    const [patientId, setPatientId] = useState(() =>
        user?.id ? localStorage.getItem(patientKey(user.id)) : null
    );
    const [patientName, setPatientName] = useState(null);
    const [isChecking, setIsChecking] = useState(false);
    const [needsOnboarding, setNeedsOnboarding] = useState(false);

    // Check for existing patient whenever user changes
    useEffect(() => {
        if (!user?.id) return;
        // Already have one stored
        if (patientId) { setNeedsOnboarding(false); return; }

        setIsChecking(true);
        getPatientByUser(user.id).then(({ data, error }) => {
            if (data?.id) {
                localStorage.setItem(patientKey(user.id), data.id);
                setPatientId(data.id);
                setPatientName(data.name);
                setNeedsOnboarding(false);
            } else {
                // 404 or error — user needs onboarding
                setNeedsOnboarding(true);
            }
            setIsChecking(false);
        });
    }, [user?.id, patientId]);

    const createPatient = useCallback(async (heartRate) => {
        if (!user?.id) return null;
        const { data, error } = await createPatientFromUser(user.id, heartRate);
        if (error || !data?.id) throw new Error(error || 'Failed to create patient profile');
        localStorage.setItem(patientKey(user.id), data.id);
        setPatientId(data.id);
        setPatientName(data.name);
        setNeedsOnboarding(false);
        return data.id;
    }, [user?.id]);

    const clearPatient = useCallback(() => {
        if (user?.id) localStorage.removeItem(patientKey(user.id));
        setPatientId(null);
        setPatientName(null);
        setNeedsOnboarding(true);
    }, [user?.id]);

    return (
        <PatientContext.Provider value={{
            patientId,
            patientName,
            isChecking,
            needsOnboarding,
            createPatient,
            clearPatient,
        }}>
            {children}
        </PatientContext.Provider>
    );
}

export function usePatient() {
    const ctx = useContext(PatientContext);
    if (!ctx) throw new Error('usePatient must be used inside <PatientProvider>');
    return ctx;
}
