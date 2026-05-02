import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { PageLoader } from '../common/Loader';

function ProtectedRoute({ children, roles = [], redirectTo = '/login' }) {
    const { isAuthenticated, isLoading, user, hasAnyRole } = useAuth();
    const location = useLocation();

    // Show loading state while checking auth
    if (isLoading) {
        return <PageLoader message="Checking authentication..." />;
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to={redirectTo} state={{ from: location }} replace />;
    }

    // Check role-based access
    if (roles.length > 0 && !hasAnyRole(roles)) {
        // User doesn't have required role, redirect to dashboard or unauthorized page
        return <Navigate to="/unauthorized" replace />;
    }

    return children;
}

export default ProtectedRoute;