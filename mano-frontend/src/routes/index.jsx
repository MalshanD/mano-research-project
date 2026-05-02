import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { PageLoader } from '../components/common/Loader';
import {
    MainLayout,
    AuthLayout,
    ProtectedRoute,
    PublicRoute,
    ErrorBoundary,
} from '../components/layout';
import { ROLES } from '../config/constants';
import { PatientProvider } from '../contexts/PatientContext';

const Landing = lazy(() => import('../pages/public/Landing'));

// Lazy load pages for code splitting
const ForgotPassword = lazy(() => import('../pages/public/ForgotPassword'));
const ResetPassword = lazy(() => import('../pages/public/ResetPassword'));
const VerifyEmail = lazy(() => import('../pages/public/VerifyEmail'));
const NotFound = lazy(() => import('../pages/public/NotFound'));
const Unauthorized = lazy(() => import('../pages/public/Unauthorized'));
const TakeAssessment = lazy(() => import('../pages/user/TakeAssessment'));

// User pages
const Dashboard = lazy(() => import('../pages/user/Dashboard'));
const Chat = lazy(() => import('../pages/user/Chat'));
const Predictions = lazy(() => import('../pages/user/Predictions'));
const Assessments = lazy(() => import('../pages/user/Assessments'));
const Community = lazy(() => import('../pages/user/Community'));
const Activities = lazy(() => import('../pages/user/Activities'));
const Profile = lazy(() => import('../pages/user/Profile'));
const Settings = lazy(() => import('../pages/user/Settings'));
const Journal = lazy(() => import('../pages/user/Journal'));
const Games = lazy(() => import('../pages/user/Games'));
const Insights = lazy(() => import('../pages/user/Insights'));
const TherapySession = lazy(() => import('../pages/user/TherapySession'));

// Professional pages
const ProfessionalDashboard = lazy(() => import('../pages/professional/ProfessionalDashboard'));
const CrisisAlerts = lazy(() => import('../pages/professional/CrisisAlerts'));

// Admin pages
const AdminDashboard = lazy(() => import('../pages/admin/AdminDashboard'));
const UserManagement = lazy(() => import('../pages/admin/UserManagement'));

// ── Component-1 (revamp) consumer pages ───────────────────────────────────
const C1MySummary       = lazy(() => import('../pages/c1/MySummary'));
const C1SeeMyFuture     = lazy(() => import('../pages/c1/SeeMyFuture'));
const C1AIRecommendation = lazy(() => import('../pages/c1/AIRecommendation'));
const C1DigitalTwin     = lazy(() => import('../pages/c1/DigitalTwin'));
const C1UnderstandRisk  = lazy(() => import('../pages/c1/UnderstandMyRisk'));
const C1GuidedTherapy   = lazy(() => import('../pages/c1/GuidedTherapy'));

// ── Component-1 researcher pages (role-gated by ResearcherRoute) ──────────
const C1SimLab         = lazy(() => import('../pages/c1/researcher/SimulationLab'));
const C1Sequencer      = lazy(() => import('../pages/c1/researcher/InterventionSequencer'));
const C1Uncertainty    = lazy(() => import('../pages/c1/researcher/UncertaintyExplorer'));
const C1ClinicalReport = lazy(() => import('../pages/c1/researcher/ClinicalReport'));
const C1ModelDiag      = lazy(() => import('../pages/c1/researcher/ModelDiagnostics'));
import ResearcherRoute from '../components/c1/ResearcherRoute';

// Suspense wrapper
const SuspenseWrapper = ({ children }) => (
    <Suspense fallback={<PageLoader message="Loading page..." />}>
        <ErrorBoundary>{children}</ErrorBoundary>
    </Suspense>
);

