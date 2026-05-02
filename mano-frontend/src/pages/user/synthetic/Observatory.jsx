import { motion } from 'framer-motion';
import { Activity, Users, FlaskConical, ArrowUpRight, ArrowDownRight, Minus, Cpu, Brain, Zap, Heart } from 'lucide-react';
import { useApi } from '../../../hooks/useApi';
import { getHealth, listPatients } from '../../../api/client';
import { Link } from 'react-router-dom';

const fadeUp = {
    hidden: { opacity: 0, y: 12 },
    visible: (i) => ({
        opacity: 1,
        y: 0,
        transition: { delay: i * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }
    })
};

function ModelStatusCard({ name, icon: Icon, status, index }) {
    const isOk = status === 'loaded';
    return (
        <motion.div
            className="glass-card"
            custom={index}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
        >
            <div className="flex items-center justify-between mb-md">
                <div className="flex items-center gap-sm">
                    <Icon size={18} className={isOk ? 'text-safe' : 'text-risk'} />
                    <span className="data-label">{name}</span>
                </div>
                <span className={`pulse-dot ${isOk ? '' : 'degraded'}`} />
            </div>
            <div className={`data-value ${isOk ? 'text-safe' : 'text-risk'}`}>
                {isOk ? 'Online' : 'Offline'}
            </div>
        </motion.div>
    );
}

function PatientPreviewRow({ patient }) {
    const riskColors = { Low: 'text-success', Medium: 'text-caution', High: 'text-risk' };
    const riskBadge = { Low: 'badge-safe', Medium: 'badge-caution', High: 'badge-risk' };

    return (
        <tr>
            <td>
                <Link to={`/predictions/patients/${patient.id}`} className="flex items-center gap-sm" style={{ textDecoration: 'none', color: 'var(--text-primary)' }}>
                    <div style={{
                        width: 32, height: 32, borderRadius: 'var(--radius-full)',
                        background: 'var(--predict-dim)', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: 'var(--text-xs)', color: 'var(--predict)',
                        fontWeight: 600
                    }}>
                        {(patient.name || 'P')[0].toUpperCase()}
                    </div>
                    <span style={{ fontWeight: 500 }}>{patient.name || `Patient ${patient.id.slice(0, 8)}`}</span>
                </Link>
            </td>
            <td>
                <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {patient.age || '—'}
                </span>
            </td>
            <td>
                <span className={`badge ${riskBadge[patient.cached_risk_level] || 'badge-predict'}`}>
                    {patient.cached_risk_level || 'Unknown'}
                </span>
            </td>
            <td>
                <span style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {patient.created_at ? new Date(patient.created_at).toLocaleDateString() : '—'}
                </span>
            </td>
        </tr>
    );
}

export default function Observatory() {
    const { data: health, loading: healthLoading } = useApi(getHealth, { key: 'health' });
    const { data: patients, loading: patientsLoading } = useApi(listPatients, { key: 'patients' });

    const models = health ? [
        { name: 'LSTM Risk Predictor', icon: Brain, status: health.models?.risk_model },
        { name: 'Seq2Seq Simulator', icon: Zap, status: health.models?.intervention_model },
        { name: 'GPU Acceleration', icon: Cpu, status: health.gpu?.available ? 'loaded' : 'unavailable' },
    ] : [];

    return (
        <div className="fade-in">
            <div className="page-header">
                <h1 className="page-title">Observatory</h1>
                <p className="page-subtitle">System state and patient overview — your cognitive anchor point</p>
            </div>

            {/* System Intelligence Status */}
            <section className="mb-lg">
                <div className="flex items-center gap-sm mb-md">
                    <Activity size={16} className="text-safe" />
                    <span className="data-label">Intelligence Core</span>
                </div>
                <div className="grid-3">
                    {healthLoading ? (
                        <>
                            <div className="shimmer" style={{ height: 100 }} />
                            <div className="shimmer" style={{ height: 100 }} />
                            <div className="shimmer" style={{ height: 100 }} />
                        </>
                    ) : (
                        models.map((model, i) => (
                            <ModelStatusCard key={model.name} {...model} index={i} />
                        ))
                    )}
                </div>
            </section>

            {/* Quick Actions */}
            <section className="mb-lg">
                <div className="flex items-center gap-sm mb-md">
                    <FlaskConical size={16} className="text-predict" />
                    <span className="data-label">Quick Actions</span>
                </div>
                <div className="flex gap-md">
                    <Link to="/predictions/patients" className="btn btn-primary" style={{ textDecoration: 'none' }}>
                        <Users size={16} />
                        View Patients
                    </Link>
                    <Link to="/predictions/simulate" className="btn btn-ghost" style={{ textDecoration: 'none' }}>
                        <FlaskConical size={16} />
                        Open Simulation Lab
                    </Link>
                </div>
            </section>

            {/* Recent Patients */}
            <section>
                <div className="flex items-center justify-between mb-md">
                    <div className="flex items-center gap-sm">
                        <Users size={16} className="text-safe" />
                        <span className="data-label">Recent Patients</span>
                    </div>
                    <Link to="/predictions/patients" className="btn btn-ghost btn-sm" style={{ textDecoration: 'none' }}>
                        View All
                        <ArrowUpRight size={14} />
                    </Link>
                </div>
                <div className="glass-card no-hover">
                    {patientsLoading ? (
                        <div className="flex flex-col gap-md">
                            <div className="shimmer" style={{ height: 40 }} />
                            <div className="shimmer" style={{ height: 40 }} />
                            <div className="shimmer" style={{ height: 40 }} />
                        </div>
                    ) : patients?.patients?.length > 0 ? (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Patient</th>
                                    <th>Age</th>
                                    <th>Risk Level</th>
                                    <th>Created</th>
                                </tr>
                            </thead>
                            <tbody>
                                {patients.patients.slice(0, 5).map(p => (
                                    <PatientPreviewRow key={p.id} patient={p} />
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div style={{
                            textAlign: 'center',
                            padding: 'var(--space-2xl)',
                            color: 'var(--text-muted)'
                        }}>
                            <Heart size={32} style={{ marginBottom: 'var(--space-sm)', opacity: 0.3 }} />
                            <p>No patients yet. Create one to begin simulation.</p>
                            <Link to="/predictions/patients" className="btn btn-primary btn-sm mt-md" style={{ textDecoration: 'none' }}>
                                <Users size={14} />
                                Add Patient
                            </Link>
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
}
