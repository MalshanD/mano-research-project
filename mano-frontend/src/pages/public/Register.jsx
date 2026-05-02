import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import {
    UserIcon,
    EnvelopeIcon,
    LockClosedIcon,
    PhoneIcon,
    CalendarIcon,
    ArrowLeftIcon,
    ArrowRightIcon,
    CheckIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { registerSchema } from '../../utils/validations';
import {
    Button,
    Input,
    Select,
    Checkbox,
    Alert,
    Divider,
    SocialButtons,
    PasswordStrength,
} from '../../components/common';
import { cn } from '../../utils/helpers';

// Multi-step form configuration
const STEPS = [
    { id: 1, title: 'Account', description: 'Basic information' },
    { id: 2, title: 'Security', description: 'Create password' },
    { id: 3, title: 'Profile', description: 'Optional details' },
];

function Register() {
    const navigate = useNavigate();
    const { register: registerUser, isLoading, error: authError, clearError } = useAuth();
    const [currentStep, setCurrentStep] = useState(1);
    const [registrationComplete, setRegistrationComplete] = useState(false);

    const {
        register,
        handleSubmit,
        watch,
        trigger,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: yupResolver(registerSchema),
        defaultValues: {
            firstName: '',
            lastName: '',
            username: '',
            email: '',
            password: '',
            confirmPassword: '',
            phone: '',
            dateOfBirth: '',
            gender: '',
            privacyConsent: false,
            dataSharingConsent: false,
        },
        mode: 'onChange',
    });

    const password = watch('password');

    // Validate current step fields before proceeding
    const validateStep = async () => {
        const fieldsToValidate = {
            1: ['firstName', 'lastName', 'username', 'email'],
            2: ['password', 'confirmPassword'],
            3: ['privacyConsent'],
        };

        const isValid = await trigger(fieldsToValidate[currentStep]);
        return isValid;
    };

    const handleNext = async () => {
        const isValid = await validateStep();
        if (isValid && currentStep < 3) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
        }
    };

    const onSubmit = async (data) => {
        clearError();

        const result = await registerUser({
            firstName: data.firstName,
            lastName: data.lastName,
            username: data.username,
            email: data.email,
            password: data.password,
            phone: data.phone || null,
            dateOfBirth: data.dateOfBirth || null,
            gender: data.gender || null,
            privacyConsent: data.privacyConsent,
            dataSharingConsent: data.dataSharingConsent,
        });

        if (result.success) {
            setRegistrationComplete(true);
        }
    };

    const handleSocialLogin = (provider) => {
        console.log(`Register with ${provider}`);
    };

    // Registration Complete Screen
    if (registrationComplete) {
        return (
            <div className="animate-fade-in text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-success-100 flex items-center justify-center">
                    <CheckIcon className="w-8 h-8 text-success-600" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Check your email</h2>
                <p className="text-neutral-500 mb-8">
                    We've sent a verification link to your email address. Please verify your email to activate your account.
                </p>
                <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    onClick={() => navigate('/login', { state: { registered: true } })}
                >
                    Go to Login
                </Button>
                <p className="mt-4 text-sm text-neutral-500">
                    Didn't receive the email?{' '}
                    <button className="font-medium text-primary-600 hover:text-primary-700">
                        Resend verification email
                    </button>
                </p>
            </div>
        );
    }

    return (
        <div className="animate-fade-in">
            {/* Header */}
            <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Create your account</h2>
                <p className="text-neutral-500">Start your mental wellness journey today</p>
            </div>

            {/* Progress Steps */}
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    {STEPS.map((step, index) => (
                        <div key={step.id} className="flex items-center">
                            <div className="flex flex-col items-center">
                                <div
                                    className={cn(
                                        'w-10 h-10 rounded-full flex items-center justify-center font-medium text-sm transition-all',
                                        currentStep > step.id
                                            ? 'bg-success-500 text-white'
                                            : currentStep === step.id
                                                ? 'bg-primary-500 text-white'
                                                : 'bg-neutral-100 text-neutral-400'
                                    )}
                                >
                                    {currentStep > step.id ? (
                                        <CheckIcon className="w-5 h-5" />
                                    ) : (
                                        step.id
                                    )}
                                </div>
                                <div className="mt-2 text-center hidden sm:block">
                                    <p
                                        className={cn(
                                            'text-xs font-medium',
                                            currentStep >= step.id ? 'text-neutral-900' : 'text-neutral-400'
                                        )}
                                    >
                                        {step.title}
                                    </p>
                                </div>
                            </div>
                            {index < STEPS.length - 1 && (
                                <div
                                    className={cn(
                                        'flex-1 h-0.5 mx-2 sm:mx-4 transition-all',
                                        currentStep > step.id ? 'bg-success-500' : 'bg-neutral-200'
                                    )}
                                />
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Error Alert */}
            {authError && (
                <Alert variant="danger" className="mb-6" dismissible onDismiss={clearError}>
                    {authError}
                </Alert>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)}>
                {/* Step 1: Account Information */}
                {currentStep === 1 && (
                    <div className="space-y-5 animate-fade-in">
                        <SocialButtons
                            onGoogleClick={() => handleSocialLogin('google')}
                            onAppleClick={() => handleSocialLogin('apple')}
                            disabled={isLoading || isSubmitting}
                        />

                        <Divider label="or register with email" className="my-6" />

                        <div className="grid grid-cols-2 gap-4">
                            <Input
                                label="First Name"
                                placeholder="John"
                                leftIcon={<UserIcon className="w-5 h-5" />}
                                error={errors.firstName?.message}
                                disabled={isLoading || isSubmitting}
                                autoFocus
                                {...register('firstName')}
                            />
                            <Input
                                label="Last Name"
                                placeholder="Doe"
                                error={errors.lastName?.message}
                                disabled={isLoading || isSubmitting}
                                {...register('lastName')}
                            />
                        </div>

                        <Input
                            label="Username"
                            placeholder="johndoe"
                            leftIcon={<UserIcon className="w-5 h-5" />}
                            error={errors.username?.message}
                            hint="Letters, numbers, and underscores only"
                            disabled={isLoading || isSubmitting}
                            {...register('username')}
                        />

                        <Input
                            label="Email"
                            type="email"
                            placeholder="john@example.com"
                            leftIcon={<EnvelopeIcon className="w-5 h-5" />}
                            error={errors.email?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('email')}
                        />
                    </div>
                )}

                {/* Step 2: Security */}
                {currentStep === 2 && (
                    <div className="space-y-5 animate-fade-in">
                        <div>
                            <Input
                                label="Password"
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
                            label="Confirm Password"
                            type="password"
                            placeholder="Confirm your password"
                            leftIcon={<LockClosedIcon className="w-5 h-5" />}
                            error={errors.confirmPassword?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('confirmPassword')}
                        />
                    </div>
                )}

                {/* Step 3: Profile (Optional) & Consent */}
                {currentStep === 3 && (
                    <div className="space-y-5 animate-fade-in">
                        <div className="p-4 bg-neutral-50 rounded-xl mb-4">
                            <p className="text-sm text-neutral-600">
                                These fields are optional but help us personalize your experience.
                            </p>
                        </div>

                        <Input
                            label="Phone Number"
                            type="tel"
                            placeholder="+1 (555) 000-0000"
                            leftIcon={<PhoneIcon className="w-5 h-5" />}
                            error={errors.phone?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('phone')}
                        />

                        <Input
                            label="Date of Birth"
                            type="date"
                            leftIcon={<CalendarIcon className="w-5 h-5" />}
                            error={errors.dateOfBirth?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('dateOfBirth')}
                        />

                        <Select
                            label="Gender"
                            placeholder="Select gender (optional)"
                            options={[
                                { value: 'male', label: 'Male' },
                                { value: 'female', label: 'Female' },
                                { value: 'other', label: 'Other' },
                                { value: 'prefer_not_to_say', label: 'Prefer not to say' },
                            ]}
                            error={errors.gender?.message}
                            disabled={isLoading || isSubmitting}
                            {...register('gender')}
                        />

                        <Divider className="my-6" />

                        {/* Consent Checkboxes */}
                        <div className="space-y-4">
                            <Checkbox
                                label="I agree to the Privacy Policy and Terms of Service"
                                description="Required to create an account"
                                error={errors.privacyConsent?.message}
                                disabled={isLoading || isSubmitting}
                                {...register('privacyConsent')}
                            />
                            <Checkbox
                                label="I consent to data sharing for research purposes"
                                description="Optional - helps improve mental health research"
                                disabled={isLoading || isSubmitting}
                                {...register('dataSharingConsent')}
                            />
                        </div>
                    </div>
                )}

                {/* Navigation Buttons */}
                <div className="flex items-center justify-between mt-8 gap-4">
                    {currentStep > 1 ? (
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={handleBack}
                            leftIcon={<ArrowLeftIcon className="w-4 h-4" />}
                            disabled={isLoading || isSubmitting}
                        >
                            Back
                        </Button>
                    ) : (
                        <div />
                    )}

                    {currentStep < 3 ? (
                        <Button
                            type="button"
                            variant="primary"
                            onClick={handleNext}
                            rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                            disabled={isLoading || isSubmitting}
                        >
                            Continue
                        </Button>
                    ) : (
                        <Button
                            type="submit"
                            variant="primary"
                            loading={isLoading || isSubmitting}
                        >
                            Create Account
                        </Button>
                    )}
                </div>
            </form>

            {/* Sign In Link */}
            <p className="mt-8 text-center text-sm text-neutral-500">
                Already have an account?{' '}
                <Link
                    to="/login"
                    className="font-semibold text-primary-600 hover:text-primary-700 transition-colors"
                >
                    Sign in
                </Link>
            </p>
        </div>
    );
}

export default Register;