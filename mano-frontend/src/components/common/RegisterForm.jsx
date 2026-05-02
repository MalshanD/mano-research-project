import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import {
    UserIcon,
    LockClosedIcon,
    CheckIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { registerSchema } from '../../utils/validations';
import { Button, Input, Checkbox, Alert, PasswordStrength } from '../common';
import CaptchaWidget from './CaptchaWidget';

function RegisterForm({ onSwitchToLogin }) {
    const { register: registerUser, isLoading, error: authError, clearError } = useAuth();
    const [registrationComplete, setRegistrationComplete] = useState(false);
    const captchaRef = useRef(null);
    const [captchaToken, setCaptchaToken] = useState(null);
    const [captchaError, setCaptchaError] = useState('');

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: yupResolver(registerSchema),
        defaultValues: {
            username: '',
            password: '',
            confirmPassword: '',
            privacyConsent: false,
        },
        mode: 'onChange',
    });

    const password = watch('password');

    const onSubmit = async (data) => {
        // Validate CAPTCHA
        if (!captchaToken) {
            setCaptchaError('Please complete the CAPTCHA verification.');
            return;
        }
        setCaptchaError('');
        clearError();

        const result = await registerUser({
            username: data.username,
            password: data.password,
            privacyConsent: data.privacyConsent,
            captchaToken,
        });

        if (result.success) {
            setRegistrationComplete(true);
        } else {
            // Reset CAPTCHA on failure
            captchaRef.current?.reset();
            setCaptchaToken(null);
        }
    };

    // Registration Complete Screen
    if (registrationComplete) {
        return (
            <div className="animate-fade-in text-center py-4">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-success-100 flex items-center justify-center">
                    <CheckIcon className="w-8 h-8 text-success-600" />
                </div>
                <h2 className="text-xl font-bold text-neutral-900 mb-2">Account Created!</h2>
                <p className="text-neutral-500 text-sm mb-6">
                    We've sent a verification link to your email. Please verify your account before signing in.
                </p>
                <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    onClick={() => {
                        onSwitchToLogin?.();
                        setRegistrationComplete(false);
                    }}
                >
                    Go to Sign In
                </Button>
            </div>
        );
    }

    return (
        <div className="animate-fade-in">
            {/* Header */}
            <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-neutral-900 mb-1">Create your account</h2>
                <p className="text-neutral-500 text-sm">Start your mental wellness journey today</p>
            </div>

            {/* Error Alert */}
            {authError && (
                <Alert variant="danger" className="mb-4" dismissible onDismiss={clearError}>
                    {authError}
                </Alert>
            )}

            {/* Register Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <Input
                    label="Username"
                    placeholder="Choose a username"
                    leftIcon={<UserIcon className="w-5 h-5" />}
                    error={errors.username?.message}
                    hint="Letters, numbers, and underscores only"
                    disabled={isLoading || isSubmitting}
                    autoFocus
                    {...register('username')}
                />

                <div>
                    <Input
                        label="Password"
                        type="password"
                        placeholder="Create a strong password"
                        leftIcon={<LockClosedIcon className="w-5 h-5" />}
                        error={errors.password?.message}
                        disabled={isLoading || isSubmitting}
                        {...register('password')}
                    />
                    <PasswordStrength password={password} />
                </div>

                <Input
                    label="Confirm Password"
                    type="password"
                    placeholder="Confirm your password"
                    leftIcon={<LockClosedIcon className="w-5 h-5" />}
                    error={errors.confirmPassword?.message}
                    disabled={isLoading || isSubmitting}
                    {...register('confirmPassword')}
                />

                <Checkbox
                    label="I agree to the Privacy Policy and Terms of Service"
                    description="Required to create an account"
                    error={errors.privacyConsent?.message}
                    disabled={isLoading || isSubmitting}
                    {...register('privacyConsent')}
                />

                {/* CAPTCHA */}
                <CaptchaWidget
                    ref={captchaRef}
                    onChange={(token) => {
                        setCaptchaToken(token);
                        if (token) setCaptchaError('');
                    }}
                    error={captchaError}
                />

                <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={isLoading || isSubmitting}
                >
                    Create Account
                </Button>
            </form>

            {/* Switch to Login */}
            <p className="mt-5 text-center text-sm text-neutral-500">
                Already have an account?{' '}
                <button
                    onClick={onSwitchToLogin}
                    className="font-semibold text-primary-600 hover:text-primary-700 transition-colors"
                >
                    Sign in
                </button>
            </p>
        </div>
    );
}

export default RegisterForm;
