import { Link } from 'react-router-dom';
import { HomeIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import Button from '../../components/common/Button';

function NotFound() {
    return (
        <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full text-center">
                {/* 404 Illustration */}
                <div className="mb-8">
                    <div className="relative">
            <span className="text-[150px] font-bold font-display text-neutral-100 select-none">
              404
            </span>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-glow animate-bounce-soft">
                                <span className="text-4xl font-bold text-white font-display">?</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Message */}
                <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                    Page not found
                </h1>
                <p className="text-neutral-500 mb-8">
                    Oops! The page you're looking for doesn't exist or has been moved.
                </p>

                {/* Actions */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                    <Button
                        as={Link}
                        to="/dashboard"
                        variant="primary"
                        leftIcon={<HomeIcon className="w-5 h-5" />}
                    >
                        Go to Dashboard
                    </Button>
                    <Button
                        variant="ghost"
                        leftIcon={<ArrowLeftIcon className="w-5 h-5" />}
                        onClick={() => window.history.back()}
                    >
                        Go Back
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default NotFound;