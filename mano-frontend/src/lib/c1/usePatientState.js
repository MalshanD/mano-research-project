/**
 * usePatientState — single shared hook for fetching the live patient
 * state used by every Component-1 page bundle.
 *
 * Replaces the duplicated `buildPatientState` + hardcoded fallback
 * pattern that existed in 5 legacy synthetic pages and was carried
 * (badly) into the new C1 pages. Now the shape is built ONCE,
 * sourced exclusively from the backend, and the empty/missing states
 * are first-class UI signals — never silent mocks.
 *
 * Returned status modes:
 *   `loading`        — request in flight
 *   `no_patient`     — user has not created a patient profile yet
 *   `incomplete`     — patient exists but lacks the 7-day vitals
 *                      window the bundle endpoints require
 *   `error`          — backend rejected; carries `error` string
 *   `ready`          — `patientState` is a fully validated payload
 */

import { useEffect, useState, useCallback } from 'react';
import { getPatient } from '../../api/client';
import { usePatient } from '../../contexts/PatientContext';

const CHANNELS = ['sleep_hours', 'sleep_quality', 'heart_rate', 'stress_level'];

/** Build the canonical patient_state payload from a backend patient row.
 *  Returns null if the row is missing the inputs the model needs. */
export function shapePatientState(patient) {
    if (!patient) return null;
    if (!Array.isArray(patient.latest_vitals) || patient.latest_vitals.length < 7) {
        return null;
    }
    const dynamic_history = patient.latest_vitals.slice(-7).map((v) => ({
        sleep_hours: Number(v.sleep_hours),
        sleep_quality: Number(v.sleep_quality),
        heart_rate: Number(v.heart_rate),
        stress_level: Number(v.stress_level),
    }));
    // Defensive: every value must be finite + in range. If not, the
    // state isn't usable.
    for (const day of dynamic_history) {
        for (const ch of CHANNELS) {
            if (!Number.isFinite(day[ch])) return null;
        }
    }
    const static_features =
        Array.isArray(patient.static_features) && patient.static_features.length === 20
            ? patient.static_features.map(Number)
            : null;
    if (!static_features) return null;

    return { static_data: { features: static_features }, dynamic_history };
}

export function usePatientState() {
    const { patientId, patientName, isChecking, needsOnboarding } = usePatient();
    const [state, setState] = useState({
        status: 'loading',
        patientState: null,
        patient: null,
        error: null,
    });

    const refresh = useCallback(async () => {
        if (isChecking) {
            setState({ status: 'loading', patientState: null, patient: null, error: null });
            return;
        }
        if (needsOnboarding || !patientId) {
            setState({ status: 'no_patient', patientState: null, patient: null, error: null });
            return;
        }
        setState((s) => ({ ...s, status: 'loading' }));
        const { data, error } = await getPatient(patientId);
        if (error) {
            setState({ status: 'error', patientState: null, patient: null, error });
            return;
        }
        const shaped = shapePatientState(data);
        if (!shaped) {
            setState({ status: 'incomplete', patientState: null, patient: data, error: null });
            return;
        }
        setState({ status: 'ready', patientState: shaped, patient: data, error: null });
    }, [patientId, needsOnboarding, isChecking]);

    useEffect(() => { refresh(); }, [refresh]);

    return {
        ...state,
        patientId,
        patientName,
        refresh,
    };
}
