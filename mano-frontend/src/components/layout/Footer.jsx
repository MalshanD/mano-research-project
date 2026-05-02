import { Link } from 'react-router-dom';
import { HeartIcon } from '@heroicons/react/24/solid';

function Footer({ minimal = false }) {
    const currentYear = new Date().getFullYear();

    if (minimal) {
        return (
            <footer className="py-4 text-center text-sm text-neutral-500">
                <p>© {currentYear} Manō. All rights reserved.</p>
            </footer>
        );
    }

    return (
        <footer className="bg-white/60 backdrop-blur-sm border-t border-sand/30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="py-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {/* Brand */}
                        <div className="col-span-2 md:col-span-1">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-2xl bg-gradient-to-br from-terracotta to-terracotta-light flex items-center justify-center">
                                    <span className="text-sm font-bold text-white font-display">M</span>
                                </div>
                                <span className="text-lg font-bold font-display text-organic-gradient">Manō</span>
                            </div>
                            <p className="text-sm text-neutral-500 mb-4">
                                Your AI-powered mental wellness companion. Supporting your journey to better mental health.
                            </p>
                            <div className="flex items-center gap-1 text-sm text-neutral-500">
                                <span>Made with</span>
                                <HeartIcon className="w-4 h-4 text-coral" />
                                <span>for mental wellness</span>
                            </div>
                        </div>

                        {/* Quick Links */}
                        <div>
                            <h3 className="font-semibold text-neutral-900 mb-4">Quick Links</h3>
                            <ul className="space-y-3">
                                <li>
                                    <Link to="/dashboard" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Dashboard
                                    </Link>
                                </li>
                                <li>
                                    <Link to="/chat" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Chat with AI
                                    </Link>
                                </li>
                                <li>
                                    <Link to="/assessments" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Assessments
                                    </Link>
                                </li>
                                <li>
                                    <Link to="/community" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Community
                                    </Link>
                                </li>
                            </ul>
                        </div>

                        {/* Resources */}
                        <div>
                            <h3 className="font-semibold text-neutral-900 mb-4">Resources</h3>
                            <ul className="space-y-3">
                                <li>
                                    <Link to="/help" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Help Center
                                    </Link>
                                </li>
                                <li>
                                    <Link to="/privacy" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Privacy Policy
                                    </Link>
                                </li>
                                <li>
                                    <Link to="/terms" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Terms of Service
                                    </Link>
                                </li>
                                <li>
                                    <a href="mailto:support@mano.app" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                                        Contact Us
                                    </a>
                                </li>
                            </ul>
                        </div>

                        {/* Emergency */}
                        <div>
                            <h3 className="font-semibold text-neutral-900 mb-4">Crisis Support</h3>
                            <div className="space-y-3">
                                <div className="p-3 bg-coral-light/10 border border-coral-light/20 rounded-2xl">
                                    <p className="text-xs text-coral-dark font-medium mb-1">Suicide Prevention</p>
                                    <a href="tel:988" className="text-lg font-bold text-coral-dark">
                                        988
                                    </a>
                                </div>
                                <div className="p-3 bg-cream rounded-2xl">
                                    <p className="text-xs text-neutral-500 font-medium mb-1">Crisis Text Line</p>
                                    <p className="text-sm font-semibold text-neutral-700">Text HOME to 741741</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="py-4 border-t border-sand/30 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <p className="text-sm text-neutral-500">
                        © {currentYear} Manō Mental Wellness. All rights reserved.
                    </p>
                    <div className="flex items-center gap-6">
                        <Link to="/privacy" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                            Privacy
                        </Link>
                        <Link to="/terms" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                            Terms
                        </Link>
                        <Link to="/accessibility" className="text-sm text-neutral-500 hover:text-terracotta transition-colors">
                            Accessibility
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}

export default Footer;