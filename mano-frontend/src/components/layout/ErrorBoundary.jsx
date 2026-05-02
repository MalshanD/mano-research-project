// import { Component } from 'react';
// import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
// import Button from '../common/Button';
//
// class ErrorBoundary extends Component {
//     constructor(props) {
//         super(props);
//         this.state = { hasError: false, error: null, errorInfo: null };
//     }
//
//     static getDerivedStateFromError(error) {
//         return { hasError: true, error };
//     }
//
//     componentDidCatch(error, errorInfo) {
//         this.setState({ errorInfo });
//
//         // Log error to error reporting service
//         console.error('Error caught by boundary:', error, errorInfo);
//
//         // You could send to an error tracking service here
//         // errorReportingService.log(error, errorInfo);
//     }
//
//     handleRetry = () => {
//         this.setState({ hasError: false, error: null, errorInfo: null });
//     };
//
//     handleGoHome = () => {
//         window.location.href = '/dashboard';
//     };
//
//     render() {
//         if (this.state.hasError) {
//             return (
//                 <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
//                     <div className="max-w-md w-full text-center">
//                         {/* Icon */}
//                         <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-warning-100 flex items-center justify-center">
//                             <ExclamationTriangleIcon className="w-10 h-10 text-warning-600" />
//                         </div>
//
//                         {/* Message */}
//                         <h1 className="text-2xl font-bold text-neutral-900 mb-2">
//                             Something went wrong
//                         </h1>
//                         <p className="text-neutral-500 mb-6">
//                             We're sorry, but something unexpected happened. Please try again or go back to the dashboard.
//                         </p>
//
//                         {/* Actions */}
//                         <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
//                             <Button variant="primary" onClick={this.handleRetry}>
//                                 Try Again
//                             </Button>
//                             <Button variant="secondary" onClick={this.handleGoHome}>
//                                 Go to Dashboard
//                             </Button>
//                         </div>
//
//                         {/* Error Details (Dev only) */}
//                         {import.meta.env.DEV && this.state.error && (
//                             <details className="mt-8 text-left">
//                                 <summary className="text-sm text-neutral-500 cursor-pointer hover:text-neutral-700">
//                                     Show error details
//                                 </summary>
//                                 <div className="mt-4 p-4 bg-neutral-100 rounded-xl overflow-auto">
//                   <pre className="text-xs text-crisis-600 whitespace-pre-wrap">
//                     {this.state.error.toString()}
//                       {this.state.errorInfo?.componentStack}
//                   </pre>
//                                 </div>
//                             </details>
//                         )}
//                     </div>
//                 </div>
//             );
//         }
//
//         return this.props.children;
//     }
// }
//
// export default ErrorBoundary;

import { Component } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });

        // Log error to error reporting service
        console.error('Error caught by boundary:', error, errorInfo);

        // You could send to an error tracking service here
        // errorReportingService.log(error, errorInfo);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    handleGoHome = () => {
        window.location.href = '/dashboard';
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
                    <div className="max-w-md w-full text-center">
                        {/* Icon */}
                        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-warning-100 flex items-center justify-center">
                            <ExclamationTriangleIcon className="w-10 h-10 text-warning-600" />
                        </div>

                        {/* Message */}
                        <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                            Something went wrong
                        </h1>
                        <p className="text-neutral-500 mb-6">
                            We're sorry, but something unexpected happened. Please try again or go back to the dashboard.
                        </p>

                        {/* Actions - Using native buttons to avoid circular dependency */}
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                            <button
                                onClick={this.handleRetry}
                                className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors duration-200 w-full sm:w-auto"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={this.handleGoHome}
                                className="px-6 py-2.5 bg-neutral-200 hover:bg-neutral-300 text-neutral-900 font-medium rounded-lg transition-colors duration-200 w-full sm:w-auto"
                            >
                                Go to Dashboard
                            </button>
                        </div>

                        {/* Error Details (Dev only) */}
                        {import.meta.env.DEV && this.state.error && (
                            <details className="mt-8 text-left">
                                <summary className="text-sm text-neutral-500 cursor-pointer hover:text-neutral-700">
                                    Show error details
                                </summary>
                                <div className="mt-4 p-4 bg-neutral-100 rounded-xl overflow-auto">
                                    <pre className="text-xs text-red-600 whitespace-pre-wrap">
                                        {this.state.error.toString()}
                                        {this.state.errorInfo?.componentStack}
                                    </pre>
                                </div>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;