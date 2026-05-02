import { Link } from 'react-router-dom';
import { ShieldExclamationIcon, HomeIcon } from '@heroicons/react/24/outline';
import Button from '../../components/common/Button';

function Unauthorized() {
    return (
        <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full text-center">
                {/* Icon */}
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-crisis-100 flex items-center justify-center">
                    <ShieldExclamationIcon className="w-10 h-10 text-crisis-600" />
                </div>

                {/* Message */}
                <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                    Access Denied
                </h1>
                <p className="text-neutral-500 mb-8">
                    You don't have permission to access this page. If you believe this is an error, please contact support.
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
                        as={Link}
                        to="/help"
                        variant="ghost"
                    >
                        Contact Support
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default Unauthorized;