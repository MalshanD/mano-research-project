"""CBT Thought Journal Service — CRUD + ML analysis for journal entries.

Handles:
- Creating journal entries with automatic CBT distortion analysis
- Retrieving entries by date range
- Distortion trend analytics (frequency, severity over time)
- User feedback on reframes
- Integration with user's current assessment scores for context-aware analysis
"""

from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from model.journal_entry import JournalEntry
from model.response import Response
from model.mood_checkin import MoodCheckIn
from lib.CBT.cbt_predictor import analyze_journal_text, get_distortion_catalog


class JournalService:
    """Service for CBT thought journal with ML distortion detection."""

    # ── Create / Analyze ─────────────────────────────────────────────────────

    @staticmethod
    def create_entry(db: Session, user_id: int, entry_text: str, entry_date: date = None):
        """Create a journal entry and analyze it for cognitive distortions."""
        if entry_date is None:
            entry_date = date.today()

        # Get user's latest assessment scores for context-aware analysis
        stress, anxiety, depression = _get_user_scores(db, user_id)

        # Run ML distortion analysis
        analysis = analyze_journal_text(
            text=entry_text,
            stress_score=stress,
            anxiety_score=anxiety,
            depression_score=depression,
        )

        # Create and persist the entry
        entry = JournalEntry(
            user_id=user_id,
            entry_text=entry_text,
            entry_date=entry_date,
            distortion_type=analysis["distortion_type"],
            distortion_label=analysis["label"],
            confidence=analysis["confidence"],
            severity=analysis["severity"],
            condition_context=analysis["condition_context"],
            reframe_suggestion=analysis["reframe_suggestion"],
            cbt_explanation=analysis["cbt_explanation"],
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return {
            "entry": _serialize_entry(entry),
            "analysis": analysis,
        }

    @staticmethod
    def analyze_text_only(db: Session, user_id: int, text: str):
        """Analyze text without saving — for live preview while typing."""
        stress, anxiety, depression = _get_user_scores(db, user_id)
        return analyze_journal_text(
            text=text,
            stress_score=stress,
            anxiety_score=anxiety,
            depression_score=depression,
        )

    # ── Read ─────────────────────────────────────────────────────────────────

    @staticmethod
    def get_entries(db: Session, user_id: int, days: int = 30, limit: int = 50):
        """Get user's journal entries for the last N days."""
        since = date.today() - timedelta(days=days)
        entries = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.user_id == user_id,
                JournalEntry.entry_date >= since,
            )
            .order_by(desc(JournalEntry.created_at))
            .limit(limit)
            .all()
        )
        return [_serialize_entry(e) for e in entries]

    @staticmethod
    def get_entry(db: Session, entry_id: int, user_id: int):
        """Get a single journal entry by ID."""
        entry = (
            db.query(JournalEntry)
            .filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
            .first()
        )
        if not entry:
            return None
        return _serialize_entry(entry)

    @staticmethod
    def get_entries_by_date(db: Session, user_id: int, target_date: date):
        """Get all entries for a specific date."""
        entries = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.user_id == user_id,
                JournalEntry.entry_date == target_date,
            )
            .order_by(JournalEntry.created_at.asc())
            .all()
        )
        return [_serialize_entry(e) for e in entries]

    # ── Feedback ─────────────────────────────────────────────────────────────

    @staticmethod
    def rate_reframe(db: Session, entry_id: int, user_id: int, found_helpful: bool):
        """User rates whether the reframe suggestion was helpful."""
        entry = (
            db.query(JournalEntry)
            .filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
            .first()
        )
        if not entry:
            return None
        entry.user_found_helpful = found_helpful
        db.commit()
        return {"entry_id": entry_id, "user_found_helpful": found_helpful}

    # ── Analytics / Trends ───────────────────────────────────────────────────

    @staticmethod
    def get_distortion_trends(db: Session, user_id: int, days: int = 30):
        """Get distortion frequency and severity trends over time."""
        since = date.today() - timedelta(days=days)

        entries = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.user_id == user_id,
                JournalEntry.entry_date >= since,
                JournalEntry.distortion_type.isnot(None),
            )
            .all()
        )

        if not entries:
            return {
                "total_entries": 0,
                "distortion_frequency": {},
                "daily_severity": [],
                "top_distortion": None,
                "avg_severity": 0,
                "balanced_ratio": 0,
                "insights": [],
            }

        # Frequency count per distortion type
        freq = {}
        for e in entries:
            dt = e.distortion_type
            freq[dt] = freq.get(dt, 0) + 1

        # Daily severity trend
        daily = {}
        for e in entries:
            d = e.entry_date.isoformat()
            if d not in daily:
                daily[d] = {"date": d, "entries": 0, "total_severity": 0, "distortions_found": 0}
            daily[d]["entries"] += 1
            daily[d]["total_severity"] += (e.severity or 0)
            if e.distortion_type != "none":
                daily[d]["distortions_found"] += 1

        daily_list = sorted(daily.values(), key=lambda x: x["date"])
        for d in daily_list:
            d["avg_severity"] = round(d["total_severity"] / d["entries"], 2) if d["entries"] else 0

        # Top distortion (excluding "none")
        distorted_freq = {k: v for k, v in freq.items() if k != "none"}
        top_distortion = max(distorted_freq, key=distorted_freq.get) if distorted_freq else None

        # Balanced ratio
        total = len(entries)
        balanced_count = freq.get("none", 0)
        balanced_ratio = round(balanced_count / total, 2) if total else 0

        # Average severity (excluding balanced entries)
        distorted_entries = [e for e in entries if e.distortion_type != "none"]
        avg_severity = round(
            sum(e.severity or 0 for e in distorted_entries) / len(distorted_entries), 2
        ) if distorted_entries else 0

        # Generate insights
        insights = _generate_trend_insights(freq, total, balanced_ratio, avg_severity, top_distortion, days)

        return {
            "total_entries": total,
            "distortion_frequency": freq,
            "daily_severity": daily_list,
            "top_distortion": top_distortion,
            "avg_severity": avg_severity,
            "balanced_ratio": balanced_ratio,
            "insights": insights,
            "period_days": days,
        }

    @staticmethod
    def get_catalog():
        """Return the full distortion catalog for the frontend."""
        return get_distortion_catalog()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_scores(db: Session, user_id: int):
    """Get user's latest assessment scores. Returns (stress, anxiety, depression)."""
    last_response = (
        db.query(Response)
        .filter(Response.user_id == user_id)
        .order_by(Response.id.desc())
        .first()
    )
    if last_response:
        return (
            last_response.stress_score or 50,
            last_response.anxiety_score or 50,
            last_response.depression_score or 50,
        )

    # Fallback: infer from recent mood checkins
    recent_moods = (
        db.query(MoodCheckIn.mood)
        .filter(MoodCheckIn.user_id == user_id)
        .order_by(MoodCheckIn.checkin_date.desc())
        .limit(7)
        .all()
    )
    if recent_moods:
        mood_map = {"great": 10, "good": 30, "okay": 50, "low": 70, "bad": 90}
        avg = sum(mood_map.get(m.mood.value if hasattr(m.mood, 'value') else m.mood, 50) for m in recent_moods) / len(recent_moods)
        return (avg, avg, avg)

    return (50, 50, 50)  # Default neutral


