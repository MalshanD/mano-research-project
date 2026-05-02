"""
Streak & Achievement Badge Service
Handles daily activity logging, streak calculation, and automatic badge awarding.
"""
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from model.user_activity_log import UserActivityLog
from model.achievement import Achievement, BadgeType, BADGE_CATALOG


class StreakService:

    # ─── Activity Logging ────────────────────────────────────────────────

    @staticmethod
    def log_activity(db: Session, user_id: int, activity_type: str):
        """Log a user action for today. Called when user completes an activity,
        creates a post, or checks in mood. Then checks for new badges.

        activity_type: 'activity_completed' | 'post_created' | 'mood_checkin'
        """
        today = date.today()

        # Get or create today's log
        log = db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date == today
        ).first()

        if not log:
            log = UserActivityLog(
                user_id=user_id,
                log_date=today,
                activities_completed=0,
                posts_created=0,
                mood_checked_in=False
            )
            db.add(log)

        # Increment the relevant counter
        if activity_type == "activity_completed":
            log.activities_completed += 1
        elif activity_type == "post_created":
            log.posts_created += 1
        elif activity_type == "mood_checkin":
            log.mood_checked_in = True

        log.updated_at = datetime.now()
        db.commit()

        # Check and award any new badges
        new_badges = StreakService._check_and_award_badges(db, user_id)
        return new_badges

    # ─── Streak Calculation ──────────────────────────────────────────────

    @staticmethod
    def get_user_streaks(db: Session, user_id: int):
        """Calculate current streak, longest streak, and weekly stats."""
        # Fetch all log dates for user (sorted desc)
        logs = db.query(UserActivityLog.log_date).filter(
            UserActivityLog.user_id == user_id
        ).order_by(UserActivityLog.log_date.desc()).all()

        active_dates = set(l[0] for l in logs)

        # Current streak: consecutive days ending today or yesterday
        current_streak = 0
        today = date.today()
        check_date = today

        # Allow today to not be counted yet (check from today backwards)
        if check_date not in active_dates:
            check_date = today - timedelta(days=1)

        while check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        # Longest streak ever
        longest_streak = 0
        if active_dates:
            sorted_dates = sorted(active_dates)
            streak = 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                    streak += 1
                else:
                    longest_streak = max(longest_streak, streak)
                    streak = 1
            longest_streak = max(longest_streak, streak)

        # This week stats (Mon-Sun)
        week_start = today - timedelta(days=today.weekday())
        week_logs = db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date >= week_start,
            UserActivityLog.log_date <= today
        ).all()

        week_activities = sum(l.activities_completed for l in week_logs)
        week_posts = sum(l.posts_created for l in week_logs)
        week_moods = sum(1 for l in week_logs if l.mood_checked_in)
        active_days_this_week = len(week_logs)

        # Total stats
        total_stats = db.query(
            func.sum(UserActivityLog.activities_completed),
            func.sum(UserActivityLog.posts_created),
            func.count(UserActivityLog.id)
        ).filter(
            UserActivityLog.user_id == user_id
        ).first()

        total_activities = total_stats[0] or 0
        total_posts = total_stats[1] or 0
        total_active_days = total_stats[2] or 0

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_active_days": total_active_days,
            "total_activities_completed": total_activities,
            "total_posts_created": total_posts,
            "week": {
                "active_days": active_days_this_week,
                "activities_completed": week_activities,
                "posts_created": week_posts,
                "moods_logged": week_moods,
                "days_remaining": 7 - active_days_this_week,
            },
            # Last 7 days heatmap
            "heatmap": StreakService._get_heatmap(db, user_id, 14),
        }

    @staticmethod
    def _get_heatmap(db: Session, user_id: int, days: int = 14):
        """Get daily activity intensity for the last N days."""
        start_date = date.today() - timedelta(days=days - 1)
        logs = db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date >= start_date
        ).order_by(UserActivityLog.log_date.asc()).all()

        log_map = {l.log_date: l for l in logs}
        heatmap = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            log = log_map.get(d)
            if log:
                intensity = min(
                    log.activities_completed + log.posts_created + (1 if log.mood_checked_in else 0),
                    5  # cap at 5 for display
                )
            else:
                intensity = 0
            heatmap.append({
                "date": str(d),
                "intensity": intensity,
                "is_today": d == date.today()
            })
        return heatmap

    # ─── Achievement Badges ──────────────────────────────────────────────

    @staticmethod
    def get_user_achievements(db: Session, user_id: int):
        """Get all earned badges plus the full catalog with locked/unlocked status."""
        earned = db.query(Achievement).filter(
            Achievement.user_id == user_id
        ).order_by(Achievement.earned_at.desc()).all()

        earned_types = {a.badge_type for a in earned}
        earned_map = {a.badge_type: a for a in earned}

        badges = []
        for badge_type, meta in BADGE_CATALOG.items():
            is_earned = badge_type in earned_types
            badge_info = {
                "badge_type": badge_type.value,
                "name": meta["name"],
                "description": meta["description"],
                "icon": meta["icon"],
                "tier": meta["tier"],
                "earned": is_earned,
                "earned_at": earned_map[badge_type].earned_at.isoformat() if is_earned else None,
            }
            badges.append(badge_info)

        # Sort: earned first (most recent), then locked
        badges.sort(key=lambda b: (not b["earned"], b["earned_at"] or ""), reverse=False)
        earned_badges = [b for b in badges if b["earned"]]
        locked_badges = [b for b in badges if not b["earned"]]

        return {
            "total_earned": len(earned_badges),
            "total_available": len(BADGE_CATALOG),
            "earned_badges": earned_badges,
            "locked_badges": locked_badges,
        }

    @staticmethod
    def _check_and_award_badges(db: Session, user_id: int):
        """Check all badge conditions and award any newly qualified badges.
        Returns list of newly awarded badge names."""
        earned_types = {
            a.badge_type for a in db.query(Achievement.badge_type).filter(
                Achievement.user_id == user_id
            ).all()
        }

        new_badges = []

        # ── Streak badges ──
        streaks = StreakService.get_user_streaks(db, user_id)
        current = streaks["current_streak"]

        streak_thresholds = [
            (3, BadgeType.streak_3),
            (7, BadgeType.streak_7),
            (14, BadgeType.streak_14),
            (30, BadgeType.streak_30),
        ]
        for threshold, badge_type in streak_thresholds:
            if current >= threshold and badge_type not in earned_types:
                new_badges.append(StreakService._award_badge(db, user_id, badge_type))

        # ── Activity completion badges ──
        total_activities = streaks["total_activities_completed"]
        activity_thresholds = [
            (1, BadgeType.first_step),
            (5, BadgeType.active_5),
            (10, BadgeType.active_10),
            (25, BadgeType.active_25),
            (50, BadgeType.active_50),
        ]
        for threshold, badge_type in activity_thresholds:
            if total_activities >= threshold and badge_type not in earned_types:
                new_badges.append(StreakService._award_badge(db, user_id, badge_type))

        # ── Post badges ──
        total_posts = streaks["total_posts_created"]
        post_thresholds = [
            (1, BadgeType.first_post),
            (5, BadgeType.community_voice),
            (10, BadgeType.social_butterfly),
        ]
        for threshold, badge_type in post_thresholds:
            if total_posts >= threshold and badge_type not in earned_types:
                new_badges.append(StreakService._award_badge(db, user_id, badge_type))

        # ── Mood badges ──
        from model.mood_checkin import MoodCheckIn
        total_moods = db.query(func.count(MoodCheckIn.id)).filter(
            MoodCheckIn.user_id == user_id
        ).scalar() or 0

        if total_moods >= 1 and BadgeType.mood_starter not in earned_types:
            new_badges.append(StreakService._award_badge(db, user_id, BadgeType.mood_starter))

        if total_moods >= 30 and BadgeType.mood_master not in earned_types:
            new_badges.append(StreakService._award_badge(db, user_id, BadgeType.mood_master))

        # Mood warrior: 7 consecutive days of mood check-ins
        if BadgeType.mood_warrior not in earned_types:
            mood_dates = [
                r[0] for r in db.query(MoodCheckIn.checkin_date).filter(
                    MoodCheckIn.user_id == user_id
                ).order_by(MoodCheckIn.checkin_date.desc()).all()
            ]
            if len(mood_dates) >= 7:
                consecutive = 1
                for i in range(1, len(mood_dates)):
                    if (mood_dates[i - 1] - mood_dates[i]).days == 1:
                        consecutive += 1
                        if consecutive >= 7:
                            new_badges.append(StreakService._award_badge(db, user_id, BadgeType.mood_warrior))
                            break
                    else:
                        consecutive = 1

        # ── Wellness Explorer: activities from 3+ categories ──
        if BadgeType.wellness_explorer not in earned_types:
            from model.completed_activity import CompletedActivity
            completed = db.query(CompletedActivity).filter(
                CompletedActivity.user_id == user_id
            ).all()
            categories = set()
            for c in completed:
                if c.activity_json and isinstance(c.activity_json, dict):
                    cat = c.activity_json.get("category")
                    if cat:
                        categories.add(cat)
            if len(categories) >= 3:
                new_badges.append(StreakService._award_badge(db, user_id, BadgeType.wellness_explorer))

        # ── Consistency King: 7-day streak + mood + post in same week ──
        if BadgeType.consistency_king not in earned_types:
            if current >= 7:
                week = streaks["week"]
                if week["moods_logged"] >= 5 and week["posts_created"] >= 1:
                    new_badges.append(StreakService._award_badge(db, user_id, BadgeType.consistency_king))

        db.commit()
        return new_badges

    @staticmethod
    def _award_badge(db: Session, user_id: int, badge_type: BadgeType):
        """Award a badge to a user. Returns badge info dict."""
        achievement = Achievement(
            user_id=user_id,
            badge_type=badge_type,
        )
        db.add(achievement)

        meta = BADGE_CATALOG[badge_type]
        return {
            "badge_type": badge_type.value,
            "name": meta["name"],
            "description": meta["description"],
            "icon": meta["icon"],
            "tier": meta["tier"],
        }
