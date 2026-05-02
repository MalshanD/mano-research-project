import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    ChatBubbleLeftRightIcon,
    ChartBarIcon,
    UserGroupIcon,
    ShieldCheckIcon,
    SparklesIcon,
    HeartIcon,
    ArrowRightIcon,
    CheckCircleIcon,
    ArrowDownIcon,
} from '@heroicons/react/24/outline';
import { Button } from '../../components/common';
import AuthModal from '../../components/common/AuthModal';
import logoImg from '../../assets/images/logo.png';

/* ───────────────────── Intersection Observer Hook ───────────────────── */
function useInView(options = {}) {
    const ref = useRef(null);
    const [isInView, setIsInView] = useState(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const observer = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) setIsInView(true); },
            { threshold: 0.15, ...options }
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, []);

    return [ref, isInView];
}

/* ───────────────────── Animated Counter ───────────────────── */
function AnimatedCounter({ end, suffix = '', duration = 2000 }) {
    const [count, setCount] = useState(0);
    const [ref, isInView] = useInView();

    useEffect(() => {
        if (!isInView) return;
        let start = 0;
        const step = end / (duration / 16);
        const timer = setInterval(() => {
            start += step;
            if (start >= end) { setCount(end); clearInterval(timer); }
            else setCount(Math.floor(start));
        }, 16);
        return () => clearInterval(timer);
    }, [isInView, end, duration]);

    return <span ref={ref}>{count.toLocaleString()}{suffix}</span>;
}

/* ───────────────────── Floating Orbs Background ───────────────────── */
function FloatingOrbs() {
    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-200/30 rounded-full blur-3xl animate-float" />
            <div className="absolute top-1/3 -left-20 w-60 h-60 bg-accent-200/20 rounded-full blur-3xl animate-float animation-delay-200" style={{ animationDuration: '8s' }} />
            <div className="absolute -bottom-20 right-1/4 w-72 h-72 bg-success-200/20 rounded-full blur-3xl animate-float animation-delay-400" style={{ animationDuration: '10s' }} />
        </div>
    );
}

/* ───────────────────── Scroll Reveal Wrapper ───────────────────── */
function Reveal({ children, className = '', delay = 0, direction = 'up' }) {
    const [ref, isInView] = useInView();

    const directionMap = {
        up: 'translate-y-8',
        down: '-translate-y-8',
        left: 'translate-x-8',
        right: '-translate-x-8',
    };

    return (
        <div
            ref={ref}
            className={`transition-all duration-700 ease-out ${
                isInView ? 'opacity-100 translate-y-0 translate-x-0' : `opacity-0 ${directionMap[direction]}`
            } ${className}`}
            style={{ transitionDelay: `${delay}ms` }}
        >
            {children}
        </div>
    );
}

/* ───────────────────── Data ───────────────────── */
const features = [
    {
        icon: ChatBubbleLeftRightIcon,
        title: 'AI-Powered Chat',
        description: 'Talk to our empathetic AI companion anytime. Get personalized support when you need it most.',
        gradient: 'from-blue-500 to-cyan-500',
        bg: 'bg-blue-50',
        iconColor: 'text-blue-600',
    },
    {
        icon: ChartBarIcon,
        title: 'Smart Insights',
        description: 'Advanced ML models analyze your patterns to provide personalized mental health predictions.',
        gradient: 'from-violet-500 to-purple-500',
        bg: 'bg-violet-50',
        iconColor: 'text-violet-600',
    },
    {
        icon: UserGroupIcon,
        title: 'Peer Community',
        description: 'Connect with others on similar journeys. Share experiences in a safe, moderated space.',
        gradient: 'from-emerald-500 to-teal-500',
        bg: 'bg-emerald-50',
        iconColor: 'text-emerald-600',
    },
    {
        icon: ShieldCheckIcon,
        title: 'Privacy First',
        description: 'Your data is protected with enterprise-grade security and end-to-end encryption.',
        gradient: 'from-amber-500 to-orange-500',
        bg: 'bg-amber-50',
        iconColor: 'text-amber-600',
    },
    {
        icon: SparklesIcon,
        title: 'Personalized Activities',
        description: 'Get tailored wellness recommendations powered by machine learning algorithms.',
        gradient: 'from-pink-500 to-rose-500',
        bg: 'bg-pink-50',
        iconColor: 'text-pink-600',
    },
    {
        icon: HeartIcon,
        title: 'CBT Thought Journal',
        description: 'Identify cognitive distortions in your thinking with AI-powered analysis and reframing.',
        gradient: 'from-teal-500 to-cyan-500',
        bg: 'bg-teal-50',
        iconColor: 'text-teal-600',
    },
];

