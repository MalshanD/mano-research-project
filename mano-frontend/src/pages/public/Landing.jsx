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
import AuthModal from '../../components/common/AuthModal';
import logoImg from '../../assets/images/logo.png';
import styles from './Landing.module.css';

/* ────────────────────────── Intersection Observer Hook ────────────────────────── */
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

/* ────────────────────────── Animated Counter ────────────────────────── */
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

/* ────────────────────────── Scroll Reveal Wrapper ────────────────────────── */
function Reveal({ children, className = '', delay = 0, direction = 'up' }) {
    const [ref, isInView] = useInView();

    const directionMap = {
        up:    'translate-y-8',
        down:  '-translate-y-8',
        left:  'translate-x-8',
        right: '-translate-x-8',
    };

    return (
        <div
            ref={ref}
            className={`transition-all duration-700 ease-out ${
                isInView
                    ? 'opacity-100 translate-y-0 translate-x-0'
                    : `opacity-0 ${directionMap[direction]}`
            } ${className}`}
            style={{ transitionDelay: `${delay}ms` }}
        >
            {children}
        </div>
    );
}

/* ────────────────────────── Hero Staggered Words ────────────────────────── */
function StaggeredHeading({ words, gradientWords = [], delay = 0 }) {
    const [show, setShow] = useState(false);
    useEffect(() => {
        const t = setTimeout(() => setShow(true), delay);
        return () => clearTimeout(t);
    }, [delay]);
    return (
        <h1 className="font-display text-4xl sm:text-5xl lg:text-7xl font-extrabold leading-[1.05] tracking-tight text-white mb-6">
            {words.map((w, i) => {
                const isGrad = gradientWords.includes(i);
                return (
                    <span
                        key={i}
                        className={`${styles.heroWord} ${show ? styles.heroWordIn : ''} ${isGrad ? styles.gradientText : ''} mr-3`}
                        style={{ transitionDelay: `${i * 110}ms` }}
                    >
                        {w}
                    </span>
                );
            })}
        </h1>
    );
}

/* ────────────────────────── Cosmos Background ────────────────────────── */
function CosmosBackground() {
    useEffect(() => {
        let raf = 0;
        let last = 0;
        const onScroll = () => {
            if (raf) return;
            raf = requestAnimationFrame(() => {
                const y = window.scrollY;
                if (Math.abs(y - last) > 0.5) {
                    document.documentElement.style.setProperty('--scroll', y);
                    last = y;
                }
                raf = 0;
            });
        };
        // Disable parallax for reduced-motion users
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!reduce) window.addEventListener('scroll', onScroll, { passive: true });
        return () => {
            window.removeEventListener('scroll', onScroll);
            if (raf) cancelAnimationFrame(raf);
        };
    }, []);

    return (
        <div className={styles.cosmosBg} aria-hidden="true">
            <div className={`${styles.stars} ${styles.starsSm}`} />
            <div className={`${styles.stars} ${styles.starsMd}`} />
            <div className={`${styles.stars} ${styles.starsLg}`} />
            <div className={`${styles.nebula} ${styles.nebula1}`} />
            <div className={`${styles.nebula} ${styles.nebula2}`} />
            <div className={`${styles.nebula} ${styles.nebula3}`} />
            <div className={styles.gridOverlay} />
            <div className={styles.vignette} />
        </div>
    );
}

/* ────────────────────────── Data ────────────────────────── */
const features = [
    {
        icon: ChatBubbleLeftRightIcon,
        title: 'AI-Powered Chat',
        description: 'Talk to our empathetic AI companion anytime. Get personalized support when you need it most.',
        ring: 'border-blue-400/30 bg-blue-500/10 text-blue-300',
    },
    {
        icon: ChartBarIcon,
        title: 'Smart Insights',
        description: 'Advanced ML models analyze your patterns to provide personalized mental health predictions.',
        ring: 'border-violet-400/30 bg-violet-500/10 text-violet-300',
    },
    {
        icon: UserGroupIcon,
        title: 'Peer Community',
        description: 'Connect with others on similar journeys. Share experiences in a safe, moderated space.',
        ring: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-300',
    },
    {
        icon: ShieldCheckIcon,
        title: 'Privacy First',
        description: 'Your data is protected with enterprise-grade security and end-to-end encryption.',
        ring: 'border-amber-400/30 bg-amber-500/10 text-amber-300',
    },
    {
        icon: SparklesIcon,
        title: 'Personalized Activities',
        description: 'Get tailored wellness recommendations powered by machine learning algorithms.',
        ring: 'border-pink-400/30 bg-pink-500/10 text-pink-300',
    },
    {
        icon: HeartIcon,
        title: 'CBT Thought Journal',
        description: 'Identify cognitive distortions in your thinking with AI-powered analysis and reframing.',
        ring: 'border-cyan-400/30 bg-cyan-500/10 text-cyan-300',
    },
];

