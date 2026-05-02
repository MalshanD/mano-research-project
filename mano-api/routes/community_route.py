from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from lib.activity.community_service import CommunityService
from lib.CBT.streak_service import StreakService
from lib.CBT.reaction_service import ReactionService
from lib.CBT.wellness_service import WellnessService
from lib.CBT.crisis_service import CrisisDetectionService
from lib.CBT.journal_service import JournalService
from schemas.community.communityInSchema import (
    CreatePostRequest, MoodCheckInRequest, ReactionRequest,
    JournalEntryRequest, JournalAnalyzeRequest, JournalFeedbackRequest,
)


router = APIRouter(prefix="/community", tags=["Community"])

# NOTE: static/multi-segment routes MUST come before single-segment wildcards

@router.get("/clusters", description="Get all communities with their actual member counts")
def get_community_clusters(db: Session = Depends(get_db)):
    return CommunityService.get_all_clusters_with_counts(db)

@router.get("/feed/{user_id}", description="Get community feed for a user (server-side cluster lookup)")
def get_user_feed(user_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_feed_for_user(db, user_id)

# ── Mood Check-In Pulse ──────────────────────────────────────────────────────

@router.post("/mood/{user_id}", description="Submit or update today's mood check-in")
def submit_mood(user_id: int, request: MoodCheckInRequest, db: Session = Depends(get_db)):
    result = CommunityService.submit_mood_checkin(db, user_id, request.mood)
    # Auto-log for streak tracking
    new_badges = StreakService.log_activity(db, user_id, "mood_checkin")
    if new_badges:
        result["new_badges"] = new_badges
    # Crisis safety net: check mood patterns after each check-in
    if request.mood in ("bad", "low"):
        crisis_check = CrisisDetectionService.check_mood_patterns(db, user_id)
        if crisis_check.get("crisis_detected"):
            result["crisis_alert"] = crisis_check
    return result

@router.get("/mood/{user_id}/today", description="Get user's mood check-in for today")
def get_mood_today(user_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_my_mood_today(db, user_id)

@router.get("/mood/{user_id}/pulse", description="Get community mood pulse (aggregated mood for user's community)")
def get_mood_pulse(user_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_community_mood_pulse(db, user_id)

@router.get("/mood/{user_id}/history", description="Get user's mood history for last N days")
def get_mood_history(user_id: int, days: int = Query(default=7, ge=1, le=90), db: Session = Depends(get_db)):
    return CommunityService.get_my_mood_history(db, user_id, days)

# ── Posts ─────────────────────────────────────────────────────────────────────

@router.post("/{community_id}/post/{user_id}", description="Create a new post in a community")
def create_community_post(community_id: int, user_id: int, request: CreatePostRequest, db: Session = Depends(get_db)):
    result = CommunityService.create_post(
        db=db,
        user_id=user_id,
        community_id=community_id,
        post_type=request.post_type,
        paragraph=request.paragraph
    )
    # Auto-log for streak tracking
    StreakService.log_activity(db, user_id, "post_created")
    # Crisis safety net: scan post content
    crisis_check = CrisisDetectionService.check_post_content(
        db, user_id, request.paragraph, post_id=result.id if hasattr(result, 'id') else None
    )
    if crisis_check.get("crisis_detected"):
        return {
            "post": {"id": result.id, "post_type": result.post_type.name, "paragraph": result.paragraph},
            "crisis_alert": crisis_check,
        }
    return result

@router.get("/{community_id}/posts/{user_id}", description="Get all posts for a community (with user access check)")
def get_user_community_posts(community_id: int, user_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_community_posts(db, community_id, user_id)

@router.get("/{community_id}/posts", description="Get all posts for a community")
def get_community_posts(community_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_posts_by_community(db, community_id)

@router.get("/{community_id}/users", description="Get names of all users in a community")
def get_community_users(community_id: int, db: Session = Depends(get_db)):
    return CommunityService.get_community_users(db, community_id)

# ── Post Reactions (Beyond Likes) ─────────────────────────────────────────────

@router.post("/post/{post_id}/react/{user_id}", description="Toggle a reaction on a post (add if missing, remove if exists)")
def toggle_post_reaction(post_id: int, user_id: int, request: ReactionRequest, db: Session = Depends(get_db)):
    return ReactionService.toggle_reaction(db, user_id, post_id, request.reaction_type)

@router.get("/post/{post_id}/reactions/{user_id}", description="Get all reactions for a post (with user's own reactions)")
def get_post_reactions(post_id: int, user_id: int, db: Session = Depends(get_db)):
    return ReactionService.get_post_reactions(db, post_id, user_id)

@router.get("/post/{post_id}/reactions", description="Get all reactions for a post (anonymous)")
def get_post_reactions_public(post_id: int, db: Session = Depends(get_db)):
    return ReactionService.get_post_reactions(db, post_id)

# ── Weekly Wellness Summary ───────────────────────────────────────────────────

@router.get("/wellness-summary/{user_id}", description="Get the user's weekly wellness summary with insights")
def get_wellness_summary(user_id: int, db: Session = Depends(get_db)):
    return WellnessService.get_weekly_summary(db, user_id)

# ── Crisis Detection Safety Net ───────────────────────────────────────────────

@router.get("/crisis/safety-check/{user_id}", description="Run full safety check (mood patterns + engagement drop)")
def run_safety_check(user_id: int, db: Session = Depends(get_db)):
    return CrisisDetectionService.run_safety_check(db, user_id)

@router.get("/crisis/alerts/{user_id}", description="Get user's active crisis alerts")
def get_crisis_alerts(user_id: int, active_only: bool = Query(default=True), db: Session = Depends(get_db)):
    return CrisisDetectionService.get_user_alerts(db, user_id, active_only)

@router.post("/crisis/resolve/{alert_id}", description="Resolve a crisis alert")
def resolve_crisis_alert(alert_id: int, db: Session = Depends(get_db)):
    return CrisisDetectionService.resolve_alert(db, alert_id)

# ── Streaks & Achievement Badges ─────────────────────────────────────────────

@router.get("/streaks/{user_id}", description="Get user's activity streaks and weekly stats")
def get_user_streaks(user_id: int, db: Session = Depends(get_db)):
    return StreakService.get_user_streaks(db, user_id)

@router.get("/badges/{user_id}", description="Get user's achievement badges (earned + locked)")
def get_user_badges(user_id: int, db: Session = Depends(get_db)):
    return StreakService.get_user_achievements(db, user_id)

# ── CBT Thought Journal ──────────────────────────────────────────────────────

@router.post("/journal/{user_id}", description="Create a journal entry with CBT distortion analysis")
def create_journal_entry(user_id: int, request: JournalEntryRequest, db: Session = Depends(get_db)):
    from datetime import date as date_type
    entry_date = None
    if request.entry_date:
        try:
            entry_date = date_type.fromisoformat(request.entry_date)
        except ValueError:
            pass
    result = JournalService.create_entry(db, user_id, request.entry_text, entry_date)
    # Auto-log for streak tracking
    StreakService.log_activity(db, user_id, "journal_entry")
    # Crisis safety net: scan journal text
    try:
        crisis_check = CrisisDetectionService.check_post_content(
            db, user_id, request.entry_text, post_id=None
        )
        if crisis_check.get("crisis_detected"):
            result["crisis_alert"] = crisis_check
    except Exception:
        pass
    return result

@router.post("/journal/{user_id}/analyze", description="Analyze text for distortions without saving (live preview)")
def analyze_journal_text(user_id: int, request: JournalAnalyzeRequest, db: Session = Depends(get_db)):
    return JournalService.analyze_text_only(db, user_id, request.text)

@router.get("/journal/{user_id}/entries", description="Get user's journal entries for last N days")
def get_journal_entries(user_id: int, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return JournalService.get_entries(db, user_id, days)

@router.get("/journal/{user_id}/entry/{entry_id}", description="Get a single journal entry")
def get_journal_entry(user_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = JournalService.get_entry(db, entry_id, user_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry

@router.get("/journal/{user_id}/trends", description="Get distortion trends and analytics")
def get_journal_trends(user_id: int, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return JournalService.get_distortion_trends(db, user_id, days)

@router.post("/journal/{user_id}/feedback/{entry_id}", description="Rate whether a reframe was helpful")
def rate_journal_reframe(user_id: int, entry_id: int, request: JournalFeedbackRequest, db: Session = Depends(get_db)):
    result = JournalService.rate_reframe(db, entry_id, user_id, request.found_helpful)
    if not result:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return result

@router.get("/journal/catalog", description="Get the full CBT distortion catalog")
def get_distortion_catalog_route(db: Session = Depends(get_db)):
    return JournalService.get_catalog()

# Single-segment catch-all LAST to avoid swallowing the routes above
@router.get("/{user_id}", description="Get a user's current community")
def get_user_community(user_id: int, db: Session = Depends(get_db)):
    community = CommunityService.get_user_community(db, user_id)
    if not community:
        raise HTTPException(status_code=404, detail="User is not assigned to any community")
    return community
