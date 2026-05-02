import { useState, useEffect, useCallback, useRef } from 'react';

// ─── localStorage helpers ────────────────────────────────────────────────────
const STORAGE_KEY = 'mano_games';
function loadGameData() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
}
function saveGameData(data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// ─── Breathing Bubble ────────────────────────────────────────────────────────
function BreathingBubble({ onBack }) {
    const phases = [
        { label: 'Breathe In', duration: 4000, scale: 1.6, color: 'from-sage-light to-sage' },
        { label: 'Hold', duration: 4000, scale: 1.6, color: 'from-sage to-sage-dark' },
        { label: 'Breathe Out', duration: 6000, scale: 1, color: 'from-terracotta-light to-terracotta' },
        { label: 'Hold', duration: 2000, scale: 1, color: 'from-terracotta to-terracotta-light' },
    ];
    const [running, setRunning] = useState(false);
    const [phaseIdx, setPhaseIdx] = useState(0);
    const [cycles, setCycles] = useState(0);
    const [totalCycles, setTotalCycles] = useState(0);
    const timerRef = useRef(null);

    useEffect(() => {
        const d = loadGameData();
        setTotalCycles(d.breathingCycles || 0);
    }, []);

    useEffect(() => {
        if (!running) return;
        timerRef.current = setTimeout(() => {
            const next = (phaseIdx + 1) % phases.length;
            setPhaseIdx(next);
            if (next === 0) {
                const newCycles = cycles + 1;
                setCycles(newCycles);
                const d = loadGameData();
                d.breathingCycles = (d.breathingCycles || 0) + 1;
                saveGameData(d);
                setTotalCycles(d.breathingCycles);
            }
        }, phases[phaseIdx].duration);
        return () => clearTimeout(timerRef.current);
    }, [running, phaseIdx, cycles]);

    const toggle = () => {
        if (running) { clearTimeout(timerRef.current); setRunning(false); }
        else { setPhaseIdx(0); setCycles(0); setRunning(true); }
    };

    const phase = phases[phaseIdx];

    return (
        <div className="flex flex-col items-center gap-8 py-8 animate-fade-in">
            <button onClick={onBack} className="self-start text-sm text-terracotta hover:text-terracotta-dark transition-colors font-medium">
                &larr; Back to Games
            </button>
            <h2 className="text-2xl font-bold text-terracotta-dark font-display">Breathing Bubble</h2>
            <p className="text-neutral-500 text-center max-w-md">Follow the bubble. Breathe in as it grows, breathe out as it shrinks.</p>

            {/* Bubble */}
            <div className="relative flex items-center justify-center w-64 h-64">
                <div
                    className={`absolute inset-0 rounded-full bg-gradient-to-br ${phase.color} opacity-20 blur-2xl`}
                    style={{ transform: `scale(${running ? phase.scale : 1})`, transition: `transform ${phase.duration}ms ease-in-out` }}
                />
                <div
                    className={`w-40 h-40 rounded-full bg-gradient-to-br ${phase.color} shadow-organic-lg flex items-center justify-center`}
                    style={{ transform: `scale(${running ? phase.scale : 1})`, transition: `transform ${phase.duration}ms ease-in-out` }}
                >
                    <span className="text-white font-bold text-lg font-display">
                        {running ? phase.label : 'Ready'}
                    </span>
                </div>
            </div>

            <button
                onClick={toggle}
                className="px-8 py-3 rounded-2xl font-semibold text-white bg-gradient-to-r from-terracotta to-terracotta-light shadow-organic hover:shadow-organic-hover transition-all"
            >
                {running ? 'Stop' : 'Start Breathing'}
            </button>

            <div className="flex gap-6 text-sm text-neutral-500">
                <span>This session: <strong className="text-terracotta-dark">{cycles}</strong> cycles</span>
                <span>All time: <strong className="text-terracotta-dark">{totalCycles}</strong> cycles</span>
            </div>
        </div>
    );
}

// ─── Memory Match ────────────────────────────────────────────────────────────
const CARD_EMOJIS = ['🌸', '🌿', '🦋', '🌙', '☀️', '🌊', '🍃', '🌺'];

function shuffleArray(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

function MemoryMatch({ onBack }) {
    const [cards, setCards] = useState([]);
    const [flipped, setFlipped] = useState([]);
    const [matched, setMatched] = useState([]);
    const [moves, setMoves] = useState(0);
    const [bestScore, setBestScore] = useState(null);
    const [gameWon, setGameWon] = useState(false);
    const lockRef = useRef(false);

    const initGame = useCallback(() => {
        const deck = shuffleArray([...CARD_EMOJIS, ...CARD_EMOJIS]).map((emoji, i) => ({ id: i, emoji }));
        setCards(deck);
        setFlipped([]);
        setMatched([]);
        setMoves(0);
        setGameWon(false);
        lockRef.current = false;
    }, []);

    useEffect(() => {
        initGame();
        const d = loadGameData();
        setBestScore(d.memoryBest || null);
    }, [initGame]);

    const handleFlip = (id) => {
        if (lockRef.current) return;
        if (flipped.includes(id) || matched.includes(id)) return;

        const newFlipped = [...flipped, id];
        setFlipped(newFlipped);

        if (newFlipped.length === 2) {
            lockRef.current = true;
            setMoves((m) => m + 1);
            const [a, b] = newFlipped;
            if (cards[a].emoji === cards[b].emoji) {
                const newMatched = [...matched, a, b];
                setMatched(newMatched);
                setFlipped([]);
                lockRef.current = false;
                if (newMatched.length === cards.length) {
                    const finalMoves = moves + 1;
                    setGameWon(true);
                    const d = loadGameData();
                    if (!d.memoryBest || finalMoves < d.memoryBest) {
                        d.memoryBest = finalMoves;
                        saveGameData(d);
                        setBestScore(finalMoves);
                    }
                }
            } else {
                setTimeout(() => { setFlipped([]); lockRef.current = false; }, 800);
            }
        }
    };

    return (
        <div className="flex flex-col items-center gap-6 py-8 animate-fade-in">
            <button onClick={onBack} className="self-start text-sm text-terracotta hover:text-terracotta-dark transition-colors font-medium">
                &larr; Back to Games
            </button>
            <h2 className="text-2xl font-bold text-terracotta-dark font-display">Memory Match</h2>
            <p className="text-neutral-500">Flip cards to find matching pairs. Train your focus!</p>

            <div className="flex gap-6 text-sm text-neutral-500">
                <span>Moves: <strong className="text-terracotta-dark">{moves}</strong></span>
                {bestScore && <span>Best: <strong className="text-sage-dark">{bestScore}</strong></span>}
            </div>

            {/* Card Grid */}
            <div className="grid grid-cols-4 gap-3 max-w-xs">
                {cards.map((card) => {
                    const isFlipped = flipped.includes(card.id) || matched.includes(card.id);
                    const isMatched = matched.includes(card.id);
                    return (
                        <button
                            key={card.id}
                            onClick={() => handleFlip(card.id)}
                            className={`w-16 h-16 sm:w-18 sm:h-18 rounded-2xl text-2xl font-bold transition-all duration-300 shadow-organic
                                ${isMatched ? 'bg-mint/40 border-2 border-sage-light/60 scale-95' :
                                  isFlipped ? 'bg-cream border-2 border-terracotta-light/40 rotate-0' :
                                  'bg-white border-2 border-sand/40 hover:shadow-organic-hover hover:border-terracotta-light/30 cursor-pointer'}`}
                        >
                            {isFlipped ? card.emoji : '?'}
                        </button>
                    );
                })}
            </div>

            {gameWon && (
                <div className="text-center space-y-3 animate-bounce-in">
                    <p className="text-xl font-bold text-sage-dark">🎉 You matched them all!</p>
                    <p className="text-sm text-neutral-500">Completed in <strong>{moves}</strong> moves</p>
                    <button
                        onClick={initGame}
                        className="px-6 py-2 rounded-2xl font-semibold text-white bg-gradient-to-r from-terracotta to-terracotta-light shadow-organic hover:shadow-organic-hover transition-all"
                    >
                        Play Again
                    </button>
                </div>
            )}

            {!gameWon && (
                <button
                    onClick={initGame}
                    className="text-sm text-terracotta hover:text-terracotta-dark font-medium transition-colors"
                >
                    Restart Game
                </button>
            )}
        </div>
    );
}

// ─── Gratitude Garden ────────────────────────────────────────────────────────
const FLOWERS = ['🌸', '🌺', '🌻', '🌷', '🌹', '🌼', '💐', '🪻', '🌱', '🌿', '🍀', '🌾'];

function GratitudeGarden({ onBack }) {
    const [entries, setEntries] = useState([]);
    const [text, setText] = useState('');
    const inputRef = useRef(null);

    useEffect(() => {
        const d = loadGameData();
        setEntries(d.gardenEntries || []);
    }, []);

    const addEntry = () => {
        if (!text.trim()) return;
        const flower = FLOWERS[Math.floor(Math.random() * FLOWERS.length)];
        const newEntry = { id: Date.now(), text: text.trim(), flower, date: new Date().toLocaleDateString() };
        const updated = [newEntry, ...entries];
        setEntries(updated);
        const d = loadGameData();
        d.gardenEntries = updated;
        saveGameData(d);
        setText('');
        inputRef.current?.focus();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addEntry(); }
    };

    return (
        <div className="flex flex-col items-center gap-6 py-8 animate-fade-in">
            <button onClick={onBack} className="self-start text-sm text-terracotta hover:text-terracotta-dark transition-colors font-medium">
                &larr; Back to Games
            </button>
            <h2 className="text-2xl font-bold text-terracotta-dark font-display">Gratitude Garden</h2>
            <p className="text-neutral-500 text-center max-w-md">Plant a flower for each thing you're grateful for. Watch your garden grow!</p>

            {/* Input */}
            <div className="w-full max-w-md flex gap-2">
                <input
                    ref={inputRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="I'm grateful for..."
                    className="flex-1 px-4 py-3 rounded-2xl border border-sand/40 bg-white focus:ring-2 focus:ring-peach/50 focus:border-terracotta-light outline-none transition-all text-sm"
                />
                <button
                    onClick={addEntry}
                    disabled={!text.trim()}
                    className="px-5 py-3 rounded-2xl font-semibold text-white bg-gradient-to-r from-sage to-sage-dark shadow-organic hover:shadow-organic-hover transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    Plant
                </button>
            </div>

            {/* Garden View */}
            {entries.length > 0 && (
                <div className="w-full max-w-lg">
                    <div className="flex items-center justify-between mb-3">
                        <p className="text-sm text-terracotta font-medium font-hand text-lg">{entries.length} flower{entries.length !== 1 ? 's' : ''} planted</p>
                    </div>
                    <div className="bg-gradient-to-br from-cream/60 to-mint/20 rounded-3xl border border-sand/30 p-4 shadow-organic">
                        {/* Flower grid */}
                        <div className="flex flex-wrap gap-2 mb-4 justify-center">
                            {entries.map((e, i) => (
                                <span
                                    key={e.id}
                                    className="text-3xl cursor-default hover:scale-125 transition-transform"
                                    title={e.text}
                                    style={{ animationDelay: `${i * 50}ms` }}
                                >
                                    {e.flower}
                                </span>
                            ))}
                        </div>
                        {/* Entry list */}
                        <div className="space-y-2 max-h-60 overflow-y-auto">
                            {entries.map((e) => (
                                <div key={e.id} className="flex items-start gap-2 p-2 rounded-xl hover:bg-white/60 transition-colors">
                                    <span className="text-xl flex-shrink-0">{e.flower}</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-neutral-700">{e.text}</p>
                                        <p className="text-xs text-neutral-400">{e.date}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {entries.length === 0 && (
                <div className="text-center py-12">
                    <span className="text-6xl block mb-4">🌱</span>
                    <p className="text-neutral-400 font-hand text-lg">Your garden is waiting for its first flower...</p>
                </div>
            )}
        </div>
    );
}

// ─── Main Games Hub ──────────────────────────────────────────────────────────
function Games() {
    const [activeGame, setActiveGame] = useState(null);

    if (activeGame === 'breathing') return <BreathingBubble onBack={() => setActiveGame(null)} />;
    if (activeGame === 'memory') return <MemoryMatch onBack={() => setActiveGame(null)} />;
    if (activeGame === 'garden') return <GratitudeGarden onBack={() => setActiveGame(null)} />;

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Page Header */}
            <div className="text-center">
                <h1 className="text-3xl font-bold font-display text-organic-gradient doodle-underline inline-block">
                    Mindful Games
                </h1>
                <p className="mt-3 text-neutral-500 font-hand text-xl">
                    Play, breathe, and grow your inner garden
                </p>
            </div>

            {/* Games Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Breathing Bubble */}
                <button
                    onClick={() => setActiveGame('breathing')}
                    className="soft-card text-center cursor-pointer group text-left"
                >
                    <div className="text-5xl mb-4 group-hover:animate-breathe inline-block">🫧</div>
                    <h3 className="text-lg font-semibold text-terracotta-dark mb-2">Breathing Bubble</h3>
                    <p className="text-sm text-neutral-500">
                        Follow the bubble to calm your breathing with guided inhale-hold-exhale cycles.
                    </p>
                    <span className="tag tag-sage mt-3 inline-flex">Relaxation</span>
                </button>

                {/* Memory Match */}
                <button
                    onClick={() => setActiveGame('memory')}
                    className="soft-card text-center cursor-pointer group text-left"
                >
                    <div className="text-5xl mb-4 group-hover:animate-wobble inline-block">🧠</div>
                    <h3 className="text-lg font-semibold text-terracotta-dark mb-2">Memory Match</h3>
                    <p className="text-sm text-neutral-500">
                        Flip cards, find matching pairs, and sharpen your focus and memory.
                    </p>
                    <span className="tag tag-lavender mt-3 inline-flex">Focus</span>
                </button>

                {/* Gratitude Garden */}
                <button
                    onClick={() => setActiveGame('garden')}
                    className="soft-card text-center cursor-pointer group text-left"
                >
                    <div className="text-5xl mb-4 group-hover:animate-sway inline-block">🌻</div>
                    <h3 className="text-lg font-semibold text-terracotta-dark mb-2">Gratitude Garden</h3>
                    <p className="text-sm text-neutral-500">
                        Plant flowers by writing things you're grateful for. Watch your garden bloom!
                    </p>
                    <span className="tag tag-terracotta mt-3 inline-flex">Gratitude</span>
                </button>
            </div>

            {/* Stats bar */}
            <div className="flex justify-center gap-8 text-sm text-neutral-400">
                <span>🫧 Breathing cycles: <strong className="text-terracotta">{loadGameData().breathingCycles || 0}</strong></span>
                <span>🧠 Memory best: <strong className="text-terracotta">{loadGameData().memoryBest || '—'}</strong> moves</span>
                <span>🌻 Flowers planted: <strong className="text-terracotta">{(loadGameData().gardenEntries || []).length}</strong></span>
            </div>
        </div>
    );
}

export default Games;
