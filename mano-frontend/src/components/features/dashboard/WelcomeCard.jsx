import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { cn } from '../../../utils/helpers';
import { Button } from '../../common';
import {
    SunIcon,
    MoonIcon,
    SparklesIcon,
    ArrowRightIcon,
} from '@heroicons/react/24/outline';

function WelcomeCard({ user, className }) {
    const hour = new Date().getHours();

    const getGreeting = () => {
        if (hour < 12) return { text: 'Good morning', emoji: '\u2600\uFE0F', icon: SunIcon, gradient: 'from-amber-400 to-orange-500' };
        if (hour < 18) return { text: 'Good afternoon', emoji: '\uD83C\uDF3B', icon: SunIcon, gradient: 'from-blue-400 to-cyan-500' };
        return { text: 'Good evening', emoji: '\uD83C\uDF19', icon: MoonIcon, gradient: 'from-indigo-500 to-purple-600' };
    };

    const greeting = getGreeting();
    const GreetingIcon = greeting.icon;

    return (
        <div
            className={cn(
                'relative overflow-hidden rounded-3xl p-6 lg:p-8 text-white bg-cover bg-center',
                className
            )}
            style={{ backgroundImage: 'url("/demo.jpg")' }}
        >
            {/* Organic overlay for better readability */}
            <div className="absolute inset-0 bg-gradient-to-r from-terracotta-dark/40 to-transparent rounded-3xl" />

            <div className="relative">
                <div className="flex items-start justify-between">
                    <div>
                        <div className="flex items-center gap-2 text-white/90 mb-2">
                            <span className="text-xl">{greeting.emoji}</span>
                            <span className="text-sm font-medium">{greeting.text}</span>
                        </div>
                        <h1 className="text-2xl lg:text-3xl font-bold font-display text-white mb-2 drop-shadow-sm">
                            {user?.firstName || user?.guest_name || user?.username || 'Friend'}! {'\uD83D\uDC4B'}
                        </h1>
                        <p className="text-white/90 max-w-md font-hand text-lg">
                            {format(new Date(), 'EEEE, MMMM d, yyyy')}
                        </p>
                    </div>

                    <div className="hidden lg:flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-2xl px-4 py-2 border border-white/10">
                        <span className="text-lg">{'\u2728'}</span>
                        <span className="text-sm font-medium">Day {user?.streak || 1} Streak</span>
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="flex flex-wrap items-center gap-3 mt-6">
                    <Button
                        as={Link}
                        to="/chat"
                        variant="secondary"
                        className="bg-white/20 backdrop-blur-sm text-white border-white/30 hover:bg-white/30 shadow-sm rounded-2xl"
                    >
                        {'\uD83D\uDCAC'} Start a Chat
                    </Button>
                    <Button
                        as={Link}
                        to="/assessments"
                        variant="ghost"
                        className="text-white hover:bg-white/10 drop-shadow-sm rounded-2xl"
                        rightIcon={<ArrowRightIcon className="w-4 h-4" />}
                    >
                        Take Assessment
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default WelcomeCard;