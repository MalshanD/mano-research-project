from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.activity.activityInSchema import RecommendationRequest, CompleteActivityRequest, ActivityFeedbackRequest
from db.database import get_db
from lib.activity.activity_service import ActivityService
from lib.CBT.streak_service import StreakService
from lib.CBT.feedback_service import FeedbackService

router = APIRouter(prefix="/activity", tags=["Activity"])

@router.post("/stress/{user_id}/{stress_level}")
def recommend_stress_activity(user_id: int, stress_level: float, request: RecommendationRequest, db: Session = Depends(get_db)):
    return ActivityService.generate_and_save_recommendation(db, user_id, "stress", stress_level, request)

@router.post("/anxiety/{user_id}/{anxiety_level}")
def recommend_anxiety_activity(user_id: int, anxiety_level: float, request: RecommendationRequest, db: Session = Depends(get_db)):
    return ActivityService.generate_and_save_recommendation(db, user_id, "anxiety", anxiety_level, request)

@router.post("/depression/{user_id}/{depression_level}")
def recommend_depression_activity(user_id: int, depression_level: float, request: RecommendationRequest, db: Session = Depends(get_db)):
    return ActivityService.generate_and_save_recommendation(db, user_id, "depression", depression_level, request)

@router.get("/categories", description="Get all unique categories from the activities database")
def get_all_activity_categories():
    from data.activities import ACTIVITIES_DATABASE
    
    categories = set()
    for activity in ACTIVITIES_DATABASE:
        if 'category' in activity:
            categories.add(activity['category'])
            
    return {"categories": sorted(list(categories))}

@router.get("/details/{activity_id}", description="Get a specific activity by its ID")
def get_activity_details(activity_id: str):
    from data.activities import get_activity_by_id
    from fastapi import HTTPException
    
    activity = get_activity_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    return activity

# ── Activity Effectiveness Feedback ──────────────────────────────────────────

@router.post("/feedback/{user_id}", description="Submit effectiveness feedback for a completed activity")
def submit_activity_feedback(user_id: int, request: ActivityFeedbackRequest, db: Session = Depends(get_db)):
    return FeedbackService.submit_feedback(
        db=db,
        user_id=user_id,
        activity_id=request.activity_id,
        effectiveness_rating=request.effectiveness_rating,
        mood_before=request.mood_before,
        mood_after=request.mood_after,
        feedback_note=request.feedback_note,
        would_recommend=request.would_recommend,
    )

@router.get("/feedback/{user_id}/{activity_id}", description="Get user's own feedback for an activity")
def get_my_activity_feedback(user_id: int, activity_id: str, db: Session = Depends(get_db)):
    return FeedbackService.get_my_feedback(db, user_id, activity_id)

@router.get("/feedback/summary/{user_id}", description="Get all feedback submitted by a user")
def get_user_feedback_summary(user_id: int, db: Session = Depends(get_db)):
    return FeedbackService.get_user_feedback_summary(db, user_id)

@router.get("/effectiveness/{activity_id}", description="Get aggregated effectiveness data for an activity")
def get_activity_effectiveness(activity_id: str, db: Session = Depends(get_db)):
    return FeedbackService.get_activity_effectiveness(db, activity_id)

@router.get("/top-rated", description="Get top-rated activities based on community feedback")
def get_top_rated_activities(db: Session = Depends(get_db)):
    return FeedbackService.get_top_rated_activities(db)

@router.get("/{user_id}")
def get_user_recommended_activities(user_id: int, db: Session = Depends(get_db)):
    return ActivityService.get_user_recommended_activities(db, user_id)

@router.get("/{user_id}/category/{category_name}", description="Get a user's recommended activities filtered by category")
def get_user_recommended_activities_by_category(user_id: int, category_name: str, db: Session = Depends(get_db)):
    return ActivityService.get_user_recommended_activities_by_category(db, user_id, category_name)

@router.post("/complete/{user_id}", description="Log a completed activity for a user")
def complete_user_activity(user_id: int, request: CompleteActivityRequest, db: Session = Depends(get_db)):
    result = ActivityService.log_completed_activity(db, user_id, request.activity_id)
    # Auto-log for streak tracking & badge awarding
    new_badges = StreakService.log_activity(db, user_id, "activity_completed")
    if new_badges:
        result["new_badges"] = new_badges
    return result

@router.get("/completed/{user_id}", description="Get all activities completed by a user")
def get_user_completed_activities(user_id: int, db: Session = Depends(get_db)):
    return ActivityService.get_user_completed_activities(db, user_id)