def _serialize_entry(entry: JournalEntry) -> dict:
    """Serialize a JournalEntry to API response dict."""
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "entry_text": entry.entry_text,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "distortion_type": entry.distortion_type,
        "distortion_label": entry.distortion_label,
        "confidence": entry.confidence,
        "severity": entry.severity,
        "severity_label": _severity_label(entry.severity),
        "condition_context": entry.condition_context,
        "reframe_suggestion": entry.reframe_suggestion,
        "cbt_explanation": entry.cbt_explanation,
        "user_found_helpful": entry.user_found_helpful,
        "is_distorted": entry.distortion_type != "none" if entry.distortion_type else False,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def _severity_label(severity):
    if severity is None:
        return "unknown"
    if severity < 0.5:
        return "balanced"
    elif severity < 1.5:
        return "mild"
    elif severity < 2.5:
        return "moderate"
    else:
        return "severe"


def _generate_trend_insights(freq, total, balanced_ratio, avg_severity, top_distortion, days):
    """Generate personalized insights from distortion trends."""
    insights = []

    # Positive: high balanced ratio
    if balanced_ratio >= 0.7:
        insights.append({
            "type": "positive",
            "icon": "check_circle",
            "text": f"Great work! {int(balanced_ratio * 100)}% of your journal entries show balanced thinking.",
        })
    elif balanced_ratio >= 0.4:
        insights.append({
            "type": "encouragement",
            "icon": "trending_up",
            "text": f"{int(balanced_ratio * 100)}% of your entries show balanced thinking. You're building awareness!",
        })

    # Top distortion pattern
    if top_distortion:
        catalog = get_distortion_catalog()
        label = catalog.get(top_distortion, {}).get("label", top_distortion)
        count = freq.get(top_distortion, 0)
        insights.append({
            "type": "pattern",
            "icon": "psychology",
            "text": f"Your most common thinking pattern is {label} ({count} times in {days} days). Recognizing this is the first step to change.",
        })

    # Severity trend
    if avg_severity >= 2.0:
        insights.append({
            "type": "support",
            "icon": "favorite",
            "text": "Your entries show some strong emotions. Remember, writing about them is already a healthy coping strategy.",
        })
    elif avg_severity >= 1.0:
        insights.append({
            "type": "awareness",
            "icon": "lightbulb",
            "text": "You're experiencing moderate distortions. The reframes provided can help challenge these thought patterns.",
        })

    # Journaling consistency
    if total >= days * 0.7:
        insights.append({
            "type": "celebration",
            "icon": "emoji_events",
            "text": f"You've journaled {total} times in {days} days — amazing consistency!",
        })
    elif total >= 3:
        insights.append({
            "type": "nudge",
            "icon": "edit_note",
            "text": f"You've written {total} entries. Try to journal daily — even a few sentences helps build self-awareness.",
        })

    return insights[:5]  # Max 5 insights
