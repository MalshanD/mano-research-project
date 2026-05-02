import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Plus, Search, Trash2, ArrowUpRight, X } from 'lucide-react';
import { useApi } from '../../../hooks/useApi';
import { listPatients, createPatient, deletePatient } from '../../../api/client';
import { Link } from 'react-router-dom';

const fadeUp = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
    exit: { opacity: 0, y: -8, transition: { duration: 0.2 } }
};

function CreatePatientModal({ onClose, onCreated }) {
    const [form, setForm] = useState({
        name: '', age: '', gender: 'M',
        diagnosis: '', sleep_hours: 7, heart_rate: 72, stress_level: 0.3
    });
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        const result = await createPatient({
            name: form.name,
            age: parseInt(form.age) || null,
            gender: form.gender,
            diagnosis: form.diagnosis || null,
            latest_sleep_hours: parseFloat(form.sleep_hours),
            latest_heart_rate: parseFloat(form.heart_rate),
            latest_stress_level: parseFloat(form.stress_level),
        });
        setSubmitting(false);
        if (!result.error) {
            onCreated();
            onClose();
        }
    };

    return (
        <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
                position: 'fixed', inset: 0, zIndex: 200,
                background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
        >
            <motion.div
                className="glass-card elevated"
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                onClick={e => e.stopPropagation()}
                style={{ width: '100%', maxWidth: 480, padding: 'var(--space-xl)' }}
            >
                <div className="flex items-center justify-between mb-lg">
                    <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>New Patient</h2>
                    <button onClick={onClose} className="btn btn-ghost btn-sm" style={{ padding: 'var(--space-xs)' }}>
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-md">
                    <div>
                        <label className="data-label mb-sm" style={{ display: 'block', marginBottom: 4 }}>Name</label>
                        <input className="input-field" value={form.name}
                            onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required placeholder="Patient name" />
                    </div>
                    <div className="grid-2">
                        <div>
                            <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Age</label>
                            <input className="input-field" type="number" value={form.age}
                                onChange={e => setForm(f => ({ ...f, age: e.target.value }))} placeholder="Age" min={0} max={120} />
                        </div>
                        <div>
                            <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Gender</label>
                            <select className="select-field" value={form.gender}
                                onChange={e => setForm(f => ({ ...f, gender: e.target.value }))}>
                                <option value="M">Male</option>
                                <option value="F">Female</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Diagnosis</label>
                        <input className="input-field" value={form.diagnosis}
                            onChange={e => setForm(f => ({ ...f, diagnosis: e.target.value }))} placeholder="Primary diagnosis (optional)" />
                    </div>

                    <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: 'var(--space-md)', marginTop: 'var(--space-sm)' }}>
                        <span className="data-label">Initial Vitals</span>
                    </div>
                    <div className="grid-3">
                        <div>
                            <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Sleep (hrs)</label>
                            <input className="input-field" type="number" step="0.5" value={form.sleep_hours}
                                onChange={e => setForm(f => ({ ...f, sleep_hours: e.target.value }))} min={0} max={24} />
                        </div>
                        <div>
                            <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Heart Rate</label>
                            <input className="input-field" type="number" value={form.heart_rate}
                                onChange={e => setForm(f => ({ ...f, heart_rate: e.target.value }))} min={40} max={200} />
                        </div>
                        <div>
                            <label className="data-label" style={{ display: 'block', marginBottom: 4 }}>Stress</label>
                            <input className="input-field" type="number" step="0.1" value={form.stress_level}
                                onChange={e => setForm(f => ({ ...f, stress_level: e.target.value }))} min={0} max={1} />
                        </div>
                    </div>

                    <div className="flex justify-between mt-md">
                        <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
                        <button type="submit" className="btn btn-primary" disabled={submitting || !form.name}>
                            {submitting ? 'Creating...' : 'Create Patient'}
                        </button>
                    </div>
                </form>
            </motion.div>
        </motion.div>
    );
}

