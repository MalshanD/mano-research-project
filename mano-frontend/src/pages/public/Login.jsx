import { useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import {
    LockClosedIcon,
    ArrowRightIcon,
    SparklesIcon,
    ArrowPathIcon,
    UserCircleIcon,
    ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { guestAuthSchema } from '../../utils/validations';
import { Button, Input, Alert } from '../../components/common';
import CaptchaWidget from '../../components/common/CaptchaWidget';

// ─── Random guest name generator ────────────────────────────────────────────
const ADJECTIVES = [
    'Calm', 'Bright', 'Gentle', 'Kind', 'Bold', 'Swift', 'Serene', 'Brave',
    'Quiet', 'Warm', 'Clear', 'Wise', 'Fuzzy', 'Happy', 'Cozy', 'Lively',
    'Sunny', 'Misty', 'Azure', 'Amber',
];
const NOUNS = [
    'Panda', 'Breeze', 'River', 'Falcon', 'Cedar', 'Maple', 'Lotus', 'Cloud',
    'Ember', 'Stone', 'Willow', 'Robin', 'Crane', 'Dusk', 'Dawn', 'Spark',
    'Haven', 'Peak', 'Tide', 'Fern',
];

function randomGuestName() {
    const adj = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)];
    const noun = NOUNS[Math.floor(Math.random() * NOUNS.length)];
    const num = Math.floor(Math.random() * 900) + 100;
    return `${adj}${noun}${num}`;
}
// ────────────────────────────────────────────────────────────────────────────

