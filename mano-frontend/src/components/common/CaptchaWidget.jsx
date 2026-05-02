import { forwardRef } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import { cn } from '../../utils/helpers';

/**
 * CaptchaWidget — wraps react-google-recaptcha with error display.
 *
 * Usage:
 *   const captchaRef = useRef(null);
 *   <CaptchaWidget ref={captchaRef} onChange={setToken} error={captchaError} />
 *
 * For development/testing the key below is Google's public test key that
 * always passes — replace VITE_RECAPTCHA_SITE_KEY in .env for production.
 */

// Google's official test site key (always passes in dev)
const TEST_SITE_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
const SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || TEST_SITE_KEY;

// forwardRef MUST wrap the function — don't destructure ref from props
const CaptchaWidget = forwardRef(function CaptchaWidget(
    { onChange, error, className, ...props },
    ref
) {
    return (
        <div className={cn('flex flex-col items-center gap-1', className)}>
            <div>
                <ReCAPTCHA
                    ref={ref}
                    sitekey={SITE_KEY}
                    onChange={onChange}
                    onExpired={() => onChange?.(null)}
                    onError={() => onChange?.(null)}
                    theme="light"
                    {...props}
                />
            </div>
            {error && (
                <p className="text-xs text-crisis-500 font-medium">{error}</p>
            )}
        </div>
    );
});

CaptchaWidget.displayName = 'CaptchaWidget';

export default CaptchaWidget;
