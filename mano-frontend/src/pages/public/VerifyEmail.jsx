import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
    CheckCircleIcon,
    XCircleIcon,
    ArrowPathIcon,
} from '@heroicons/react/24/outline';
import authService from '../../services/authService';
import { Button, Loader } from '../../components/common';

function VerifyEmail() {
    const { token } = useParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState('loading'); // loading, success, error, expired
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        verifyEmail();
    }, [token]);

    const verifyEmail = async () => {
        if (!token) {
            setStatus('error');
            setErrorMessage('Invalid verification link');
            return;
        }

        try {
            await authService.verifyEmail(token);
            setStatus('success');
        } catch (err) {
            if (err.message?.includes('expired')) {
                setStatus('expired');
            } else {
                setStatus('error');
                setErrorMessage(err.message || 'Verification failed');
            }
        }
    };

    const handleResendVerification = async () => {
        // This would need the user's email
        // For now, redirect to login
        navigate('/login');
    };

    // Loading State
    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
                <div className="text-center animate-fade-in">
                    <Loader size="xl" className="mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                        Verifying your email...
                    </h2>
                    <p className="text-neutral-500">Please wait a moment</p>
                </div>
            </div>
        );
    }

    // Success State
    if (status === 'success') {
        return (
            <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
                <div className="max-w-md w-full text-center animate-fade-in">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-success-100 flex items-center justify-center">
                        <CheckCircleIcon className="w-10 h-10 text-success-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                        Email verified!
                    </h2>
                    <p className="text-neutral-500 mb-8">
                        Your email has been successfully verified. You can now sign in to your account.
                    </p>
                    <Button
                        variant="primary"
                        size="lg"
                        fullWidth
                        onClick={() => navigate('/login')}
                    >
                        Go to Login
                    </Button>
                </div>
            </div>
        );
    }

    // Expired State
    if (status === 'expired') {
        return (
            <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
                <div className="max-w-md w-full text-center animate-fade-in">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-warning-100 flex items-center justify-center">
                        <ArrowPathIcon className="w-10 h-10 text-warning-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                        Link expired
                    </h2>
                    <p className="text-neutral-500 mb-8">
                        This verification link has expired. Please request a new verification email.
                    </p>
                    <div className="space-y-4">
                        <Button
                            variant="primary"
                            size="lg"
                            fullWidth
                            onClick={handleResendVerification}
                        >
                            Resend Verification Email
                        </Button>
                        <Button
                            variant="ghost"
                            fullWidth
                            onClick={() => navigate('/login')}
                        >
                            Back to Login
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    // Error State
    return (
        <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full text-center animate-fade-in">
                <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-crisis-100 flex items-center justify-center">
                    <XCircleIcon className="w-10 h-10 text-crisis-600" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                    Verification failed
                </h2>
                <p className="text-neutral-500 mb-8">
                    {errorMessage || 'We couldn\'t verify your email. The link may be invalid or already used.'}
                </p>
                <div className="space-y-4">
                    <Button
                        variant="primary"
                        size="lg"
                        fullWidth
                        onClick={handleResendVerification}
                    >
                        Request New Verification
                    </Button>
                    <Button
                        variant="ghost"
                        fullWidth
                        onClick={() => navigate('/login')}
                    >
                        Back to Login
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default VerifyEmail;