function Login() {
    const navigate = useNavigate();
    const location = useLocation();
    const { loginOrRegister, isLoading, error: authError, clearError } = useAuth();

    const captchaRef = useRef(null);
    const [captchaToken, setCaptchaToken] = useState(null);
    const [captchaError, setCaptchaError] = useState('');
    const [spinning, setSpinning] = useState(false);

    const from = location.state?.from?.pathname || '/dashboard';

    const {
        register,
        handleSubmit,
        setValue,
        formState: { errors, isSubmitting },
    } = useForm({
        resolver: yupResolver(guestAuthSchema),
        defaultValues: { guest_name: '', password: '' },
    });

    const { ref: guestNameRef, ...guestNameRest } = register('guest_name');

    const handleRandomName = useCallback(() => {
        setSpinning(true);
        setValue('guest_name', randomGuestName(), { shouldValidate: true });
        setTimeout(() => setSpinning(false), 400);
    }, [setValue]);

    const onSubmit = async (data) => {
        if (!captchaToken) {
            setCaptchaError('Please complete the CAPTCHA verification.');
            return;
        }
        setCaptchaError('');
        clearError();

        const result = await loginOrRegister({
            guest_name: data.guest_name,
            password: data.password,
        });

        if (result.success) {
            navigate(from, { replace: true });
        } else {
            captchaRef.current?.reset();
            setCaptchaToken(null);
        }
    };

    const isDisabled = isLoading || isSubmitting;

    return (
        <div className="animate-fade-in">
            {/* Header */}
            <div className="text-center mb-8">
                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-primary-50 flex items-center justify-center">
                    <SparklesIcon className="w-7 h-7 text-primary-600" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Welcome to Mano</h2>
                <p className="text-neutral-500 text-sm">
                    Enter your guest name and password to continue.
                    <br />
                    <span className="text-primary-600 font-medium">New here? We'll create your account automatically.</span>
                </p>
            </div>

            {/* Error Alert */}
            {authError && (
                <Alert variant="danger" className="mb-6" dismissible onDismiss={clearError}>
                    {authError}
                </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

                {/* ── Guest Name field ─────────────────────────────────── */}
                <div>
                    <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
                        Guest Name
                    </label>

                    <div
                        className={[
                            'flex items-center bg-white dark:bg-neutral-900 border rounded-xl transition-all duration-200',
                            'focus-within:ring-2 focus-within:ring-offset-0',
                            errors.guest_name
                                ? 'border-crisis-300 focus-within:border-crisis-500 focus-within:ring-crisis-100'
                                : 'border-neutral-200 dark:border-neutral-700 focus-within:border-primary-500 focus-within:ring-primary-100',
                            isDisabled ? 'bg-neutral-50 dark:bg-neutral-800' : '',
                        ].join(' ')}
                    >
                        {/* Left icon */}
                        <span className="pl-3 flex items-center text-neutral-400 dark:text-neutral-500 flex-shrink-0">
                            <UserCircleIcon className="w-5 h-5" />
                        </span>

                        {/* Input */}
                        <input
                            ref={guestNameRef}
                            {...guestNameRest}
                            type="text"
                            placeholder="Enter your guest name"
                            autoComplete="username"
                            autoFocus
                            disabled={isDisabled}
                            className="flex-1 min-w-0 bg-transparent px-3 py-3 text-base text-neutral-800 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 border-0 focus:ring-0 focus:border-0 focus:shadow-none outline-none focus:outline-none disabled:cursor-not-allowed disabled:text-neutral-500 dark:disabled:text-neutral-600"
                            style={{ boxShadow: 'none' }}
                        />

                        {/* Right: "Random" chip button */}
                        <div className="pr-2 flex-shrink-0">
                            <button
                                type="button"
                                onClick={handleRandomName}
                                disabled={isDisabled}
                                title="Generate a random guest name"
                                className="
                                    inline-flex items-center gap-1.5
                                    px-2.5 py-1.5 rounded-lg
                                    text-xs font-semibold
                                    bg-primary-50 text-primary-600
                                    hover:bg-primary-100 hover:text-primary-700
                                    border border-primary-200 hover:border-primary-300
                                    transition-all duration-200
                                    disabled:opacity-40 disabled:cursor-not-allowed
                                    select-none
                                "
                            >
                                <ArrowPathIcon
                                    className={`w-3.5 h-3.5 transition-transform duration-400 ${spinning ? 'rotate-180' : ''}`}
                                />
                                Random
                            </button>
                        </div>
                    </div>

                    {errors.guest_name ? (
                        <p className="mt-1.5 text-sm text-crisis-500 flex items-center gap-1">
                            <ExclamationCircleIcon className="w-4 h-4 flex-shrink-0" />
                            {errors.guest_name.message}
                        </p>
                    ) : (
                        <p className="mt-1.5 text-sm text-neutral-500">
                            New users are registered automatically.
                        </p>
                    )}
                </div>
                {/* ──────────────────────────────────────────────────────── */}

                {/* Password */}
                <Input
                    label="Password"
                    type="password"
                    placeholder="Enter your password"
                    leftIcon={<LockClosedIcon className="w-5 h-5" />}
                    error={errors.password?.message}
                    disabled={isDisabled}
                    autoComplete="current-password"
                    hint="At least 6 characters."
                    {...register('password')}
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

                {/* Submit */}
                <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={isDisabled}
                    rightIcon={!isDisabled ? <ArrowRightIcon className="w-4 h-4" /> : null}
                >
                    Continue
                </Button>
            </form>

            {/* Info Banner */}
            <div className="mt-6 p-4 bg-primary-50 rounded-xl border border-primary-100">
                <p className="text-xs text-primary-700 text-center leading-relaxed">
                    🔐 &nbsp;If your guest name exists, you'll be signed in. If not, a new account is created — no email required.
                </p>
            </div>

            {/* Dev Demo Credentials */}
            {import.meta.env.DEV && (
                <div className="mt-4 p-4 bg-neutral-50 rounded-xl border border-neutral-200">
                    <p className="text-xs text-neutral-500 text-center mb-2">Demo Credentials</p>
                    <div className="flex items-center justify-center gap-4 text-xs">
                        <span className="text-neutral-600">
                            <strong>Guest Name:</strong> demodemodemo
                        </span>
                        <span className="text-neutral-600">
                            <strong>Password:</strong> demodemodemo
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Login;