import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FlaskConical, Calendar, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { useApi } from '../../../hooks/useApi';
import { getPatient } from '../../../api/client';

export default function PatientProfile() {
    const { id } = useParams();
    const { data: patient, loading } = useApi(getPatient, { args: [id], key: id });

    if (loading) {
        return (
            <div className="fade-in">
                <div className="shimmer" style={{ height: 40, width: 200, marginBottom: 'var(--space-lg)' }} />
                <div className="shimmer" style={{ height: 200, marginBottom: 'var(--space-lg)' }} />
                <div className="shimmer" style={{ height: 300 }} />
            </div>
        );
    }

    if (!patient) {
        return (
            <div className="fade-in">
                <p className="text-muted">Patient not found.</p>
                <Link to="/predictions/patients" className="btn btn-ghost mt-md" style={{ textDecoration: 'none' }}>
                    <ArrowLeft size={16} /> Back
                </Link>
            </div>
        );
    }

    const riskBadge = { Low: 'badge-safe', Medium: 'badge-caution', High: 'badge-risk' };
    const riskColor = { Low: 'var(--success)', Medium: 'var(--caution)', High: 'var(--risk)' };
    const riskPercent = { Low: 20, Medium: 50, High: 80 };

    return (
        <div className="fade-in">
            {/* Header */}
            <div className="flex items-center gap-md mb-lg">
                <Link to="/predictions/patients" className="btn btn-ghost btn-sm" style={{ textDecoration: 'none', padding: 'var(--space-xs)' }}>
                    <ArrowLeft size={18} />
                </Link>
                <div>
                    <h1 className="page-title">{patient.name || `Patient ${patient.id.slice(0, 8)}`}</h1>
                    <p className="page-subtitle">
                        {patient.age ? `${patient.age}y` : ''} {patient.gender ? `· ${patient.gender}` : ''}
                        {patient.diagnosis ? ` · ${patient.diagnosis}` : ''}
                    </p>
                </div>
            </div>

            <div className="grid-2 mb-lg">
                {/* Reality Layer — Current State */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                >
                    <div className="data-label mb-md">Current State — Reality Layer</div>

                    {/* Risk Field */}
                    <div className="mb-lg">
                        <div className="flex items-center justify-between mb-sm">
                            <span className="data-label">Risk Level</span>
                            <span className={`badge ${riskBadge[patient.cached_risk_level] || 'badge-predict'}`}>
                                {patient.cached_risk_level || 'Unscored'}
                            </span>
                        </div>
                        <div className="risk-field">
                            <div
                                className="risk-field-indicator"
                                style={{ left: `${riskPercent[patient.cached_risk_level] || 50}%` }}
                            />
                        </div>
                    </div>

                    {/* Vitals */}
                    <div className="grid-3 mt-lg">
                        <div>
                            <div className="data-label">Sleep</div>
                            <div className="data-value">{patient.latest_sleep_hours ?? '—'}<span className="data-unit">hrs</span></div>
                        </div>
                        <div>
                            <div className="data-label">Heart Rate</div>
                            <div className="data-value">{patient.latest_heart_rate ?? '—'}<span className="data-unit">bpm</span></div>
                        </div>
                        <div>
                            <div className="data-label">Stress</div>
                            <div className="data-value">{patient.latest_stress_level != null ? (patient.latest_stress_level * 100).toFixed(0) : '—'}<span className="data-unit">%</span></div>
                        </div>
                    </div>
                </motion.div>

                {/* Quick Actions */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
                >
                    <div className="data-label mb-md">Actions</div>
                    <div className="flex flex-col gap-md">
                        <Link to="/predictions/simulate" className="btn btn-primary w-full" style={{ textDecoration: 'none', justifyContent: 'center' }}>
                            <FlaskConical size={16} />
                            Run Simulation
                        </Link>
                        <Link to="/predictions/compare" className="btn btn-ghost w-full" style={{ textDecoration: 'none', justifyContent: 'center' }}>
                            Compare All Interventions
                        </Link>
                        <Link to="/predictions/prescribe" className="btn btn-ghost w-full" style={{ textDecoration: 'none', justifyContent: 'center' }}>
                            Get AI Prescription
                        </Link>
                    </div>

                    <div style={{ borderTop: '1px solid var(--glass-border)', marginTop: 'var(--space-lg)', paddingTop: 'var(--space-md)' }}>
                        <div className="data-label mb-sm">Details</div>
                        <div className="flex flex-col gap-xs" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                            <div className="flex justify-between">
                                <span>ID</span>
                                <span style={{ fontFamily: 'var(--font-data)' }}>{patient.id.slice(0, 12)}…</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Created</span>
                                <span>{patient.created_at ? new Date(patient.created_at).toLocaleString() : '—'}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Updated</span>
                                <span>{patient.updated_at ? new Date(patient.updated_at).toLocaleString() : '—'}</span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Simulation History */}
            <motion.div
                className="glass-card no-hover"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            >
                <div className="flex items-center gap-sm mb-md">
                    <Calendar size={16} className="text-predict" />
                    <span className="data-label">Simulation History — Temporal Layer</span>
                </div>

                {patient.simulation_history?.length > 0 ? (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Intervention</th>
                                <th>Intensity</th>
                                <th>Before</th>
                                <th>After</th>
                                <th>Change</th>
                            </tr>
                        </thead>
                        <tbody>
                            {patient.simulation_history.map((sim, i) => {
                                const reduction = sim.risk_reduction_score || 0;
                                const TrendIcon = reduction > 0 ? TrendingDown : reduction < 0 ? TrendingUp : Minus;
                                const trendClass = reduction > 0 ? 'text-success' : reduction < 0 ? 'text-risk' : 'text-muted';
                                return (
                                    <tr key={i}>
                                        <td style={{ fontFamily: 'var(--font-data)', fontSize: 'var(--text-xs)' }}>
                                            {sim.created_at ? new Date(sim.created_at).toLocaleString() : '—'}
                                        </td>
                                        <td>{sim.intervention_type || '—'}</td>
                                        <td style={{ fontFamily: 'var(--font-data)' }}>{sim.intensity?.toFixed(1) || '—'}</td>
                                        <td><span className={`badge ${riskBadge[sim.original_risk_level] || 'badge-predict'}`}>{sim.original_risk_level || '—'}</span></td>
                                        <td><span className={`badge ${riskBadge[sim.projected_risk_level] || 'badge-predict'}`}>{sim.projected_risk_level || '—'}</span></td>
                                        <td>
                                            <span className={`velocity-indicator ${reduction > 0 ? 'decreasing' : reduction < 0 ? 'increasing' : 'stable'}`}>
                                                <TrendIcon size={12} />
                                                {Math.abs(reduction * 100).toFixed(1)}%
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                ) : (
                    <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                        No simulations run yet for this patient.
                    </div>
                )}
            </motion.div>
        </div>
    );
}