const stats = [
    { value: 10, suffix: 'K+', label: 'Active Users' },
    { value: 98, suffix: '%', label: 'Satisfaction Rate' },
    { value: 4, suffix: '', label: 'ML Models Integrated' },
    { value: 24, suffix: '/7', label: 'Crisis Support' },
];

const steps = [
    { step: '01', title: 'Take Assessment', description: 'Complete a brief wellness questionnaire to help us understand your needs.' },
    { step: '02', title: 'Get Your Profile', description: 'Our ML models analyze your responses across 7 mental health dimensions.' },
    { step: '03', title: 'Personalized Journey', description: 'Receive tailored activities, community matching, and ongoing AI support.' },
];

const testimonials = [
    { name: 'Sarah M.', role: 'University Student', text: 'Manō helped me understand my anxiety patterns. The thought journal feature is incredible — it actually teaches you to think differently.', avatar: 'S' },
    { name: 'James K.', role: 'Software Engineer', text: 'The AI chat feels like talking to someone who truly understands. The community support made me realize I\'m not alone in this.', avatar: 'J' },
    { name: 'Priya R.', role: 'Healthcare Worker', text: 'As someone in healthcare, I needed something discreet and effective. Manō\'s privacy-first approach won me over completely.', avatar: 'P' },
];

