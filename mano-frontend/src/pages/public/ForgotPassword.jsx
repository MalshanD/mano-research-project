import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import {
    EnvelopeIcon,
    ArrowLeftIcon,
    CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { forgotPasswordSchema } from '../../utils/validations';
import authService from '../../services/authService';
import { Button, Input, Alert } from '../../components/common';

function ForgotPassword() {
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [submittedEmail, setSubmittedEmail] = useState('');
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: yupResolver(forgotPasswordSchema),
        defaultValues: {
            email: '',
        },
    });

    const onSubmit = async (data) => {
        setError(null);
        setIsLoading(true);

        try {
            await authService.forgotPassword(data.email);
            setSubmittedEmail(data.email);
            setIsSubmitted(true);
        } catch (err) {
            // Don't reveal if email exists or not for security
            // Still show success message
            setSubmittedEmail(data.email);
            setIsSubmitted(true);
        } finally {
            setIsLoading(false);
        }
    };

    const handleResend = async () => {
        setIsLoading(true);
        try {
            await authService.forgotPassword(submittedEmail);
            // Show success feedback
        } catch (err) {
            // Silent fail for security
        } finally {
            setIsLoading(false);
        }
    };

    // Success State
    if (isSubmitted) {
        return (
            <div className="animate-fade-in text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-success-100 flex items-center justify-center">
                    <CheckCircleIcon className="w-8 h-8 text-success-600" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Check your email</h2>
                <p className="text-neutral-500 mb-2">
                    If an account exists for <strong className="text-neutral-700">{submittedEmail}</strong>,
                    we've sent password reset instructions.
                </p>
                <p className="text-sm text-neutral-400 mb-8">
                    The link will expire in 24 hours.
                </p>

                <div className="space-y-4">
                    <Button
                        variant="primary"
                        size="lg"
                        fullWidth
                        as={Link}
                        to="/login"
                    >
                        Back to Login
                    </Button>

                    <p className="text-sm text-neutral-500">
                        Didn't receive the email?{' '}
                        <button
                            onClick={handleResend}
                            disabled={isLoading}
                            className="font-medium text-primary-600 hover:text-primary-700 disabled:opacity-50"
                        >
                            {isLoading ? 'Sending...' : 'Resend'}
                        </button>
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="animate-fade-in">
            {/* Back Link */}
            <Link
                to="/login"
                className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-700 transition-colors mb-8"
            >
                <ArrowLeftIcon className="w-4 h-4" />
                Back to login
            </Link>

            {/* Header */}
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Reset your password</h2>
                <p className="text-neutral-500">
                    Enter your email address and we'll send you instructions to reset your password.
                </p>
            </div>

            {/* Error Alert */}
            {error && (
                <Alert variant="danger" className="mb-6" dismissible onDismiss={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Input
                    label="Email Address"
                    type="email"
                    placeholder="Enter your email"
                    leftIcon={<EnvelopeIcon className="w-5 h-5" />}
                    error={errors.email?.message}
                    disabled={isLoading || isSubmitting}
                    autoComplete="email"
                    autoFocus
                    {...register('email')}
                />

                <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={isLoading || isSubmitting}
                >
                    Send Reset Instructions
                </Button>
            </form>

            {/* Help Text */}
            <div className="mt-8 p-4 bg-neutral-50 rounded-xl">
                <h3 className="font-medium text-neutral-900 mb-2">Need help?</h3>
                <p className="text-sm text-neutral-500">
                    If you're having trouble accessing your account, please{' '}
                    <a href="mailto:support@mano.app" className="text-primary-600 hover:text-primary-700">
                        contact our support team
                    </a>.
                </p>
            </div>
        </div>
    );
}

export default ForgotPassword;