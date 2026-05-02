import { Link } from 'react-router-dom';
import {
    ShieldCheckIcon,
    LockClosedIcon,
    EyeIcon,
    TrashIcon,
    DocumentTextIcon,
    ServerIcon,
    UserGroupIcon,
    BellAlertIcon,
} from '@heroicons/react/24/outline';

const sections = [
    {
        id: 'data-collected',
        icon: DocumentTextIcon,
        title: '1. Information We Collect',
        content: [
            {
                subtitle: 'Account Information',
                text: 'When you register, we collect your name, email address, username, and optionally your phone number, date of birth, and gender. This information is required to create and manage your account.',
            },
            {
                subtitle: 'Mental Health Data',
                text: 'With your explicit consent, we collect data from your self-assessments, mood check-ins, journal entries, and interactions with our AI companion. This data is used solely to provide personalized mental health support.',
            },
            {
                subtitle: 'Usage Data',
                text: 'We automatically collect information about how you use the platform, including pages visited, features used, session duration, and device/browser information, to improve our services.',
            },
            {
                subtitle: 'Communication Data',
                text: 'Messages sent to our AI companion are processed to generate responses and may be reviewed by our team (in anonymized form) to improve model performance. Professional consultations may be recorded with your prior consent.',
            },
        ],
    },
    {
        id: 'how-we-use',
        icon: ServerIcon,
        title: '2. How We Use Your Data',
        content: [
            {
                subtitle: 'Providing Services',
                text: 'We use your data to operate and personalize the Manō platform, including generating AI-powered insights, activity recommendations, and risk assessments tailored to your mental health journey.',
            },
            {
                subtitle: 'Research & Improvement',
                text: 'With your separate, optional consent to the data sharing option during registration, your anonymized data may contribute to mental health research. You may withdraw this consent at any time from Settings.',
            },
            {
                subtitle: 'Safety & Crisis Response',
                text: 'When our systems detect potential crisis signals, relevant data is flagged to licensed mental health professionals on our platform who may reach out to offer support. This is a core safety feature.',
            },
            {
                subtitle: 'Communications',
                text: 'We send account-related emails (verification, password resets) and, with your consent, wellness tips and platform updates. You can manage notification preferences in Settings.',
            },
        ],
    },
    {
        id: 'data-sharing',
        icon: UserGroupIcon,
        title: '3. Data Sharing',
        content: [
            {
                subtitle: 'Mental Health Professionals',
                text: 'If you choose to connect with a professional on our platform, they will have access to the data you explicitly share with them, including your assessment results and risk scores.',
            },
            {
                subtitle: 'Service Providers',
                text: 'We work with trusted third-party providers (cloud hosting, analytics, payment processors) who are contractually bound to protect your data and may not use it for any other purpose.',
            },
            {
                subtitle: 'Legal Requirements',
                text: 'We may disclose your information if required by law, court order, or to protect the rights, safety, or property of Manō, our users, or the public. We will notify you of such disclosures where legally possible.',
            },
            {
                subtitle: 'We Never Sell Your Data',
                text: 'Manō does not sell, rent, or trade your personal information or mental health data to advertisers, data brokers, or any third party for commercial purposes. Your mental health is not a product.',
            },
        ],
    },
    {
        id: 'data-security',
        icon: LockClosedIcon,
        title: '4. Data Security',
        content: [
            {
                subtitle: 'Encryption',
                text: 'All data is encrypted in transit using TLS 1.3 and at rest using AES-256 encryption. Mental health data receives additional encryption layers.',
            },
            {
                subtitle: 'Differential Privacy',
                text: 'When your data is used for research or analytics, we apply differential privacy techniques to ensure individual users cannot be re-identified from aggregate datasets.',
            },
            {
                subtitle: 'Access Controls',
                text: 'Access to your data is strictly limited on a need-to-know basis. All staff with data access undergo background checks and privacy training.',
            },
            {
                subtitle: 'Breach Notification',
                text: 'In the unlikely event of a data breach affecting your information, we will notify you within 72 hours and take immediate steps to mitigate any harm.',
            },
        ],
    },
    {
        id: 'your-rights',
        icon: EyeIcon,
        title: '5. Your Rights',
        content: [
            {
                subtitle: 'Access Your Data',
                text: 'You can request a full export of all data we hold about you at any time through Settings → Privacy → Download My Data.',
            },
            {
                subtitle: 'Correct Your Data',
                text: 'You can update or correct your personal information directly in your Profile settings. For data that cannot be self-corrected, contact our support team.',
            },
            {
                subtitle: 'Delete Your Account',
                text: 'You can permanently delete your account and all associated data from Settings → Account → Delete Account. Some data may be retained for up to 30 days in backups before permanent deletion.',
            },
            {
                subtitle: 'Withdraw Consent',
                text: 'You can withdraw consent for data sharing for research at any time from Settings. This will not affect the lawfulness of processing based on consent before withdrawal.',
            },
        ],
    },
    {
        id: 'data-retention',
        icon: TrashIcon,
        title: '6. Data Retention',
        content: [
            {
                subtitle: 'Active Accounts',
                text: 'We retain your data for as long as your account is active and as necessary to provide the services you use.',
            },
            {
                subtitle: 'After Account Deletion',
                text: 'After you delete your account, most personal data is permanently deleted within 30 days. Some anonymized data may be retained in aggregated form for research purposes if you previously consented.',
            },
            {
                subtitle: 'Legal Retention',
                text: 'Certain data may be retained longer if required by law (e.g., financial transaction records for up to 7 years, or data subject to legal holds).',
            },
        ],
    },
    {
        id: 'crisis-alerts',
        icon: BellAlertIcon,
        title: '7. Crisis Detection & Safety',
        content: [
            {
                subtitle: 'Automated Detection',
                text: 'Our AI systems continuously analyze patterns in your interactions to detect potential mental health crises. This is a safety-critical feature that cannot be disabled.',
            },
            {
                subtitle: 'Professional Review',
                text: 'When a crisis is detected, a licensed mental health professional on our platform will be notified and may reach out. In cases of immediate risk to life, we may contact emergency services.',
            },
            {
                subtitle: 'Why This Data Must Be Processed',
                text: 'Processing of sensitive mental health data for crisis detection is based on vital interests — protecting life — and is a core part of our service agreement, as required by applicable law.',
            },
        ],
    },
];