function AppRoutes() {
    return (
        <Routes>
            {/* Public Routes - Auth Layout */}
            <Route
                path="/"
                element={
                    <PublicRoute>
                        <SuspenseWrapper>
                            <Landing />
                        </SuspenseWrapper>
                    </PublicRoute>
                }
            />
            {/* /login and /register both redirect to the unified auth modal */}
            <Route path="/login" element={<Navigate to="/?auth=open" replace />} />
            <Route path="/register" element={<Navigate to="/?auth=open" replace />} />

            <Route
                element={
                    <PublicRoute restricted>
                        <AuthLayout />
                    </PublicRoute>
                }
            >
                <Route
                    path="/forgot-password"
                    element={
                        <SuspenseWrapper>
                            <ForgotPassword />
                        </SuspenseWrapper>
                    }
                />
            </Route>

            {/* Standalone Public Pages */}
            <Route
                path="/reset-password/:token"
                element={
                    <SuspenseWrapper>
                        <ResetPassword />
                    </SuspenseWrapper>
                }
            />
            <Route
                path="/verify-email/:token"
                element={
                    <SuspenseWrapper>
                        <VerifyEmail />
                    </SuspenseWrapper>
                }
            />

            {/* Protected Routes - Main Layout */}
            <Route
                element={
                    <ProtectedRoute>
                        <MainLayout />
                    </ProtectedRoute>
                }
            >
                {/* User Routes */}
                <Route
                    path="/dashboard"
                    element={
                        <SuspenseWrapper>
                            <Dashboard />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/chat"
                    element={
                        <SuspenseWrapper>
                            <Chat />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/predictions/*"
                    element={
                        <SuspenseWrapper>
                            <Predictions />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/assessments"
                    element={
                        <SuspenseWrapper>
                            <Assessments />
                        </SuspenseWrapper>
                    }
                />

                <Route
                    path="/assessments/:type"
                    element={
                        <SuspenseWrapper>
                            <TakeAssessment />
                        </SuspenseWrapper>
                    }
                />

                <Route
                    path="/community"
                    element={
                        <SuspenseWrapper>
                            <Community />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/activities"
                    element={
                        <SuspenseWrapper>
                            <Activities />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/journal"
                    element={
                        <SuspenseWrapper>
                            <Journal />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/games"
                    element={
                        <SuspenseWrapper>
                            <Games />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/insights"
                    element={
                        <SuspenseWrapper>
                            <Insights />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/therapy"
                    element={
                        <SuspenseWrapper>
                            <TherapySession />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/profile"
                    element={
                        <SuspenseWrapper>
                            <Profile />
                        </SuspenseWrapper>
                    }
                />
                <Route
                    path="/settings"
                    element={
                        <SuspenseWrapper>
                            <Settings />
                        </SuspenseWrapper>
                    }
                />

                {/* ── Component-1 (revamp) consumer routes ───────── */}
                <Route element={<PatientProvider><Outlet /></PatientProvider>}>
                    <Route path="/c1" element={<Navigate to="/c1/summary" replace />} />
                    <Route path="/c1/summary"        element={<SuspenseWrapper><C1MySummary /></SuspenseWrapper>} />
                    <Route path="/c1/future"         element={<SuspenseWrapper><C1SeeMyFuture /></SuspenseWrapper>} />
                    <Route path="/c1/recommendation" element={<SuspenseWrapper><C1AIRecommendation /></SuspenseWrapper>} />
                    <Route path="/c1/twin"           element={<SuspenseWrapper><C1DigitalTwin /></SuspenseWrapper>} />
                    <Route path="/c1/risk"           element={<SuspenseWrapper><C1UnderstandRisk /></SuspenseWrapper>} />
                    <Route path="/c1/therapy"        element={<SuspenseWrapper><C1GuidedTherapy /></SuspenseWrapper>} />

                    {/* ── Component-1 researcher routes (role-gated) ──── */}
                    <Route path="/c1/researcher" element={<Navigate to="/c1/researcher/simulation-lab" replace />} />
                    <Route path="/c1/researcher/simulation-lab"        element={<SuspenseWrapper><ResearcherRoute><C1SimLab /></ResearcherRoute></SuspenseWrapper>} />
                    <Route path="/c1/researcher/sequencer"             element={<SuspenseWrapper><ResearcherRoute><C1Sequencer /></ResearcherRoute></SuspenseWrapper>} />
                    <Route path="/c1/researcher/uncertainty"           element={<SuspenseWrapper><ResearcherRoute><C1Uncertainty /></ResearcherRoute></SuspenseWrapper>} />
                    <Route path="/c1/researcher/clinical-report"       element={<SuspenseWrapper><ResearcherRoute><C1ClinicalReport /></ResearcherRoute></SuspenseWrapper>} />
                    <Route path="/c1/researcher/model-diagnostics"     element={<SuspenseWrapper><ResearcherRoute><C1ModelDiag /></ResearcherRoute></SuspenseWrapper>} />
                </Route>

                {/* Professional Routes */}
                <Route
                    path="/professional/patients"
                    element={
                        <ProtectedRoute roles={[ROLES.PROFESSIONAL, ROLES.ADMIN]}>
                            <SuspenseWrapper>
                                <ProfessionalDashboard />
                            </SuspenseWrapper>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/professional/alerts"
                    element={
                        <ProtectedRoute roles={[ROLES.PROFESSIONAL, ROLES.ADMIN]}>
                            <SuspenseWrapper>
                                <CrisisAlerts />
                            </SuspenseWrapper>
                        </ProtectedRoute>
                    }
                />

                {/* Admin Routes */}
                <Route
                    path="/admin/users"
                    element={
                        <ProtectedRoute roles={[ROLES.ADMIN]}>
                            <SuspenseWrapper>
                                <AdminDashboard />
                            </SuspenseWrapper>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/admin/system"
                    element={
                        <ProtectedRoute roles={[ROLES.ADMIN]}>
                            <SuspenseWrapper>
                                <UserManagement />
                            </SuspenseWrapper>
                        </ProtectedRoute>
                    }
                />
            </Route>

            {/* Error Pages */}
            <Route
                path="/unauthorized"
                element={
                    <SuspenseWrapper>
                        <Unauthorized />
                    </SuspenseWrapper>
                }
            />

            {/* Root redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* 404 - Must be last */}
            <Route
                path="*"
                element={
                    <SuspenseWrapper>
                        <NotFound />
                    </SuspenseWrapper>
                }
            />
        </Routes>
    );
}

export default AppRoutes;