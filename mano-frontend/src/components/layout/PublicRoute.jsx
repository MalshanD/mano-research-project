import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { PageLoader } from '../common/Loader';

function PublicRoute({ children, restricted = false }) {
    const { isAuthenticated, isLoading } = useAuth();
    const location = useLocation();

    // Show loading state while checking auth
    if (isLoading) {
        return <PageLoader message="Loading..." />;
    }

    // If route is restricted (like login page) and user is authenticated,
    // redirect to dashboard or the page they came from
    if (restricted && isAuthenticated) {
        const from = location.state?.from?.pathname || '/dashboard';
        return <Navigate to={from} replace />;
    }

    return children;
}

export default PublicRoute;