import { lazy, Suspense, useState } from 'react';
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import PageContainer from '../../components/layout/PageContainer';
import { cn } from '../../utils/helpers';
import { PatientProvider, usePatient } from '../../contexts/PatientContext';
import HeartRateOnboardingModal from '../../components/features/predictions/HeartRateOnboardingModal';

// Lazy load imported pages
const UserSummary = lazy(() => import('./synthetic/UserSummary'));
const ClinicalReport = lazy(() => import('./synthetic/ClinicalReport'));
const DigitalTwinFactory = lazy(() => import('./synthetic/DigitalTwinFactory'));
const InterventionCompare = lazy(() => import('./synthetic/InterventionCompare'));
const InterventionSequencer = lazy(() => import('./synthetic/InterventionSequencer'));
const NextBestAction = lazy(() => import('./synthetic/NextBestAction'));
const Prescription = lazy(() => import('./synthetic/Prescription'));
const SimulationLab = lazy(() => import('./synthetic/SimulationLab'));
const UncertaintyExplorer = lazy(() => import('./synthetic/UncertaintyExplorer'));
const WhatIfSimulator = lazy(() => import('./synthetic/WhatIfSimulator'));
const XAIExplainer = lazy(() => import('./synthetic/XAIExplainer'));

// Loading component
const PageLoader = () => (
    <div style={{ padding: '64px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
    </div>
);

const navigationLinks = [
    { path: '.', label: 'My Profile', end: true },
    { path: 'simulate', label: 'Simulation Lab' },
    { path: 'compare', label: 'Intervention Compare' },
    { path: 'prescribe', label: 'AI Prescription' },
    { path: 'what-if', label: 'What-If Simulator' },
    { path: 'explain', label: 'XAI Explainer' },
    { path: 'next-action', label: 'Next Best Action' },
    { path: 'sequencer', label: 'Sequencer' },
    { path: 'uncertainty', label: 'Uncertainty' },
    { path: 'report', label: 'Clinical Report' },
    { path: 'twin', label: 'Digital Twin' },
];

// Inner component — has access to PatientContext
function PredictionsContent() {
    const location = useLocation();
    const { needsOnboarding, isChecking, createPatient } = usePatient();
    const [isCreating, setIsCreating] = useState(false);

    const handleOnboardingSubmit = async (heartRate) => {
        setIsCreating(true);
        try {
            await createPatient(heartRate);
        } catch (err) {
            console.error('Failed to create patient profile:', err);
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <PageContainer
            title="Predictions & Insights"
            subtitle="AI-powered discovery and analysis tools"
        >
            <div className="flex flex-col lg:flex-row gap-6">
                {/* Sidebar Nav */}
                <div className="lg:w-64 flex-shrink-0">
                    <div className="sticky top-24">
                        <nav className="space-y-1">
                            {navigationLinks.map((link) => {
const isActive = location.pathname === `/predictions${link.path === '.' ? '' : `/${link.path}`}` || 
                        (link.path === '.' && location.pathname === '/predictions');
                                
                                return (
                                    <NavLink
                                        key={link.path}
                                        to={link.path}
                                        end={link.end}
                                        className={cn(
                                            'w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-left font-medium transition-all',
                                            isActive
                                                ? 'bg-cream text-terracotta shadow-organic'
                                                : 'text-neutral-600 hover:bg-cream/50 hover:text-terracotta-dark'
                                        )}
                                    >
                                        <span className="flex-1">{link.label}</span>
                                    </NavLink>
                                );
                            })}
                        </nav>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <Suspense fallback={<PageLoader />}>
                        <Routes>
                            <Route index element={<UserSummary />} />
                            <Route path="simulate" element={<SimulationLab />} />
                            <Route path="compare" element={<InterventionCompare />} />
                            <Route path="prescribe" element={<Prescription />} />
                            <Route path="what-if" element={<WhatIfSimulator />} />
                            <Route path="explain" element={<XAIExplainer />} />
                            <Route path="next-action" element={<NextBestAction />} />
                            <Route path="sequencer" element={<InterventionSequencer />} />
                            <Route path="uncertainty" element={<UncertaintyExplorer />} />
                            <Route path="report" element={<ClinicalReport />} />
                            <Route path="twin" element={<DigitalTwinFactory />} />
                            <Route path="*" element={<Navigate to="." replace />} />
                        </Routes>
                    </Suspense>
                </div>
            </div>

            {/* One-time patient onboarding — shown until a patient profile exists */}
            <HeartRateOnboardingModal
                isOpen={!isChecking && needsOnboarding}
                onSubmit={handleOnboardingSubmit}
                isLoading={isCreating}
            />
        </PageContainer>
    );
}

// Outer component — provides PatientContext to the entire Predictions section
function Predictions() {
    return (
        <PatientProvider>
            <PredictionsContent />
        </PatientProvider>
    );
}

export default Predictions;