const stats = [
    { value: 10, suffix: 'K+', label: 'Active Users' },
    { value: 98, suffix: '%',  label: 'Satisfaction Rate' },
    { value: 4,  suffix: '',   label: 'ML Models Integrated' },
    { value: 24, suffix: '/7', label: 'Crisis Support' },
];

const steps = [
    { step: '01', title: 'Take Assessment',     description: 'Complete a brief wellness questionnaire to help us understand your needs.' },
    { step: '02', title: 'Get Your Profile',    description: 'Our ML models analyze your responses across 7 mental health dimensions.' },
    { step: '03', title: 'Personalized Journey',description: 'Receive tailored activities, community matching, and ongoing AI support.' },
];

const testimonials = [
    { name: 'Sarah M.', role: 'University Student', text: 'Manō helped me understand my anxiety patterns. The thought journal feature is incredible — it actually teaches you to think differently.', avatar: 'S' },
    { name: 'James K.', role: 'Software Engineer',  text: 'The AI chat feels like talking to someone who truly understands. The community support made me realize I\'m not alone in this.', avatar: 'J' },
    { name: 'Priya R.', role: 'Healthcare Worker',  text: 'As someone in healthcare, I needed something discreet and effective. Manō\'s privacy-first approach won me over completely.', avatar: 'P' },
];

