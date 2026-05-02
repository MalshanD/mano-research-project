"""
Activity Effectiveness Feedback Service
Handles submitting feedback, aggregating effectiveness scores,
and providing community-wide activity ratings.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from model.activity_feedback import ActivityFeedback


class FeedbackService:

    @staticmethod
    def submit_feedback(
        db: Session,
        user_id: int,
        activity_id: str,
        effectiveness_rating: int,
        mood_before: int = None,
        mood_after: int = None,
        feedback_note: str = None,
        would_recommend: int = None,
    ):
        """Submit feedback for a completed activity.
        Updates existing feedback if user already rated this activity."""
        from fastapi import HTTPException

        # Validate rating
        if effectiveness_rating < 1 or effectiveness_rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        if mood_before is not None and (mood_before < 1 or mood_before > 5):
            raise HTTPException(status_code=400, detail="mood_before must be between 1 and 5")
        if mood_after is not None and (mood_after < 1 or mood_after > 5):
            raise HTTPException(status_code=400, detail="mood_after must be between 1 and 5")

        # Upsert: update if already exists
        existing = db.query(ActivityFeedback).filter(
            ActivityFeedback.user_id == user_id,
            ActivityFeedback.activity_id == activity_id,
        ).first()

        if existing:
            existing.effectiveness_rating = effectiveness_rating
            existing.mood_before = mood_before
            existing.mood_after = mood_after
            existing.feedback_note = feedback_note
            existing.would_recommend = would_recommend
            existing.created_at = datetime.now()
            db.commit()
            db.refresh(existing)
            return {
                "id": existing.id,
                "updated": True,
                "message": "Feedback updated successfully",
            }
        else:
            feedback = ActivityFeedback(
                user_id=user_id,
                activity_id=activity_id,
                effectiveness_rating=effectiveness_rating,
                mood_before=mood_before,
                mood_after=mood_after,
                feedback_note=feedback_note,
                would_recommend=would_recommend,
            )
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
            return {
                "id": feedback.id,
                "updated": False,
                "message": "Feedback submitted successfully",
            }

    @staticmethod
    def get_my_feedback(db: Session, user_id: int, activity_id: str):
        """Get user's own feedback for an activity."""
        feedback = db.query(ActivityFeedback).filter(
            ActivityFeedback.user_id == user_id,
            ActivityFeedback.activity_id == activity_id,
        ).first()

        if not feedback:
            return {"has_feedback": False}

        return {
            "has_feedback": True,
            "effectiveness_rating": feedback.effectiveness_rating,
            "mood_before": feedback.mood_before,
            "mood_after": feedback.mood_after,
            "feedback_note": feedback.feedback_note,
            "would_recommend": feedback.would_recommend,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        }

    @staticmethod
    def get_activity_effectiveness(db: Session, activity_id: str):
        """Get aggregated effectiveness data for a single activity."""
        feedbacks = db.query(ActivityFeedback).filter(
            ActivityFeedback.activity_id == activity_id,
        ).all()

        if not feedbacks:
            return {
                "activity_id": activity_id,
                "total_reviews": 0,
                "avg_effectiveness": None,
                "avg_mood_improvement": None,
                "recommendation_rate": None,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }

        total = len(feedbacks)
        avg_eff = sum(f.effectiveness_rating for f in feedbacks) / total

        # Mood improvement (only from feedbacks that have both before/after)
        mood_pairs = [(f.mood_before, f.mood_after) for f in feedbacks if f.mood_before and f.mood_after]
        avg_mood_improvement = None
        if mood_pairs:
            improvements = [after - before for before, after in mood_pairs]
            avg_mood_improvement = round(sum(improvements) / len(improvements), 2)

        # Recommendation rate
        recommends = [f.would_recommend for f in feedbacks if f.would_recommend is not None]
        recommendation_rate = None
        if recommends:
            yes_count = sum(1 for r in recommends if r == 3)
            recommendation_rate = round((yes_count / len(recommends)) * 100, 1)

        # Rating distribution
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedbacks:
            dist[f.effectiveness_rating] = dist.get(f.effectiveness_rating, 0) + 1

        return {
            "activity_id": activity_id,
            "total_reviews": total,
            "avg_effectiveness": round(avg_eff, 2),
            "avg_mood_improvement": avg_mood_improvement,
            "recommendation_rate": recommendation_rate,
            "rating_distribution": dist,
        }

    @staticmethod
    def get_top_rated_activities(db: Session, limit: int = 10):
        """Get the top-rated activities across all users (min 2 reviews)."""
        results = (
            db.query(
                ActivityFeedback.activity_id,
                func.avg(ActivityFeedback.effectiveness_rating).label("avg_rating"),
                func.count(ActivityFeedback.id).label("review_count"),
            )
            .group_by(ActivityFeedback.activity_id)
            .having(func.count(ActivityFeedback.id) >= 2)
            .order_by(func.avg(ActivityFeedback.effectiveness_rating).desc())
            .limit(limit)
            .all()
        )

        from data.activities import get_activity_by_id

        top_activities = []
        for activity_id, avg_rating, review_count in results:
            activity = get_activity_by_id(activity_id)
            top_activities.append({
                "activity_id": activity_id,
                "activity_name": activity["name"] if activity else activity_id,
                "category": activity.get("category", "unknown") if activity else "unknown",
                "avg_rating": round(float(avg_rating), 2),
                "review_count": review_count,
            })

        return {"top_activities": top_activities, "total": len(top_activities)}

    @staticmethod
    def get_user_feedback_summary(db: Session, user_id: int):
        """Get all feedback submitted by a user."""
        feedbacks = db.query(ActivityFeedback).filter(
            ActivityFeedback.user_id == user_id,
        ).order_by(ActivityFeedback.created_at.desc()).all()

        from data.activities import get_activity_by_id

        items = []
        for f in feedbacks:
            activity = get_activity_by_id(f.activity_id)
            items.append({
                "activity_id": f.activity_id,
                "activity_name": activity["name"] if activity else f.activity_id,
                "category": activity.get("category", "unknown") if activity else "unknown",
                "effectiveness_rating": f.effectiveness_rating,
                "mood_before": f.mood_before,
                "mood_after": f.mood_after,
                "mood_change": (f.mood_after - f.mood_before) if f.mood_before and f.mood_after else None,
                "would_recommend": f.would_recommend,
                "feedback_note": f.feedback_note,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })

        avg_rating = None
        if items:
            avg_rating = round(sum(i["effectiveness_rating"] for i in items) / len(items), 2)

        return {
            "total_feedbacks": len(items),
            "avg_rating_given": avg_rating,
            "feedbacks": items,
        }