/* ───────────────────── Main Component ───────────────────── */
function Landing() {
    const [searchParams, setSearchParams] = useSearchParams();
    const isModalOpen = searchParams.get('auth') === 'open';
    const [scrolled, setScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const openAuth = () => setSearchParams({ auth: 'open' });
    const closeModal = () => setSearchParams({});

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="min-h-screen bg-white overflow-x-hidden">
            <AuthModal isOpen={isModalOpen} onClose={closeModal} />

            {/* ══════════ NAVBAR ══════════ */}
            <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
                scrolled
                    ? 'bg-white/90 backdrop-blur-xl shadow-soft border-b border-neutral-100/50'
                    : 'bg-transparent'
            }`}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-18 py-4">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <img src={logoImg} alt="Manō" className="w-11 h-11 rounded-xl object-cover" />
                                <div className="absolute inset-0 rounded-xl ring-2 ring-primary-400/20" />
                            </div>
                            <div>
                                <span className="text-xl font-bold font-display text-gradient">Manō</span>
                                <p className="text-[10px] text-neutral-400 tracking-wider uppercase -mt-0.5">Mental Wellness</p>
                            </div>
                        </div>

                        {/* Desktop Nav Links */}
                        <div className="hidden md:flex items-center gap-8">
                            <a href="#features" className="text-sm font-medium text-neutral-600 hover:text-primary-600 transition-colors">Features</a>
                            <a href="#how-it-works" className="text-sm font-medium text-neutral-600 hover:text-primary-600 transition-colors">How It Works</a>
                            <a href="#testimonials" className="text-sm font-medium text-neutral-600 hover:text-primary-600 transition-colors">Stories</a>
                        </div>

                        {/* CTA Buttons */}
                        <div className="flex items-center gap-3">
                            <button
                                onClick={openAuth}
                                className="hidden sm:block text-sm font-medium text-neutral-600 hover:text-primary-600 transition-colors"
                            >
                                Sign In
                            </button>
                            <Button onClick={openAuth} variant="primary" size="sm" className="shadow-glow/50">
                                Get Started Free
                            </Button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* ══════════ HERO ══════════ */}
            <section className="relative pt-28 sm:pt-36 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
                <FloatingOrbs />

                {/* Subtle grid background */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(14,165,233,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(14,165,233,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />

                <div className="max-w-7xl mx-auto relative z-10">
                    <div className="text-center max-w-4xl mx-auto">
                        {/* Badge */}
                        <Reveal>
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-50 border border-primary-100 mb-8">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500" />
                                </span>
                                <span className="text-sm font-medium text-primary-700">AI-Powered Mental Wellness Platform</span>
                            </div>
                        </Reveal>

                        {/* Heading */}
                        <Reveal delay={100}>
                            <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold font-display text-neutral-900 mb-6 leading-[1.1] tracking-tight">
                                Your mind deserves{' '}
                                <span className="relative inline-block">
                                    <span className="text-gradient">better care</span>
                                    <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none">
                                        <path d="M2 8C50 2 100 2 150 6C200 10 250 4 298 8" stroke="url(#underline-gradient)" strokeWidth="3" strokeLinecap="round" />
                                        <defs>
                                            <linearGradient id="underline-gradient" x1="0" y1="0" x2="300" y2="0">
                                                <stop stopColor="#0ea5e9" />
                                                <stop offset="1" stopColor="#f97316" />
                                            </linearGradient>
                                        </defs>
                                    </svg>
                                </span>
                            </h1>
                        </Reveal>

                        {/* Subheading */}
                        <Reveal delay={200}>
                            <p className="text-lg sm:text-xl text-neutral-500 mb-10 max-w-2xl mx-auto leading-relaxed">
                                Personalized AI support, cognitive behavioral tools, and a caring peer community — all working together for your wellness journey.
                            </p>
                        </Reveal>

                        {/* CTA */}
                        <Reveal delay={300}>
                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
                                <Button
                                    onClick={openAuth}
                                    variant="primary"
                                    size="xl"
                                    className="shadow-glow group"
                                    rightIcon={<ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
                                >
                                    Start Your Journey
                                </Button>
                                <Button onClick={openAuth} variant="outline" size="xl">
                                    Sign In
                                </Button>
                            </div>
                            <p className="text-sm text-neutral-400 flex items-center justify-center gap-2">
                                <CheckCircleIcon className="w-4 h-4 text-success-500" />
                                Free forever — No credit card required
                            </p>
                        </Reveal>
                    </div>

                    {/* Hero Image with floating effect */}
                    <Reveal delay={500}>
                        <div className="mt-16 sm:mt-20 relative group">
                            {/* Glow behind image */}
                            <div className="absolute -inset-4 bg-gradient-to-r from-primary-200/40 via-accent-200/30 to-primary-200/40 rounded-[2rem] blur-2xl opacity-60 group-hover:opacity-80 transition-opacity duration-700" />

                            <div className="relative bg-gradient-to-br from-primary-50/80 to-accent-50/80 rounded-3xl p-2 sm:p-3 backdrop-blur-sm border border-white/60">
                                <div className="bg-white rounded-2xl shadow-soft-lg overflow-hidden border border-neutral-100/50">
                                    <img
                                        src="/dash-image.png"
                                        alt="Manō Wellness Dashboard"
                                        className="w-full h-auto object-contain"
                                    />
                                </div>
                            </div>

                            {/* Floating badge - left */}
                            <div className="hidden lg:flex absolute -left-6 top-1/4 animate-float bg-white rounded-2xl shadow-soft-lg p-4 items-center gap-3 border border-neutral-100">
                                <div className="w-10 h-10 rounded-xl bg-success-100 flex items-center justify-center">
                                    <CheckCircleIcon className="w-5 h-5 text-success-600" />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-neutral-800">Wellness Score</p>
                                    <p className="text-xs text-success-600 font-medium">+12% this week</p>
                                </div>
                            </div>

                            {/* Floating badge - right */}
                            <div className="hidden lg:flex absolute -right-6 top-1/3 animate-float animation-delay-300 bg-white rounded-2xl shadow-soft-lg p-4 items-center gap-3 border border-neutral-100" style={{ animationDuration: '7s' }}>
                                <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center">
                                    <SparklesIcon className="w-5 h-5 text-primary-600" />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-neutral-800">AI Analysis</p>
                                    <p className="text-xs text-primary-600 font-medium">Pattern detected</p>
                                </div>
                            </div>
                        </div>
                    </Reveal>

                    {/* Scroll indicator */}
                    <div className="flex justify-center mt-12">
                        <a href="#stats" className="animate-bounce-soft">
                            <ArrowDownIcon className="w-5 h-5 text-neutral-300" />
                        </a>
                    </div>
                </div>
            </section>

            {/* ══════════ STATS BAR ══════════ */}
            <section id="stats" className="relative py-16 px-4 sm:px-6 lg:px-8">
                <div className="absolute inset-0 bg-gradient-to-r from-primary-600 via-primary-500 to-primary-700" />
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjA1Ij48cGF0aCBkPSJNMzYgMzRhMiAyIDAgMSAxIDAtNCAyIDIgMCAwIDEgMCA0eiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
                <div className="max-w-7xl mx-auto relative z-10">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                        {stats.map((stat, i) => (
                            <Reveal key={i} delay={i * 100}>
                                <div className="text-center">
                                    <p className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-2 font-display">
                                        <AnimatedCounter end={stat.value} suffix={stat.suffix} />
                                    </p>
                                    <p className="text-sm sm:text-base text-primary-100 font-medium">{stat.label}</p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ FEATURES ══════════ */}
            <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-neutral-50/50">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider text-primary-600 bg-primary-50 border border-primary-100 mb-4">
                                Features
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-display text-neutral-900 mb-4 tracking-tight">
                                Everything you need for{' '}
                                <span className="text-gradient">mental wellness</span>
                            </h2>
                            <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
                                Comprehensive AI-powered tools designed to understand, support, and improve your mental health.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                        {features.map((feature, i) => (
                            <Reveal key={i} delay={i * 80}>
                                <div className="group relative bg-white rounded-2xl p-7 shadow-soft border border-neutral-100/80 hover:shadow-soft-lg hover:-translate-y-1.5 transition-all duration-500 overflow-hidden">
                                    {/* Hover gradient accent */}
                                    <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${feature.gradient} scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left`} />

                                    <div className={`w-14 h-14 rounded-2xl ${feature.bg} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300`}>
                                        <feature.icon className={`w-7 h-7 ${feature.iconColor}`} />
                                    </div>
                                    <h3 className="text-lg font-bold text-neutral-900 mb-2 font-display">
                                        {feature.title}
                                    </h3>
                                    <p className="text-neutral-500 leading-relaxed text-[15px]">
                                        {feature.description}
                                    </p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ HOW IT WORKS ══════════ */}
            <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8 bg-white">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider text-primary-600 bg-primary-50 border border-primary-100 mb-4">
                                How It Works
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-display text-neutral-900 mb-4 tracking-tight">
                                Three steps to a{' '}
                                <span className="text-gradient">healthier mind</span>
                            </h2>
                            <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
                                Getting started is simple. Our AI takes care of the rest.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-3 gap-8 lg:gap-12 relative">
                        {/* Connecting line */}
                        <div className="hidden md:block absolute top-16 left-[20%] right-[20%] h-0.5 bg-gradient-to-r from-primary-200 via-primary-400 to-primary-200" />

                        {steps.map((item, i) => (
                            <Reveal key={i} delay={i * 150}>
                                <div className="relative text-center">
                                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 text-white text-xl font-extrabold font-display mb-6 shadow-glow relative z-10">
                                        {item.step}
                                    </div>
                                    <h3 className="text-xl font-bold text-neutral-900 mb-3 font-display">{item.title}</h3>
                                    <p className="text-neutral-500 leading-relaxed max-w-xs mx-auto">{item.description}</p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ TESTIMONIALS ══════════ */}
            <section id="testimonials" className="py-24 px-4 sm:px-6 lg:px-8 bg-neutral-50/50">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider text-primary-600 bg-primary-50 border border-primary-100 mb-4">
                                Stories
                            </span>
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-display text-neutral-900 mb-4 tracking-tight">
                                Loved by thousands of{' '}
                                <span className="text-gradient">users</span>
                            </h2>
                            <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
                                Hear from people who transformed their mental wellness with Manō.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
                        {testimonials.map((t, i) => (
                            <Reveal key={i} delay={i * 100}>
                                <div className="bg-white rounded-2xl p-7 shadow-soft border border-neutral-100/80 hover:shadow-soft-lg transition-all duration-500 h-full flex flex-col">
                                    {/* Stars */}
                                    <div className="flex gap-1 mb-4">
                                        {[...Array(5)].map((_, j) => (
                                            <svg key={j} className="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                            </svg>
                                        ))}
                                    </div>
                                    <p className="text-neutral-600 leading-relaxed mb-6 flex-1 italic">"{t.text}"</p>
                                    <div className="flex items-center gap-3 pt-4 border-t border-neutral-100">
                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-sm">
                                            {t.avatar}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-neutral-800">{t.name}</p>
                                            <p className="text-xs text-neutral-400">{t.role}</p>
                                        </div>
                                    </div>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ CTA ══════════ */}
            <section className="py-24 px-4 sm:px-6 lg:px-8">
                <div className="max-w-5xl mx-auto">
                    <Reveal>
                        <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-primary-600 via-primary-500 to-primary-700 p-10 lg:p-16 text-center">
                            {/* Background pattern */}
                            <div className="absolute inset-0 opacity-10">
                                <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full -translate-x-1/2 -translate-y-1/2" />
                                <div className="absolute bottom-0 right-0 w-60 h-60 bg-white rounded-full translate-x-1/3 translate-y-1/3" />
                                <div className="absolute top-1/2 left-1/2 w-32 h-32 bg-white rounded-full -translate-x-1/2 -translate-y-1/2" />
                            </div>

                            <div className="relative z-10">
                                <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-display text-white mb-4 tracking-tight">
                                    Ready to feel better?
                                </h2>
                                <p className="text-lg text-primary-100 mb-10 max-w-2xl mx-auto leading-relaxed">
                                    Join thousands who are already taking control of their mental health. Your journey starts with a single step.
                                </p>
                                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                    <Button
                                        onClick={openAuth}
                                        size="xl"
                                        className="bg-white text-primary-700 hover:bg-primary-50 shadow-lg hover:shadow-xl transition-all duration-300 font-bold"
                                        rightIcon={<ArrowRightIcon className="w-5 h-5" />}
                                    >
                                        Get Started — It's Free
                                    </Button>
                                </div>
                                <p className="text-sm text-primary-200 mt-6 flex items-center justify-center gap-2">
                                    <ShieldCheckIcon className="w-4 h-4" />
                                    No credit card required — 100% free to use
                                </p>
                            </div>
                        </div>
                    </Reveal>
                </div>
            </section>

            {/* ══════════ FOOTER ══════════ */}
            <footer className="bg-neutral-900 text-neutral-300">
                {/* Top border gradient */}
                <div className="h-1 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500" />

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                    <div className="grid md:grid-cols-4 gap-12 mb-12">
                        {/* Brand */}
                        <div className="md:col-span-2">
                            <div className="flex items-center gap-3 mb-5">
                                <img src={logoImg} alt="Manō" className="w-11 h-11 rounded-xl object-cover" />
                                <div>
                                    <span className="text-xl font-bold font-display text-white">Manō</span>
                                    <p className="text-xs text-neutral-500 -mt-0.5">Mental Wellness Platform</p>
                                </div>
                            </div>
                            <p className="text-neutral-400 leading-relaxed max-w-sm mb-6">
                                AI-powered mental wellness support designed to help you understand your mind, build resilience, and connect with others on similar journeys.
                            </p>
                            <div className="flex gap-4">
                                {['twitter', 'github', 'linkedin'].map(social => (
                                    <button key={social} className="w-9 h-9 rounded-lg bg-neutral-800 flex items-center justify-center hover:bg-primary-600 transition-colors duration-300">
                                        <span className="text-xs text-neutral-400 hover:text-white uppercase font-bold">{social[0]}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Links */}
                        <div>
                            <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Platform</h4>
                            <ul className="space-y-3">
                                {['Features', 'How It Works', 'Community', 'Pricing'].map(link => (
                                    <li key={link}>
                                        <button onClick={link === 'Pricing' ? openAuth : undefined} className="text-sm text-neutral-400 hover:text-white transition-colors">
                                            {link}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Support</h4>
                            <ul className="space-y-3">
                                {['Help Center', 'Privacy Policy', 'Terms of Service', 'Contact Us'].map(link => (
                                    <li key={link}>
                                        <button className="text-sm text-neutral-400 hover:text-white transition-colors">
                                            {link}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Bottom bar */}
                    <div className="pt-8 border-t border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <p className="text-sm text-neutral-500">
                            &copy; {new Date().getFullYear()} Manō. All rights reserved.
                        </p>
                        <p className="text-sm text-neutral-500 flex items-center gap-1.5">
                            Built with <HeartIcon className="w-4 h-4 text-crisis-400" /> for mental wellness
                        </p>
                    </div>
                </div>
            </footer>

            {/* ══════════ CRISIS BANNER ══════════ */}
            <div className="fixed bottom-0 left-0 right-0 z-50 bg-gradient-to-r from-crisis-600 to-crisis-700 text-white py-2.5 px-4 text-center text-sm shadow-lg">
                <span>If you're in crisis, call </span>
                <a href="tel:988" className="font-bold underline decoration-2 underline-offset-2 hover:text-crisis-100 transition-colors">988</a>
                <span> (Suicide &amp; Crisis Lifeline) or text HOME to </span>
                <a href="sms:741741" className="font-bold underline decoration-2 underline-offset-2 hover:text-crisis-100 transition-colors">741741</a>
            </div>
        </div>
    );
}

export default Landing;