function PrivacyPolicy() {
    return (
        <div className="min-h-screen bg-white">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-neutral-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Link to="/" className="flex items-center gap-2">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                                <span className="text-lg font-bold text-white font-display">M</span>
                            </div>
                            <span className="text-xl font-bold font-display text-gradient">Manō</span>
                        </Link>
                        <div className="flex items-center gap-4">
                            <Link
                                to="/login"
                                className="text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
                            >
                                Sign In
                            </Link>
                            <Link
                                to="/register"
                                className="text-sm font-medium bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
                            >
                                Get Started
                            </Link>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero */}
            <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-primary-50 via-white to-accent-50">
                <div className="max-w-4xl mx-auto text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center mx-auto mb-6 shadow-glow">
                        <ShieldCheckIcon className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-4xl sm:text-5xl font-bold font-display text-neutral-900 mb-4">
                        Privacy Policy
                    </h1>
                    <p className="text-lg text-neutral-600 max-w-2xl mx-auto mb-4">
                        We believe your mental health data deserves the highest level of protection.
                        Here's exactly how we collect, use, and protect your information.
                    </p>
                    <div className="inline-flex items-center gap-2 text-sm text-neutral-500 bg-white rounded-full px-4 py-2 border border-neutral-200 shadow-soft">
                        <span className="w-2 h-2 rounded-full bg-success-500 animate-pulse-soft" />
                        Last updated: February 28, 2026
                    </div>
                </div>
            </section>

            {/* Quick Navigation */}
            <section className="py-8 px-4 sm:px-6 lg:px-8 border-b border-neutral-100 bg-white sticky top-16 z-40">
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
                        <span className="text-xs font-medium text-neutral-500 whitespace-nowrap mr-2">Jump to:</span>
                        {sections.map((s) => (
                            <a
                                key={s.id}
                                href={`#${s.id}`}
                                className="text-xs font-medium text-primary-600 hover:text-primary-800 whitespace-nowrap bg-primary-50 hover:bg-primary-100 px-3 py-1.5 rounded-full transition-colors"
                            >
                                {s.title.replace(/^\d+\.\s/, '')}
                            </a>
                        ))}
                    </div>
                </div>
            </section>

            {/* Key Commitments */}
            <section className="py-12 px-4 sm:px-6 lg:px-8 bg-neutral-50">
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-xl font-bold font-display text-neutral-900 mb-6 text-center">
                        Our Privacy Commitments
                    </h2>
                    <div className="grid sm:grid-cols-3 gap-4">
                        {[
                            { emoji: '🔒', title: 'Never Sold', desc: 'Your data is never sold to advertisers or third parties' },
                            { emoji: '🧠', title: 'Mental Health First', desc: 'Sensitive health data receives maximum protection' },
                            { emoji: '✋', title: 'You\'re in Control', desc: 'Download or delete your data at any time' },
                        ].map((item) => (
                            <div key={item.title} className="bg-white rounded-2xl p-5 shadow-soft text-center">
                                <div className="text-3xl mb-3">{item.emoji}</div>
                                <h3 className="font-semibold text-neutral-900 mb-1">{item.title}</h3>
                                <p className="text-sm text-neutral-500">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Main Content */}
            <section className="py-16 px-4 sm:px-6 lg:px-8">
                <div className="max-w-4xl mx-auto space-y-16">
                    {sections.map((section) => (
                        <div key={section.id} id={section.id} className="scroll-mt-32">
                            <div className="flex items-start gap-4 mb-8">
                                <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
                                    <section.icon className="w-6 h-6 text-primary-600" />
                                </div>
                                <h2 className="text-2xl font-bold font-display text-neutral-900 pt-2">
                                    {section.title}
                                </h2>
                            </div>
                            <div className="grid gap-6 ml-16">
                                {section.content.map((item, idx) => (
                                    <div
                                        key={idx}
                                        className="bg-neutral-50 rounded-xl p-5 border border-neutral-100 hover:border-primary-200 hover:bg-primary-50/30 transition-colors"
                                    >
                                        <h3 className="font-semibold text-neutral-900 mb-2 text-sm">
                                            {item.subtitle}
                                        </h3>
                                        <p className="text-neutral-600 text-sm leading-relaxed">{item.text}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}

                    {/* Contact */}
                    <div className="bg-gradient-to-br from-primary-600 to-primary-700 rounded-3xl p-8 text-white text-center">
                        <h2 className="text-2xl font-bold font-display mb-3">Questions About Your Privacy?</h2>
                        <p className="text-primary-100 mb-6 max-w-xl mx-auto">
                            Our Privacy Team is here to help. Contact us with any questions, concerns, or data requests.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <a
                                href="mailto:privacy@mano.health"
                                className="inline-flex items-center gap-2 bg-white text-primary-700 font-semibold px-6 py-3 rounded-xl hover:bg-primary-50 transition-colors"
                            >
                                privacy@mano.health
                            </a>
                            <Link
                                to="/settings"
                                className="inline-flex items-center gap-2 bg-primary-500 text-white font-semibold px-6 py-3 rounded-xl hover:bg-primary-400 transition-colors"
                            >
                                Manage My Data →
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-8 px-4 sm:px-6 lg:px-8 border-t border-neutral-100 bg-neutral-50">
                <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-neutral-500">
                    <span>© {new Date().getFullYear()} Manō. All rights reserved.</span>
                    <div className="flex items-center gap-4">
                        <Link to="/terms" className="hover:text-neutral-700 transition-colors">Terms of Service</Link>
                        <Link to="/help" className="hover:text-neutral-700 transition-colors">Help Center</Link>
                        <Link to="/login" className="hover:text-neutral-700 transition-colors">Sign In</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}

export default PrivacyPolicy;
