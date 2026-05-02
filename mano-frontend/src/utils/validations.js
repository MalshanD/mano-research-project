import * as yup from 'yup';

// Common validation patterns
const patterns = {
    password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
    phone: /^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/,
    username: /^[a-zA-Z0-9_]+$/,
};

// Error messages
const messages = {
    required: (field) => `${field} is required`,
    email: 'Please enter a valid email address',
    minLength: (field, min) => `${field} must be at least ${min} characters`,
    maxLength: (field, max) => `${field} must be at most ${max} characters`,
    passwordStrength: 'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character',
    passwordMatch: 'Passwords do not match',
    invalidUsername: 'Username can only contain letters, numbers, and underscores',
    invalidPhone: 'Please enter a valid phone number',
};

// Login validation schema
export const loginSchema = yup.object().shape({
    usernameOrEmail: yup
        .string()
        .required(messages.required('Email or username'))
        .min(3, messages.minLength('Email or username', 3)),
    password: yup
        .string()
        .required(messages.required('Password'))
        .min(6, messages.minLength('Password', 6)),
    rememberMe: yup.boolean().optional(),
});

// Unified login/register schema (guest_name + password only)
export const guestAuthSchema = yup.object().shape({
    guest_name: yup
        .string()
        .required(messages.required('Username'))
        .min(3, messages.minLength('Username', 3))
        .max(50, messages.maxLength('Username', 50)),
    password: yup
        .string()
        .required(messages.required('Password'))
        .min(6, messages.minLength('Password', 6)),
});

// Registration validation schema (simplified: username + password + consent only)
export const registerSchema = yup.object().shape({
    username: yup
        .string()
        .required(messages.required('Username'))
        .min(3, messages.minLength('Username', 3))
        .max(30, messages.maxLength('Username', 30))
        .matches(patterns.username, messages.invalidUsername),
    password: yup
        .string()
        .required(messages.required('Password'))
        .min(6, messages.minLength('Password', 6))
        .matches(patterns.password, messages.passwordStrength),
    confirmPassword: yup
        .string()
        .required(messages.required('Confirm password'))
        .oneOf([yup.ref('password')], messages.passwordMatch),
    privacyConsent: yup
        .boolean()
        .oneOf([true], 'You must accept the privacy policy'),
});

// Forgot password validation schema
export const forgotPasswordSchema = yup.object().shape({
    email: yup
        .string()
        .required(messages.required('Email'))
        .email(messages.email),
});

// Reset password validation schema
export const resetPasswordSchema = yup.object().shape({
    password: yup
        .string()
        .required(messages.required('Password'))
        .min(8, messages.minLength('Password', 8))
        .matches(patterns.password, messages.passwordStrength),
    confirmPassword: yup
        .string()
        .required(messages.required('Confirm password'))
        .oneOf([yup.ref('password')], messages.passwordMatch),
});

// Change password validation schema
// Change Password Schema
export const changePasswordSchema = yup.object().shape({
    currentPassword: yup
        .string()
        .required('Current password is required'),
    newPassword: yup
        .string()
        .required('New password is required')
        .min(8, 'Password must be at least 8 characters')
        .matches(
            patterns.password,
            'Password must contain uppercase, lowercase, number, and special character'
        ),
    confirmNewPassword: yup
        .string()
        .required('Please confirm your new password')
        .oneOf([yup.ref('newPassword')], 'Passwords must match'),
});

// Profile update validation schema
export const profileSchema = yup.object().shape({
    firstName: yup
        .string()
        .required(messages.required('First name'))
        .min(2, messages.minLength('First name', 2))
        .max(50, messages.maxLength('First name', 50)),
    lastName: yup
        .string()
        .required(messages.required('Last name'))
        .min(2, messages.minLength('Last name', 2))
        .max(50, messages.maxLength('Last name', 50)),
    phone: yup
        .string()
        .nullable()
        .transform((value) => (value === '' ? null : value))
        .matches(patterns.phone, { message: messages.invalidPhone, excludeEmptyString: true }),
    dateOfBirth: yup
        .date()
        .nullable()
        .transform((value) => (value === '' ? null : value)),
    gender: yup
        .string()
        .nullable()
        .oneOf(['male', 'female', 'other', 'prefer_not_to_say', null]),
    emergencyContactName: yup
        .string()
        .nullable()
        .max(100, messages.maxLength('Emergency contact name', 100)),
    emergencyContactPhone: yup
        .string()
        .nullable()
        .transform((value) => (value === '' ? null : value))
        .matches(patterns.phone, { message: messages.invalidPhone, excludeEmptyString: true }),
});

export default {
    loginSchema,
    guestAuthSchema,
    registerSchema,
    forgotPasswordSchema,
    resetPasswordSchema,
    changePasswordSchema,
    profileSchema,
};