export default function PatientExplorer() {
    const { data, loading, execute: refetch } = useApi(listPatients, { key: 'patients' });
    const [showCreate, setShowCreate] = useState(false);
    const [search, setSearch] = useState('');
    const [deletingId, setDeletingId] = useState(null);

    const patients = data?.patients || [];
    const filtered = patients.filter(p =>
        (p.name || '').toLowerCase().includes(search.toLowerCase()) ||
        (p.diagnosis || '').toLowerCase().includes(search.toLowerCase())
    );

    const handleDelete = async (id) => {
        setDeletingId(id);
        await deletePatient(id);
        await refetch();
        setDeletingId(null);
    };

    const riskBadge = { Low: 'badge-safe', Medium: 'badge-caution', High: 'badge-risk' };

    return (
        <div className="fade-in">
            <div className="page-header">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="page-title">Patient Explorer</h1>
                        <p className="page-subtitle">Dynamic state objects — not static records</p>
                    </div>
                    <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                        <Plus size={16} />
                        New Patient
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="mb-lg" style={{ maxWidth: 400 }}>
                <div style={{ position: 'relative' }}>
                    <Search size={16} style={{
                        position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                        color: 'var(--text-muted)'
                    }} />
                    <input
                        className="input-field"
                        placeholder="Search patients..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ paddingLeft: 36 }}
                    />
                </div>
            </div>

            {/* Patients Grid */}
            {loading ? (
                <div className="grid-auto">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="shimmer" style={{ height: 160, borderRadius: 'var(--radius-lg)' }} />
                    ))}
                </div>
            ) : filtered.length > 0 ? (
                <div className="grid-auto">
                    <AnimatePresence mode="popLayout">
                        {filtered.map(patient => (
                            <motion.div
                                key={patient.id}
                                className="glass-card"
                                variants={fadeUp}
                                initial="hidden"
                                animate="visible"
                                exit="exit"
                                layout
                                style={{ position: 'relative' }}
                            >
                                {/* Subtle stability glow — pulsing to indicate "alive" */}
                                <div style={{
                                    position: 'absolute', top: 12, right: 12,
                                    width: 8, height: 8, borderRadius: '50%',
                                    background: patient.current_risk_level === 'High' ? 'var(--risk)'
                                        : patient.current_risk_level === 'Medium' ? 'var(--caution)'
                                            : 'var(--success)',
                                    animation: 'pulse-ring 3s ease infinite',
                                    boxShadow: `0 0 8px ${patient.current_risk_level === 'High' ? 'var(--risk-dim)'
                                            : patient.current_risk_level === 'Medium' ? 'var(--caution-dim)'
                                                : 'var(--safe-dim)'
                                        }`
                                }} />

                                <div className="flex items-center gap-md mb-md">
                                    <div style={{
                                        width: 40, height: 40, borderRadius: 'var(--radius-full)',
                                        background: 'var(--predict-dim)', display: 'flex', alignItems: 'center',
                                        justifyContent: 'center', fontWeight: 600, color: 'var(--predict)'
                                    }}>
                                        {(patient.name || 'P')[0].toUpperCase()}
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 600 }}>{patient.name || `ID: ${patient.id.slice(0, 8)}`}</div>
                                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                            {patient.age ? `${patient.age}y` : '—'} · {patient.gender || '—'}
                                        </div>
                                    </div>
                                </div>

                                {patient.diagnosis && (
                                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
                                        {patient.diagnosis}
                                    </div>
                                )}

                                <div className="flex items-center justify-between mt-md">
                                    <span className={`badge ${riskBadge[patient.current_risk_level] || 'badge-predict'}`}>
                                        {patient.current_risk_level || 'Unscored'}
                                    </span>
                                    <div className="flex gap-xs">
                                        <button
                                            className="btn btn-ghost btn-sm"
                                            onClick={() => handleDelete(patient.id)}
                                            disabled={deletingId === patient.id}
                                            style={{ padding: 'var(--space-xs)', color: 'var(--text-muted)' }}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                        <Link to={`/predictions/patients/${patient.id}`} className="btn btn-ghost btn-sm" style={{ textDecoration: 'none' }}>
                                            <ArrowUpRight size={14} />
                                        </Link>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            ) : (
                <div className="glass-card no-hover" style={{ textAlign: 'center', padding: 'var(--space-3xl)' }}>
                    <Users size={36} style={{ color: 'var(--text-muted)', opacity: 0.3, marginBottom: 'var(--space-md)' }} />
                    <p className="text-muted">
                        {search ? 'No patients match your search.' : 'No patients registered. Create one to begin.'}
                    </p>
                </div>
            )}

            {/* Create Patient Modal */}
            <AnimatePresence>
                {showCreate && (
                    <CreatePatientModal onClose={() => setShowCreate(false)} onCreated={refetch} />
                )}
            </AnimatePresence>
        </div>
    );
}
