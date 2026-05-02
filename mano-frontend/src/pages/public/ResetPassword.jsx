import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import {
    LockClosedIcon,
    CheckCircleIcon,
    ArrowLeftIcon,
} from '@heroicons/react/24/outline';
import { resetPasswordSchema } from '../../utils/validations';
import { Button, Input, Alert, PasswordStrength } from '../../components/common';

function ResetPassword() {
    const { token } = useParams();
    const navigate = useNavigate();
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: yupResolver(resetPasswordSchema),
        defaultValues: {
            password: '',
            confirmPassword: '',
        },
    });

    const password = watch('password');

    const onSubmit = async (data) => {
        setError(null);
        setIsLoading(true);

        try {
            // API call to reset password with token
            // await authService.resetPassword(token, data.password);

            // Simulate API call
            await new Promise((resolve) => setTimeout(resolve, 1500));
            setIsSubmitted(true);
        } catch (err) {
            setError(err.message || 'Failed to reset password. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Success State
    if (isSubmitted) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4">
                <div className="max-w-md w-full text-center animate-fade-in">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-success-100 flex items-center justify-center">
                        <CheckCircleIcon className="w-10 h-10 text-success-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                        Password reset successful!
                    </h2>
                    <p className="text-neutral-500 mb-8">
                        Your password has been successfully updated. You can now sign in with your new password.
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

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full">
                {/* Logo */}
                <div className="text-center mb-8">
                    <Link to="/" className="inline-flex items-center gap-2 mb-6">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                            <span className="text-lg font-bold text-white font-display">M</span>
                        </div>
                        <span className="text-xl font-bold font-display text-gradient">Manō</span>
                    </Link>
                </div>

                {/* Card */}
                <div className="bg-white rounded-2xl shadow-soft p-8 animate-fade-in">
                    {/* Back Link */}
                    <Link
                        to="/login"
                        className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-700 transition-colors mb-6"
                    >
                        <ArrowLeftIcon className="w-4 h-4" />
                        Back to login
                    </Link>

                    {/* Header */}
                    <div className="mb-8">
                        <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                            Create new password
                        </h2>
                        <p className="text-neutral-500">
                            Your new password must be different from previously used passwords.
                        </p>
                    </div>

                    {/* Error Alert */}
                    {error && (
                        <Alert variant="danger" className="mb-6" dismissible onDismiss={() => setError(null)}>
                            {error}
                        </Alert>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                        <div>
                            <Input
                                label="New Password"
                                type="password"
                                placeholder="Create a strong password"
                                leftIcon={<LockClosedIcon className="w-5 h-5" />}
                                error={errors.password?.message}
                                disabled={isLoading || isSubmitting}
                                autoFocus
                                {...register('password')}
                            />
                            <PasswordStrength password={password} />
                        </div>

                        <Input
                            label="Confirm New Password"
                            type="password"
                            placeholder="Confirm your new password"
                            leftIcon={<LockClosedIcon className="w-5 h-5" />}
                            error={errors.confirmPassword?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('confirmPassword')}
                        />

                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            fullWidth
                            loading={isLoading || isSubmitting}
                            className="mt-6"
                        >
                            Reset Password
                        </Button>
                    </form>
                </div>

                {/* Footer */}
                <p className="mt-8 text-center text-sm text-neutral-500">
                    Remember your password?{' '}
                    <Link
                        to="/login"
                        className="font-semibold text-primary-600 hover:text-primary-700 transition-colors"
                    >
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}

export default ResetPassword;