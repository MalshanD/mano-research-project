"""Crisis Detection Safety Net — multi-signal crisis detection engine.

Detects crisis signals from:
1. Chat messages (keyword matching + severity scoring)
2. Mood patterns (consecutive bad/low days)
3. Engagement drops (sudden inactivity after regular usage)
4. Post content (crisis language in community posts)

Each detection creates a CrisisAlert record and returns actionable data
for the frontend to show appropriate intervention UI."""

import json
import re
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from model.crisis_alert import CrisisAlert, CrisisSeverity, CrisisSource
from model.mood_checkin import MoodCheckIn, MoodType
from model.user_activity_log import UserActivityLog


# ── Keyword Tiers ─────────────────────────────────────────────────────────────
# Ordered by severity — critical first, then high, medium, low
CRISIS_KEYWORDS = {
    CrisisSeverity.critical: [
        "kill myself", "suicide", "end my life", "want to die",
        "going to end it", "take my own life", "suicidal",
        "end it all", "better off dead", "plan to die",
    ],
    CrisisSeverity.high: [
        "self-harm", "hurt myself", "cutting myself", "overdose",
        "no reason to live", "can't go on", "don't want to be alive",
        "rather be dead", "nothing left", "can't take it anymore",
        "not worth living", "goodbye forever",
    ],
    CrisisSeverity.medium: [
        "hopeless", "give up", "worthless", "nobody cares",
        "can't cope", "falling apart", "broken inside",
        "what's the point", "done trying", "tired of living",
        "no one would miss me", "trapped",
    ],
    CrisisSeverity.low: [
        "really struggling", "dark place", "everything is wrong",
        "can't handle", "overwhelmed", "losing control",
        "don't know what to do", "rock bottom",
    ],
}

# Flatten for quick lookup
ALL_KEYWORDS = {}
for severity, keywords in CRISIS_KEYWORDS.items():
    for kw in keywords:
        ALL_KEYWORDS[kw] = severity


