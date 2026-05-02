import { useState, useRef } from 'react';
import { MusicalNoteIcon, PlayCircleIcon, PauseCircleIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle } from '../../common';

function AmbientAudioWidget({ ambient }) {
    const [playingId, setPlayingId] = useState(null);
    const audioRefs = useRef({});

    if (!ambient || !ambient.tracks || ambient.tracks.length === 0) {
        return null;
    }

    const togglePlay = (trackId) => {
        const audioEl = audioRefs.current[trackId];
        if (!audioEl) return;

        if (playingId === trackId) {
            audioEl.pause();
            setPlayingId(null);
        } else {
            // Pause currently playing if any
            if (playingId && audioRefs.current[playingId]) {
                audioRefs.current[playingId].pause();
            }
            audioEl.play().catch(e => console.error("Audio playback error:", e));
            setPlayingId(trackId);
        }
    };

    return (
        <Card className="bg-gradient-to-br from-indigo-50 to-purple-50/50 border-indigo-100">
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm text-indigo-900">
                    <MusicalNoteIcon className="w-5 h-5 text-indigo-500" />
                    Recommended Soundscape
                </CardTitle>
            </CardHeader>
            <div className="px-4 pb-4 space-y-3">
                <p className="text-xs text-indigo-600/80 italic font-hand text-base mb-2">
                    Curated for your current mood ({ambient.mood})
                </p>
                {ambient.tracks.slice(0, 3).map(track => (
                    <div key={track.id} className="flex items-center justify-between p-2 rounded-xl bg-white/60 border border-white hover:bg-white transition-colors">
                        <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-medium text-indigo-950 truncate">{track.title}</span>
                            <span className="text-xs text-indigo-500/80">
                                {track.provider} {track.duration_seconds ? `• ${Math.round(track.duration_seconds)}s` : ''}
                            </span>
                        </div>
                        <button
                            onClick={() => togglePlay(track.id)}
                            className="p-1 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-full transition-colors flex-shrink-0 ml-2"
                        >
                            {playingId === track.id ? (
                                <PauseCircleIcon className="w-8 h-8" />
                            ) : (
                                <PlayCircleIcon className="w-8 h-8" />
                            )}
                        </button>
                        <audio
                            ref={el => audioRefs.current[track.id] = el}
                            src={track.preview_url}
                            onEnded={() => setPlayingId(null)}
                            loop
                        />
                    </div>
                ))}
            </div>
        </Card>
    );
}

export default AmbientAudioWidget;
