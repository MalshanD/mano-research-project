import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';
import {
    AuthProvider,
    ThemeProvider,
    NotificationProvider,
    WebSocketProvider,
} from './contexts';
import { ErrorBoundary } from './components/layout';
import AppRoutes from './routes';

// Create React Query client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 5 * 60 * 1000,
        },
    },
});

// Toast configuration
const toastOptions = {
    duration: 4000,
    position: 'top-right',
    style: {
        background: '#fff',
        color: '#171717',
        padding: '16px',
        borderRadius: '12px',
        boxShadow: '0 10px 40px -10px rgba(0, 0, 0, 0.1)',
        fontSize: '14px',
    },
    success: {
        iconTheme: { primary: '#22c55e', secondary: '#fff' },
    },
    error: {
        iconTheme: { primary: '#ef4444', secondary: '#fff' },
    },
};

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <ErrorBoundary>
                    <ThemeProvider>
                        <NotificationProvider>
                            <AuthProvider>
                                <WebSocketProvider>
                                    <AppRoutes />
                                    <Toaster toastOptions={toastOptions} />
                                </WebSocketProvider>
                            </AuthProvider>
                        </NotificationProvider>
                    </ThemeProvider>
                </ErrorBoundary>
            </BrowserRouter>
            {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
    );
}

export default App;