class CrisisDetectionService:

    # ── Text Analysis ─────────────────────────────────────────────────────────

    @staticmethod
    def analyze_text(text: str):
        """Analyze text for crisis signals. Returns severity and matched keywords.
        Returns None if no crisis detected."""
        if not text:
            return None

        lower_text = text.lower()
        matched = []
        highest_severity = None
        severity_order = {
            CrisisSeverity.critical: 4,
            CrisisSeverity.high: 3,
            CrisisSeverity.medium: 2,
            CrisisSeverity.low: 1,
        }

        for keyword, severity in ALL_KEYWORDS.items():
            if keyword in lower_text:
                matched.append({"keyword": keyword, "severity": severity.value})
                if highest_severity is None or severity_order[severity] > severity_order[highest_severity]:
                    highest_severity = severity

        if not matched:
            return None

        return {
            "severity": highest_severity,
            "matched_keywords": matched,
            "keyword_count": len(matched),
        }

    # ── Chat Message Detection ────────────────────────────────────────────────

    @staticmethod
    def check_chat_message(db: Session, user_id: int, message: str, session_id: int = None):
        """Check a chat message for crisis signals. Creates alert if detected.
        Called from chat endpoint after message processing."""
        analysis = CrisisDetectionService.analyze_text(message)
        if not analysis:
            return {"crisis_detected": False}

        # Create alert
        alert = CrisisAlert(
            user_id=user_id,
            severity=analysis["severity"],
            source=CrisisSource.chat_message,
            trigger_text=message[:200],
            details=json.dumps({
                "matched_keywords": analysis["matched_keywords"],
                "session_id": session_id,
                "full_analysis": {
                    "keyword_count": analysis["keyword_count"],
                },
            }),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        return {
            "crisis_detected": True,
            "alert_id": alert.id,
            "severity": analysis["severity"].value,
            "matched_keywords": [m["keyword"] for m in analysis["matched_keywords"]],
            "message": CrisisDetectionService._get_support_message(analysis["severity"]),
            "resources": CrisisDetectionService._get_resources(analysis["severity"]),
        }

    # ── Post Content Detection ────────────────────────────────────────────────

    @staticmethod
    def check_post_content(db: Session, user_id: int, post_text: str, post_id: int = None):
        """Check community post content for crisis signals."""
        analysis = CrisisDetectionService.analyze_text(post_text)
        if not analysis:
            return {"crisis_detected": False}

        alert = CrisisAlert(
            user_id=user_id,
            severity=analysis["severity"],
            source=CrisisSource.post_content,
            trigger_text=post_text[:200],
            details=json.dumps({
                "matched_keywords": analysis["matched_keywords"],
                "post_id": post_id,
            }),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        return {
            "crisis_detected": True,
            "alert_id": alert.id,
            "severity": analysis["severity"].value,
            "message": CrisisDetectionService._get_support_message(analysis["severity"]),
            "resources": CrisisDetectionService._get_resources(analysis["severity"]),
        }

    # ── Mood Pattern Detection ────────────────────────────────────────────────

    @staticmethod
    def check_mood_patterns(db: Session, user_id: int):
        """Check for concerning mood patterns:
        - 3+ consecutive 'bad' days → high severity
        - 3+ consecutive 'low' days → medium severity
        - 5+ consecutive 'low' or 'bad' days → critical severity
        - Sudden drop from 'great/good' to 'bad' within 2 days → medium
        Returns crisis info or None."""

        # Get last 7 days of mood check-ins
        week_ago = date.today() - timedelta(days=7)
        checkins = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date >= week_ago,
        ).order_by(MoodCheckIn.checkin_date.desc()).all()

        if len(checkins) < 3:
            return {"crisis_detected": False, "pattern": None}

        moods = [c.mood.value for c in checkins]

        # Check for 5+ consecutive bad/low
        consecutive_distress = 0
        for m in moods:
            if m in ("bad", "low"):
                consecutive_distress += 1
            else:
                break

        if consecutive_distress >= 5:
            return CrisisDetectionService._create_mood_alert(
                db, user_id, CrisisSeverity.critical,
                f"User has reported 'bad' or 'low' mood for {consecutive_distress} consecutive days",
                moods
            )

        # Check for 3+ consecutive 'bad'
        consecutive_bad = 0
        for m in moods:
            if m == "bad":
                consecutive_bad += 1
            else:
                break

        if consecutive_bad >= 3:
            return CrisisDetectionService._create_mood_alert(
                db, user_id, CrisisSeverity.high,
                f"User has reported 'bad' mood for {consecutive_bad} consecutive days",
                moods
            )

        # Check for 3+ consecutive 'low'
        consecutive_low = 0
        for m in moods:
            if m in ("low", "bad"):
                consecutive_low += 1
            else:
                break

        if consecutive_low >= 3:
            return CrisisDetectionService._create_mood_alert(
                db, user_id, CrisisSeverity.medium,
                f"User has reported low/bad mood for {consecutive_low} consecutive days",
                moods
            )

        # Sudden mood drop: great/good → bad within 2 days
        if len(moods) >= 2:
            if moods[0] == "bad" and moods[1] in ("great", "good"):
                return CrisisDetectionService._create_mood_alert(
                    db, user_id, CrisisSeverity.medium,
                    "Sudden mood drop from positive to bad within 1 day",
                    moods
                )

        return {"crisis_detected": False, "pattern": None}

    @staticmethod
    def _create_mood_alert(db: Session, user_id: int, severity: CrisisSeverity, description: str, moods: list):
        """Create a mood-pattern crisis alert, but avoid duplicates within 24 hours."""
        # Check if we already created a mood_pattern alert in the last 24h
        yesterday = datetime.now() - timedelta(hours=24)
        existing = db.query(CrisisAlert).filter(
            CrisisAlert.user_id == user_id,
            CrisisAlert.source == CrisisSource.mood_pattern,
            CrisisAlert.created_at >= yesterday,
        ).first()

        if existing:
            return {
                "crisis_detected": True,
                "alert_id": existing.id,
                "severity": existing.severity.value,
                "pattern": description,
                "existing_alert": True,
                "message": CrisisDetectionService._get_support_message(existing.severity),
                "resources": CrisisDetectionService._get_resources(existing.severity),
            }

        alert = CrisisAlert(
            user_id=user_id,
            severity=severity,
            source=CrisisSource.mood_pattern,
            trigger_text=f"Mood pattern: {', '.join(moods[:7])}",
            details=json.dumps({
                "pattern_description": description,
                "recent_moods": moods[:7],
            }),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        return {
            "crisis_detected": True,
            "alert_id": alert.id,
            "severity": severity.value,
            "pattern": description,
            "message": CrisisDetectionService._get_support_message(severity),
            "resources": CrisisDetectionService._get_resources(severity),
        }

    # ── Engagement Drop Detection ─────────────────────────────────────────────

    @staticmethod
    def check_engagement_drop(db: Session, user_id: int):
        """Check for sudden engagement drop — user was active 5+ of last 14 days
        but 0 activity in the last 3 days. This can indicate withdrawal."""

        today = date.today()
        three_days_ago = today - timedelta(days=3)
        two_weeks_ago = today - timedelta(days=14)

        # Activity in last 3 days
        recent_days = db.query(func.count(UserActivityLog.id)).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date >= three_days_ago,
        ).scalar() or 0

        # Activity in the previous 11 days (days 4-14)
        earlier_days = db.query(func.count(UserActivityLog.id)).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.log_date >= two_weeks_ago,
            UserActivityLog.log_date < three_days_ago,
        ).scalar() or 0

        if recent_days == 0 and earlier_days >= 5:
            # Check for existing alert in last 48h
            two_days_ago = datetime.now() - timedelta(hours=48)
            existing = db.query(CrisisAlert).filter(
                CrisisAlert.user_id == user_id,
                CrisisAlert.source == CrisisSource.engagement_drop,
                CrisisAlert.created_at >= two_days_ago,
            ).first()

            if existing:
                return {
                    "crisis_detected": True,
                    "alert_id": existing.id,
                    "severity": existing.severity.value,
                    "existing_alert": True,
                }

            alert = CrisisAlert(
                user_id=user_id,
                severity=CrisisSeverity.low,
                source=CrisisSource.engagement_drop,
                trigger_text=f"No activity for 3+ days after {earlier_days} active days in prior 11 days",
                details=json.dumps({
                    "recent_active_days": recent_days,
                    "previous_active_days": earlier_days,
                }),
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            return {
                "crisis_detected": True,
                "alert_id": alert.id,
                "severity": "low",
                "pattern": f"Engagement dropped after {earlier_days} active days",
            }

        return {"crisis_detected": False}

    # ── Full Safety Check (combines all signals) ──────────────────────────────

    @staticmethod
    def run_safety_check(db: Session, user_id: int):
        """Run all passive crisis detection checks for a user.
        Called from the wellness summary endpoint or periodically."""

        mood_check = CrisisDetectionService.check_mood_patterns(db, user_id)
        engagement_check = CrisisDetectionService.check_engagement_drop(db, user_id)

        # Get active alerts count
        active_alerts = db.query(func.count(CrisisAlert.id)).filter(
            CrisisAlert.user_id == user_id,
            CrisisAlert.is_active == True,
        ).scalar() or 0

        # Get recent alerts (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_alerts = db.query(CrisisAlert).filter(
            CrisisAlert.user_id == user_id,
            CrisisAlert.created_at >= week_ago,
        ).order_by(CrisisAlert.created_at.desc()).all()

        # Determine overall risk level
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_severity = "none"
        for alert in recent_alerts:
            s = alert.severity.value
            if severity_order.get(s, 0) > severity_order.get(max_severity, 0):
                max_severity = s

        return {
            "user_id": user_id,
            "safety_status": "concern" if active_alerts > 0 else "safe",
            "active_alerts": active_alerts,
            "overall_risk_level": max_severity,
            "mood_analysis": mood_check,
            "engagement_analysis": engagement_check,
            "recent_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "source": a.source.value,
                    "trigger_text": a.trigger_text[:100] if a.trigger_text else None,
                    "is_active": a.is_active,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in recent_alerts[:10]
            ],
            "support_message": CrisisDetectionService._get_support_message(
                CrisisSeverity(max_severity) if max_severity != "none" else None
            ),
            "resources": CrisisDetectionService._get_resources(
                CrisisSeverity(max_severity) if max_severity != "none" else None
            ),
        }

    # ── Alert Management ──────────────────────────────────────────────────────

    @staticmethod
    def get_user_alerts(db: Session, user_id: int, active_only: bool = True):
        """Get crisis alerts for a user."""
        query = db.query(CrisisAlert).filter(CrisisAlert.user_id == user_id)
        if active_only:
            query = query.filter(CrisisAlert.is_active == True)
        alerts = query.order_by(CrisisAlert.created_at.desc()).limit(20).all()

        return [
            {
                "id": a.id,
                "severity": a.severity.value,
                "source": a.source.value,
                "trigger_text": a.trigger_text[:100] if a.trigger_text else None,
                "is_active": a.is_active,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

    @staticmethod
    def resolve_alert(db: Session, alert_id: int, resolution_note: str = None):
        """Mark a crisis alert as resolved."""
        alert = db.query(CrisisAlert).filter(CrisisAlert.id == alert_id).first()
        if not alert:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Alert not found")

        alert.is_active = False
        alert.resolved_at = datetime.now()
        alert.resolution_note = resolution_note
        db.commit()

        return {"alert_id": alert_id, "resolved": True}

    # ── Support Messages & Resources ──────────────────────────────────────────

    @staticmethod
    def _get_support_message(severity):
        if severity is None:
            return None

        messages = {
            CrisisSeverity.critical: (
                "We're deeply concerned about you. Please reach out to a crisis helpline "
                "immediately. You are not alone, and help is available right now."
            ),
            CrisisSeverity.high: (
                "It sounds like you're going through something very difficult. "
                "Please consider reaching out to someone you trust or a professional. "
                "You matter, and support is available."
            ),
            CrisisSeverity.medium: (
                "We've noticed you might be having a tough time. "
                "It's okay to ask for help — talking to someone can make a real difference."
            ),
            CrisisSeverity.low: (
                "We're here for you. If you're feeling overwhelmed, "
                "consider trying a calming activity or reaching out to a friend."
            ),
        }
        return messages.get(severity, None)

    @staticmethod
    def _get_resources(severity):
        """Return emergency resources scaled to severity."""
        base_resources = [
            {"name": "National Mental Health Helpline", "number": "1926", "available": "24/7"},
            {"name": "Lanka Life Line", "number": "1375", "available": "24/7 (Text/Call)"},
        ]

        if severity in (CrisisSeverity.critical, CrisisSeverity.high):
            base_resources.extend([
                {"name": "Emergency Services", "number": "911", "available": "24/7"},
                {"name": "Sri Lanka Sumithrayo", "number": "+94 767 520 620", "available": "24/7"},
            ])

        return base_resources if severity else []