/* ════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ════════════════════════════════════════════════════════════ */
function Landing() {
    const [searchParams, setSearchParams] = useSearchParams();
    const isModalOpen = searchParams.get('auth') === 'open';
    const [scrolled, setScrolled] = useState(false);

    const openAuth = () => setSearchParams({ auth: 'open' });
    const closeModal = () => setSearchParams({});

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="relative min-h-screen overflow-x-hidden text-slate-100 font-body bg-[#050518]">
            <CosmosBackground />
            <AuthModal isOpen={isModalOpen} onClose={closeModal} />

            {/* ══════════ NAVBAR ══════════ */}
            <nav
                className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
                    scrolled
                        ? 'bg-[#050518]/70 backdrop-blur-xl border-b border-violet-300/15 py-3'
                        : 'bg-transparent py-4'
                }`}
            >
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <div className="relative w-11 h-11 rounded-xl border border-violet-300/20 bg-violet-400/10 flex items-center justify-center overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-cyan-500 opacity-20" />
                                <img src={logoImg} alt="Manō" className="relative w-8 h-8 object-cover rounded-lg" />
                            </div>
                            <div>
                                <span className="block font-display text-xl font-extrabold bg-gradient-to-br from-violet-300 to-cyan-300 bg-clip-text text-transparent">Manō</span>
                                <p className="text-[10px] text-slate-500 tracking-[0.15em] uppercase -mt-0.5">Mental Wellness</p>
                            </div>
                        </div>

                        {/* Desktop Nav Links */}
                        <div className="hidden md:flex items-center gap-8">
                            <a href="#features"     className="text-sm font-medium text-slate-300 hover:text-violet-300 transition-colors">Features</a>
                            <a href="#how-it-works" className="text-sm font-medium text-slate-300 hover:text-violet-300 transition-colors">How It Works</a>
                            <a href="#testimonials" className="text-sm font-medium text-slate-300 hover:text-violet-300 transition-colors">Stories</a>
                        </div>

                        {/* CTA Buttons */}
                        <div className="flex items-center gap-3">
                            <button
                                onClick={openAuth}
                                className="hidden sm:block text-sm font-medium text-slate-300 hover:text-violet-300 transition-colors"
                            >
                                Sign In
                            </button>
                            <button
                                onClick={openAuth}
                                className={`${styles.cosmicBtn} px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300`}
                            >
                                Get Started Free
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* ══════════ HERO ══════════ */}
            <section className="relative pt-32 sm:pt-40 pb-20 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center max-w-4xl mx-auto">
                        {/* Badge */}
                        <Reveal>
                            <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-violet-400/10 border border-violet-300/20 backdrop-blur-md mb-8">
                                <span className={styles.pulseDot} />
                                <span className="text-[13px] font-medium text-violet-200">AI-Powered Mental Wellness Platform</span>
                            </div>
                        </Reveal>

                        {/* Heading — staggered word-by-word */}
                        <StaggeredHeading
                            words={['Your', 'mind', 'deserves', 'better', 'care']}
                            gradientWords={[3, 4]}
                            delay={150}
                        />

                        {/* Subheading */}
                        <Reveal delay={700}>
                            <p className="text-lg sm:text-xl text-slate-300 mb-10 max-w-2xl mx-auto leading-relaxed">
                                Personalized AI support, cognitive behavioral tools, and a caring peer community —
                                all working together for your wellness journey.
                            </p>
                        </Reveal>

                        {/* CTA */}
                        <Reveal delay={850}>
                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
                                <button
                                    onClick={openAuth}
                                    className={`${styles.cosmicBtn} group inline-flex items-center gap-3 px-8 py-4 rounded-2xl text-base font-semibold transition-all duration-300`}
                                >
                                    Start Your Journey
                                    <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </button>
                                <button
                                    onClick={openAuth}
                                    className={`${styles.ghostBtn} px-8 py-4 rounded-2xl text-base font-semibold transition-all duration-300`}
                                >
                                    Sign In
                                </button>
                            </div>
                            <p className="text-sm text-slate-400 flex items-center justify-center gap-2">
                                <CheckCircleIcon className="w-4 h-4 text-cyan-400" />
                                Free forever — No credit card required
                            </p>
                        </Reveal>
                    </div>

                    {/* Hero visual mockup */}
                    <Reveal delay={1100}>
                        <div className="mt-20 relative max-w-5xl mx-auto group">
                            <div className={styles.heroGlow} />

                            <div className="relative rounded-3xl p-2 sm:p-3 backdrop-blur-xl bg-gradient-to-br from-violet-400/10 to-cyan-400/5 border border-violet-300/20">
                                <div className="rounded-2xl overflow-hidden border border-violet-300/15 bg-[#0a0a24]">
                                    {/* mockup header */}
                                    <div className="flex items-center gap-2 px-5 py-3.5 bg-black/30 border-b border-violet-300/15">
                                        <span className="w-3 h-3 rounded-full bg-red-500" />
                                        <span className="w-3 h-3 rounded-full bg-yellow-400" />
                                        <span className="w-3 h-3 rounded-full bg-green-500" />
                                        <span className="ml-3 text-[13px] font-medium text-slate-400">Wellness Dashboard</span>
                                    </div>
                                    {/* mockup body */}
                                    <div className="p-6 grid gap-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="p-4 rounded-xl border border-violet-400/25 bg-gradient-to-br from-violet-600/15 to-violet-600/5">
                                                <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Mood Score</div>
                                                <div className="font-display text-3xl font-bold text-white">8.4<span className="text-sm text-slate-500 font-normal ml-1">/10</span></div>
                                                <div className="mt-2 h-1 rounded bg-white/10 overflow-hidden">
                                                    <div className="h-full bg-gradient-to-r from-violet-400 to-cyan-400" style={{ width: '84%' }} />
                                                </div>
                                            </div>
                                            <div className="p-4 rounded-xl border border-cyan-400/25 bg-gradient-to-br from-cyan-500/15 to-cyan-500/5">
                                                <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Streak</div>
                                                <div className="font-display text-3xl font-bold text-white">12<span className="text-sm text-slate-500 font-normal ml-1">days</span></div>
                                                <div className="mt-2 flex gap-1">
                                                    {[...Array(7)].map((_, i) => (
                                                        <span key={i} className={`flex-1 h-1.5 rounded bg-cyan-400 ${i % 2 === 0 ? 'opacity-100' : 'opacity-60'}`} />
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="p-4 rounded-xl bg-black/20">
                                            <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Weekly Reflection</div>
                                            <svg viewBox="0 0 300 80" className={`w-full h-20 ${styles.chartGlow}`}>
                                                <defs>
                                                    <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="0" stopColor="#a78bfa" stopOpacity="0.5" />
                                                        <stop offset="1" stopColor="#a78bfa" stopOpacity="0" />
                                                    </linearGradient>
                                                </defs>
                                                <path d="M0,60 Q40,40 80,45 T160,30 T240,20 T300,25 L300,80 L0,80 Z" fill="url(#chartGrad)" />
                                                <path d="M0,60 Q40,40 80,45 T160,30 T240,20 T300,25" stroke="#a78bfa" strokeWidth="2" fill="none" />
                                            </svg>
                                        </div>
                                        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-cyan-400/10 border border-cyan-400/25 text-[13px] text-cyan-200">
                                            <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee]" />
                                            AI detected: improved sleep pattern
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Floating badges */}
                            <div className={`${styles.floatBadge} hidden lg:flex left-[-40px] top-[25%]`}>
                                <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-300 flex items-center justify-center">
                                    <CheckCircleIcon className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-[13px] font-semibold text-white">Wellness Score</p>
                                    <p className="text-[11px] text-emerald-300 font-medium">+12% this week</p>
                                </div>
                            </div>
                            <div className={`${styles.floatBadge} hidden lg:flex right-[-40px] top-[50%]`} style={{ animationDelay: '-3s' }}>
                                <div className="w-10 h-10 rounded-xl bg-violet-400/15 text-violet-300 flex items-center justify-center">
                                    <SparklesIcon className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-[13px] font-semibold text-white">AI Analysis</p>
                                    <p className="text-[11px] text-violet-300 font-medium">Pattern detected</p>
                                </div>
                            </div>
                        </div>
                    </Reveal>

                    {/* Scroll indicator */}
                    <div className="flex justify-center mt-12">
                        <a href="#stats" className="animate-bounce text-slate-500 hover:text-violet-300 transition-colors">
                            <ArrowDownIcon className="w-5 h-5" />
                        </a>
                    </div>
                </div>
            </section>

            {/* ══════════ STATS ══════════ */}
            <section id="stats" className="relative py-16 px-4 sm:px-6 lg:px-8">
                <div
                    className="absolute inset-0"
                    style={{ background: 'linear-gradient(90deg, transparent, rgba(124,58,237,0.08), rgba(6,182,212,0.08), transparent)' }}
                />
                <div className="max-w-7xl mx-auto relative z-10">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                        {stats.map((stat, i) => (
                            <Reveal key={i} delay={i * 100}>
                                <div className="text-center">
                                    <p className={`font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold mb-2 ${styles.gradientText}`}>
                                        <AnimatedCounter end={stat.value} suffix={stat.suffix} />
                                    </p>
                                    <p className="text-sm sm:text-base text-slate-400 font-medium">{stat.label}</p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ FEATURES ══════════ */}
            <section id="features" className="py-24 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.15em] text-violet-300 bg-violet-400/10 border border-violet-300/20 mb-5">
                                Features
                            </span>
                            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-4 tracking-tight">
                                Everything you need for{' '}
                                <span className={styles.gradientText}>mental wellness</span>
                            </h2>
                            <p className="text-lg text-slate-300 max-w-2xl mx-auto">
                                Comprehensive AI-powered tools designed to understand, support, and improve your mental health.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                        {features.map((feature, i) => (
                            <Reveal key={i} delay={i * 80}>
                                <div className={`${styles.glassCard} ${styles.glassCardGlowBorder} group p-7 h-full`}>
                                    <div className={`w-14 h-14 rounded-2xl border ${feature.ring} flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-6`}>
                                        <feature.icon className="w-7 h-7" />
                                    </div>
                                    <h3 className="font-display text-lg font-bold text-white mb-2.5">{feature.title}</h3>
                                    <p className="text-slate-300 text-[15px] leading-relaxed">{feature.description}</p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ HOW IT WORKS ══════════ */}
            <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.15em] text-violet-300 bg-violet-400/10 border border-violet-300/20 mb-5">
                                How It Works
                            </span>
                            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-4 tracking-tight">
                                Three steps to a{' '}
                                <span className={styles.gradientText}>healthier mind</span>
                            </h2>
                            <p className="text-lg text-slate-300 max-w-2xl mx-auto">
                                Getting started is simple. Our AI takes care of the rest.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-3 gap-12 relative">
                        {/* Connecting line */}
                        <div
                            className="hidden md:block absolute top-10 left-[16%] right-[16%] h-0.5"
                            style={{ background: 'linear-gradient(90deg, transparent, #a78bfa, #22d3ee, #a78bfa, transparent)' }}
                        />

                        {steps.map((item, i) => (
                            <Reveal key={i} delay={i * 150}>
                                <div className="relative text-center z-10">
                                    <div className={`${styles.stepOrb} font-display mb-6`}>{item.step}</div>
                                    <h3 className="font-display text-xl font-bold text-white mb-3">{item.title}</h3>
                                    <p className="text-slate-300 leading-relaxed max-w-xs mx-auto">{item.description}</p>
                                </div>
                            </Reveal>
                        ))}
                    </div>
                </div>
            </section>

            {/* ══════════ TESTIMONIALS ══════════ */}
            <section id="testimonials" className="py-24 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <Reveal>
                        <div className="text-center mb-16">
                            <span className="inline-block px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.15em] text-violet-300 bg-violet-400/10 border border-violet-300/20 mb-5">
                                Stories
                            </span>
                            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-4 tracking-tight">
                                Loved by thousands of{' '}
                                <span className={styles.gradientText}>users</span>
                            </h2>
                            <p className="text-lg text-slate-300 max-w-2xl mx-auto">
                                Hear from people who transformed their mental wellness with Manō.
                            </p>
                        </div>
                    </Reveal>

                    <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
                        {testimonials.map((t, i) => (
                            <Reveal key={i} delay={i * 100}>
                                <div className={`${styles.glassCard} p-7 h-full flex flex-col`}>
                                    {/* Stars */}
                                    <div className="flex gap-1 mb-4 [text-shadow:0_0_10px_rgba(245,158,11,0.4)]">
                                        {[...Array(5)].map((_, j) => (
                                            <svg key={j} className="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                            </svg>
                                        ))}
                                    </div>
                                    <p className="text-slate-200 leading-relaxed mb-6 flex-1 italic">"{t.text}"</p>
                                    <div className="flex items-center gap-3 pt-4 border-t border-violet-300/15">
                                        <div className="w-11 h-11 rounded-full bg-gradient-to-br from-violet-400 to-cyan-400 flex items-center justify-center text-white font-bold font-display">
                                            {t.avatar}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-white">{t.name}</p>
                                            <p className="text-xs text-slate-500">{t.role}</p>
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
                        <div
                            className="relative overflow-hidden rounded-[2rem] p-10 lg:p-16 text-center backdrop-blur-xl border border-violet-300/30"
                            style={{
                                background:
                                    'linear-gradient(135deg, rgba(124,58,237,0.32), rgba(236,72,153,0.22), rgba(6,182,212,0.32)), #0a0a24',
                            }}
                        >
                            <div className={`${styles.ctaOrb} ${styles.ctaOrb1}`} />
                            <div className={`${styles.ctaOrb} ${styles.ctaOrb2}`} />
                            <div className={`${styles.ctaOrb} ${styles.ctaOrb3}`} />

                            <div className="relative z-10">
                                <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-4 tracking-tight">
                                    Ready to feel better?
                                </h2>
                                <p className="text-lg text-white/85 mb-10 max-w-2xl mx-auto leading-relaxed">
                                    Join thousands who are already taking control of their mental health.
                                    Your journey starts with a single step.
                                </p>
                                <button
                                    onClick={openAuth}
                                    className="inline-flex items-center gap-3 bg-white text-violet-700 px-8 py-4 rounded-2xl text-base font-bold shadow-[0_10px_40px_rgba(255,255,255,0.2)] hover:shadow-[0_15px_50px_rgba(255,255,255,0.32)] hover:-translate-y-0.5 transition-all duration-300"
                                >
                                    Get Started — It's Free
                                    <ArrowRightIcon className="w-5 h-5" />
                                </button>
                                <p className="text-sm text-white/75 mt-6 flex items-center justify-center gap-2">
                                    <ShieldCheckIcon className="w-4 h-4" />
                                    No credit card required — 100% free to use
                                </p>
                            </div>
                        </div>
                    </Reveal>
                </div>
            </section>

            {/* ══════════ FOOTER ══════════ */}
            <footer className="relative bg-black/40 backdrop-blur-xl border-t border-violet-300/15 mt-10 pb-16">
                {/* Top gradient strip */}
                <div className="h-[2px] bg-gradient-to-r from-violet-600 via-pink-500 to-cyan-500" />

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16">
                    <div className="grid md:grid-cols-4 gap-12 mb-12">
                        {/* Brand */}
                        <div className="md:col-span-2">
                            <div className="flex items-center gap-3 mb-5">
                                <img src={logoImg} alt="Manō" className="w-11 h-11 rounded-xl object-cover" />
                                <div>
                                    <span className="font-display text-xl font-extrabold text-white">Manō</span>
                                    <p className="text-xs text-slate-500 -mt-0.5">Mental Wellness Platform</p>
                                </div>
                            </div>
                            <p className="text-slate-400 leading-relaxed max-w-sm mb-6">
                                AI-powered mental wellness support designed to help you understand your mind,
                                build resilience, and connect with others on similar journeys.
                            </p>
                            <div className="flex gap-3">
                                {['T', 'G', 'L'].map((s, i) => (
                                    <button
                                        key={i}
                                        className="w-9 h-9 rounded-lg bg-violet-400/10 border border-violet-300/20 text-slate-400 hover:bg-violet-600 hover:text-white hover:-translate-y-0.5 transition-all duration-300"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Links */}
                        <div>
                            <h4 className="text-[13px] font-semibold text-white uppercase tracking-wider mb-4">Platform</h4>
                            <ul className="space-y-3">
                                {['Features', 'How It Works', 'Community', 'Pricing'].map(link => (
                                    <li key={link}>
                                        <button onClick={link === 'Pricing' ? openAuth : undefined} className="text-sm text-slate-400 hover:text-violet-300 transition-colors">
                                            {link}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-[13px] font-semibold text-white uppercase tracking-wider mb-4">Support</h4>
                            <ul className="space-y-3">
                                {['Help Center', 'Privacy Policy', 'Terms of Service', 'Contact Us'].map(link => (
                                    <li key={link}>
                                        <button className="text-sm text-slate-400 hover:text-violet-300 transition-colors">
                                            {link}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Bottom bar */}
                    <div className="pt-8 border-t border-violet-300/15 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <p className="text-sm text-slate-500">
                            &copy; {new Date().getFullYear()} Manō. All rights reserved.
                        </p>
                        <p className="text-sm text-slate-500 flex items-center gap-1.5">
                            Built with <HeartIcon className="w-4 h-4 text-pink-400" /> for mental wellness
                        </p>
                    </div>
                </div>
            </footer>

            {/* ══════════ CRISIS BANNER ══════════ */}
            <div className="fixed bottom-0 left-0 right-0 z-50 bg-gradient-to-r from-red-900 via-red-700 to-red-900 text-white py-2.5 px-4 text-center text-sm shadow-[0_-4px_20px_rgba(220,38,38,0.4)]">
                <span>If you're in crisis, call </span>
                <a href="tel:988" className="font-bold underline decoration-2 underline-offset-2 hover:text-red-100 transition-colors">988</a>
                <span> (Suicide &amp; Crisis Lifeline) or text HOME to </span>
                <a href="sms:741741" className="font-bold underline decoration-2 underline-offset-2 hover:text-red-100 transition-colors">741741</a>
            </div>
        </div>
    );
}

export default Landing;
