"""Weekly Wellness Summary — aggregates mood, activities, streaks, and feedback
into a single snapshot for the user."""

from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from model.mood_checkin import MoodCheckIn, MoodType
from model.user_activity_log import UserActivityLog
from model.activity_feedback import ActivityFeedback
from model.post import Post
from model.achievement import Achievement
from model.journal_entry import JournalEntry


# Mood → numeric value for scoring
MOOD_SCORES = {
    MoodType.great: 5,
    MoodType.good: 4,
    MoodType.okay: 3,
    MoodType.low: 2,
    MoodType.bad: 1,
}

MOOD_EMOJIS = {
    "great": "😄",
    "good": "🙂",
    "okay": "😐",
    "low": "😔",
    "bad": "😢",
}


class WellnessService:

    @staticmethod
    def get_weekly_summary(db: Session, user_id: int):
        """Build a full weekly wellness summary for a user.
        Covers the last 7 completed days (not including today, to ensure full data)."""

        today = date.today()
        week_start = today - timedelta(days=7)
        prev_week_start = week_start - timedelta(days=7)

        summary = {
            "user_id": user_id,
            "period": {
                "start": str(week_start),
                "end": str(today - timedelta(days=1)),
            },
            "mood": WellnessService._mood_summary(db, user_id, week_start, today),
            "mood_previous": WellnessService._mood_summary(db, user_id, prev_week_start, week_start),
            "engagement": WellnessService._engagement_summary(db, user_id, week_start, today),
            "engagement_previous": WellnessService._engagement_summary(db, user_id, prev_week_start, week_start),
            "feedback": WellnessService._feedback_summary(db, user_id, week_start, today),
            "journal": WellnessService._journal_summary(db, user_id, week_start, today),
            "badges_earned": WellnessService._badges_earned(db, user_id, week_start, today),
            "generated_at": datetime.now().isoformat(),
        }

        # Compute an overall wellness score (0-100) from weighted factors
        summary["wellness_score"] = WellnessService._compute_wellness_score(summary)

        # Compute week-over-week deltas
        summary["deltas"] = WellnessService._compute_deltas(summary)

        # Generate personalized insights
        summary["insights"] = WellnessService._generate_insights(summary)

        return summary

    # ── Mood ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _mood_summary(db: Session, user_id: int, start: date, end: date):
        checkins = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date >= start,
            MoodCheckIn.checkin_date < end,
        ).order_by(MoodCheckIn.checkin_date.asc()).all()

        if not checkins:
            return {
                "checkin_count": 0,
                "avg_score": 0,
                "distribution": {},
                "trend": [],
                "best_day": None,
                "dominant_mood": None,
            }

        scores = [MOOD_SCORES.get(c.mood, 3) for c in checkins]
        avg_score = round(sum(scores) / len(scores), 2)

        # Distribution
        dist = {}
        for c in checkins:
            mood_val = c.mood.value if hasattr(c.mood, "value") else c.mood
            dist[mood_val] = dist.get(mood_val, 0) + 1

        # Daily trend
        trend = [
            {"date": str(c.checkin_date), "mood": c.mood.value, "score": MOOD_SCORES.get(c.mood, 3)}
            for c in checkins
        ]

        # Best day
        best = max(checkins, key=lambda c: MOOD_SCORES.get(c.mood, 3))
        best_day = {"date": str(best.checkin_date), "mood": best.mood.value}

        # Dominant mood
        dominant = max(dist, key=dist.get) if dist else None

        return {
            "checkin_count": len(checkins),
            "avg_score": avg_score,
            "distribution": dist,
            "trend": trend,
            "best_day": best_day,
            "dominant_mood": dominant,
        }

    # ── Engagement ────────────────────────────────────────────────────────────

    @staticmethod
    def _engagement_summary(db: Session, user_id: int, start: date, end: date):
        logs = db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date >= start,
            UserActivityLog.log_date < end,
        ).all()

        activities_completed = sum(l.activities_completed for l in logs)
        posts_created = sum(l.posts_created for l in logs)
        mood_days = sum(1 for l in logs if l.mood_checked_in)
        active_days = len(logs)

        # Posts this week from post table (more reliable than log)
        post_count = db.query(func.count(Post.id)).filter(
            Post.user_id == user_id,
            Post.created_at >= datetime.combine(start, datetime.min.time()),
            Post.created_at < datetime.combine(end, datetime.min.time()),
        ).scalar() or 0

        return {
            "active_days": active_days,
            "activities_completed": activities_completed,
            "posts_created": max(posts_created, post_count),
            "mood_checkin_days": mood_days,
        }

    # ── Feedback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _feedback_summary(db: Session, user_id: int, start: date, end: date):
        feedbacks = db.query(ActivityFeedback).filter(
            ActivityFeedback.user_id == user_id,
            ActivityFeedback.created_at >= datetime.combine(start, datetime.min.time()),
            ActivityFeedback.created_at < datetime.combine(end, datetime.min.time()),
        ).all()

        if not feedbacks:
            return {"count": 0, "avg_effectiveness": 0, "avg_mood_change": 0}

        avg_eff = round(sum(f.effectiveness_rating for f in feedbacks) / len(feedbacks), 2)

        # Mood improvement: mood_after - mood_before (only where both exist)
        mood_changes = [
            f.mood_after - f.mood_before
            for f in feedbacks
            if f.mood_before is not None and f.mood_after is not None
        ]
        avg_mood_change = round(sum(mood_changes) / len(mood_changes), 2) if mood_changes else 0

        return {
            "count": len(feedbacks),
            "avg_effectiveness": avg_eff,
            "avg_mood_change": avg_mood_change,
        }

    # ── Badges ────────────────────────────────────────────────────────────────

    @staticmethod
    def _badges_earned(db: Session, user_id: int, start: date, end: date):
        badges = db.query(Achievement).filter(
            Achievement.user_id == user_id,
            Achievement.earned_at >= datetime.combine(start, datetime.min.time()),
            Achievement.earned_at < datetime.combine(end, datetime.min.time()),
        ).all()

        from model.achievement import BADGE_CATALOG
        return [
            {
                "badge_type": b.badge_type.value,
                "name": BADGE_CATALOG.get(b.badge_type, {}).get("name", b.badge_type.value),
                "icon": BADGE_CATALOG.get(b.badge_type, {}).get("icon", ""),
                "earned_at": b.earned_at.isoformat() if b.earned_at else None,
            }
            for b in badges
        ]

    # ── Journal ─────────────────────────────────────────────────────────────

    @staticmethod
    def _journal_summary(db: Session, user_id: int, start: date, end: date):
        entries = db.query(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date < end,
        ).all()

        if not entries:
            return {"entry_count": 0, "distortions_found": 0, "top_distortion": None, "avg_severity": 0, "helpful_reframes": 0}

        distorted = [e for e in entries if e.distortion_type and e.distortion_type != "none"]
        helpful = [e for e in entries if e.user_found_helpful is True]

        # Top distortion
        freq = {}
        for e in distorted:
            freq[e.distortion_type] = freq.get(e.distortion_type, 0) + 1
        top_distortion = max(freq, key=freq.get) if freq else None

        avg_severity = round(sum(e.severity or 0 for e in distorted) / len(distorted), 2) if distorted else 0

        return {
            "entry_count": len(entries),
            "distortions_found": len(distorted),
            "top_distortion": top_distortion,
            "avg_severity": avg_severity,
            "helpful_reframes": len(helpful),
        }

    # ── Wellness Score ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_wellness_score(summary):
        """Compute a 0-100 wellness score from multiple factors:
        - Mood average (40% weight, scaled from 1-5 → 0-100)
        - Engagement: active days (25% weight, 7 = 100%)
        - Activities completed (20% weight, 7+ = 100%)
        - Mood checkin consistency (15% weight, 7 = 100%)
        """
        mood = summary["mood"]
        eng = summary["engagement"]

        # Mood score: 1-5 → 0-100
        mood_score = ((mood["avg_score"] - 1) / 4) * 100 if mood["checkin_count"] > 0 else 50

        # Active days: 0-7 → 0-100
        active_score = min(eng["active_days"] / 7, 1) * 100

        # Activities: 0-7+ → 0-100
        activity_score = min(eng["activities_completed"] / 7, 1) * 100

        # Checkin consistency: 0-7 → 0-100
        checkin_score = min(mood["checkin_count"] / 7, 1) * 100

        score = (
            mood_score * 0.40
            + active_score * 0.25
            + activity_score * 0.20
            + checkin_score * 0.15
        )
        return round(score, 1)

    # ── Deltas (week-over-week) ───────────────────────────────────────────────

    @staticmethod
    def _compute_deltas(summary):
        mood = summary["mood"]
        prev_mood = summary["mood_previous"]
        eng = summary["engagement"]
        prev_eng = summary["engagement_previous"]

        mood_delta = round(mood["avg_score"] - prev_mood["avg_score"], 2) if prev_mood["checkin_count"] > 0 else None
        activity_delta = eng["activities_completed"] - prev_eng["activities_completed"]
        active_days_delta = eng["active_days"] - prev_eng["active_days"]

        return {
            "mood_score": mood_delta,
            "activities_completed": activity_delta,
            "active_days": active_days_delta,
        }

    # ── Insights ──────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_insights(summary):
        insights = []
        mood = summary["mood"]
        eng = summary["engagement"]
        deltas = summary["deltas"]
        feedback = summary["feedback"]
        badges = summary["badges_earned"]
        score = summary["wellness_score"]

        # Mood trend insight
        if mood["checkin_count"] >= 3:
            if mood["avg_score"] >= 4.0:
                insights.append({
                    "type": "positive",
                    "icon": "🌟",
                    "text": "Your mood was consistently high this week. Keep up the great work!"
                })
            elif mood["avg_score"] <= 2.5:
                insights.append({
                    "type": "support",
                    "icon": "💙",
                    "text": "This was a tougher week emotionally. Remember, it's okay to have low days — reaching out for support can help."
                })
            elif deltas.get("mood_score") is not None and deltas["mood_score"] > 0.5:
                insights.append({
                    "type": "positive",
                    "icon": "📈",
                    "text": "Your mood improved compared to last week. The effort you're putting in is showing!"
                })
            elif deltas.get("mood_score") is not None and deltas["mood_score"] < -0.5:
                insights.append({
                    "type": "neutral",
                    "icon": "🔄",
                    "text": "Your mood dipped a bit from last week. Consider trying a different mix of activities."
                })
        elif mood["checkin_count"] == 0:
            insights.append({
                "type": "nudge",
                "icon": "📝",
                "text": "You didn't check in this week. Daily mood tracking helps you spot patterns — try to check in each day!"
            })

        # Engagement insight
        if eng["activities_completed"] >= 5:
            insights.append({
                "type": "positive",
                "icon": "🏆",
                "text": f"You completed {eng['activities_completed']} activities this week — outstanding commitment!"
            })
        elif eng["activities_completed"] == 0:
            insights.append({
                "type": "nudge",
                "icon": "🎯",
                "text": "You haven't completed any activities this week. Even one small activity can boost your mood."
            })

        # Active days
        if eng["active_days"] >= 6:
            insights.append({
                "type": "positive",
                "icon": "🔥",
                "text": f"You were active {eng['active_days']} out of 7 days — amazing consistency!"
            })

        # Feedback insight
        if feedback["avg_mood_change"] > 0.5:
            insights.append({
                "type": "positive",
                "icon": "✨",
                "text": "Activities are making a real difference — your mood improved after completing them."
            })

        # Badge celebration
        if badges:
            badge_names = ", ".join(b["name"] for b in badges[:3])
            insights.append({
                "type": "celebration",
                "icon": "🎖️",
                "text": f"You earned new badges this week: {badge_names}"
            })

        # Community engagement
        if eng["posts_created"] >= 3:
            insights.append({
                "type": "positive",
                "icon": "💬",
                "text": f"You shared {eng['posts_created']} posts with your community this week — social connection supports healing."
            })

        # Journal insight
        journal = summary.get("journal", {})
        if journal.get("entry_count", 0) >= 3:
            insights.append({
                "type": "positive",
                "icon": "📓",
                "text": f"You wrote {journal['entry_count']} journal entries this week — great self-reflection!"
            })
        elif journal.get("entry_count", 0) == 0:
            insights.append({
                "type": "nudge",
                "icon": "✍️",
                "text": "Try writing in your Thought Journal this week — it helps spot thinking patterns and build healthier perspectives."
            })

        # Overall score insight
        if score >= 80:
            insights.append({
                "type": "positive",
                "icon": "🌈",
                "text": "Your wellness score is excellent this week. You're building strong habits!"
            })
        elif score <= 30:
            insights.append({
                "type": "support",
                "icon": "🤝",
                "text": "Your wellness score is lower this week. Small steps count — even one check-in or activity helps."
            })

        # Cap at 5 insights, prioritize positive then support then nudge
        priority = {"celebration": 0, "positive": 1, "support": 2, "neutral": 3, "nudge": 4}
        insights.sort(key=lambda i: priority.get(i["type"], 5))
        return insights[:5]
