from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from model.community import Community
from model.mood_checkin import MoodCheckIn, MoodType
from lib.activity.gmm_predictor import is_model_loaded as gmm_is_loaded
from lib.CBT.feed_ranker import rank_feed_posts, is_model_loaded as feed_ranker_loaded
from lib.CBT.reaction_service import ReactionService

class CommunityService:
    @staticmethod
    def get_user_community(db: Session, user_id: int):
        community = db.query(Community).filter(Community.user_id == user_id).first()
        if not community:
            return None

        return {
            "id": community.id,
            "community_name": community.community_name,
            "description": community.description,
            "user_id": community.user_id,
            "created_at": community.created_at,
            "clustering_method": "gmm" if gmm_is_loaded() else "rule_based"
        }

    @staticmethod
    def create_post(db: Session, user_id: int, community_id: int, post_type: str, paragraph: str):
        from model.post import Post, PostType
        from fastapi import HTTPException
        
        # Validate that the community exists
        community = db.query(Community).filter(Community.id == community_id).first()
        if not community:
            raise HTTPException(status_code=404, detail="Community not found")
            
        # Map string to Enum
        try:
            enum_post_type = PostType[post_type]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid post type. Must be one of: {[e.name for e in PostType]}")
            
        new_post = Post(
            post_type=enum_post_type,
            paragraph=paragraph,
            community_id=community_id,
            user_id=user_id
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return new_post

    @staticmethod
    def get_community_posts(db: Session, community_id: int, user_id: int):
        from model.post import Post
        from model.community import Community
        from model.users import User
        from fastapi import HTTPException
        
        # 1. Fetch the user's personal community allocation to verify access
        user_community = db.query(Community).filter(Community.user_id == user_id).first()
        if not user_community:
            raise HTTPException(status_code=403, detail="User is not part of any community")
            
        # 2. Verify the requested community_id exists
        target_community = db.query(Community).filter(Community.id == community_id).first()
        if not target_community:
            raise HTTPException(status_code=404, detail="Community not found")
            
        # 3. Security Check: The user's active community designation ("Growing", "Healing", etc.) 
        # MUST identically match the requested community record's designation.
        if user_community.community_name != target_community.community_name:
            raise HTTPException(status_code=403, detail="User does not have access to this community's posts")
            
        # 4. Grab all community_ids falling under this specific community_name banner
        matching_communities = db.query(Community.id).filter(
            Community.community_name == user_community.community_name
        ).all()
        valid_community_ids = [c[0] for c in matching_communities]
        
        # 5. Fetch posts securely and Join with the User model to fetch author names
        posts_query = (
            db.query(Post, User)
            .join(User, Post.user_id == User.id)
            .filter(Post.community_id.in_(valid_community_ids))
            .order_by(Post.created_at.desc())
            .all()
        )
        
        # 6. Structuring exact JSON shape matching the frontend image requirements
        formatted_posts = []
        for post, user in posts_query:
            formatted_posts.append({
                "id": post.id,
                "post_type": post.post_type.name if hasattr(post.post_type, 'name') else post.post_type,
                "paragraph": post.paragraph,
                "author_id": user.id,
                "author_name": getattr(user, 'guest_name', f"User {user.id}"),
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "likes": 0,
                "comments": 0,
            })

        # 6b. Enrich with reaction data
        post_ids = [p["id"] for p in formatted_posts]
        if post_ids:
            reactions_map = ReactionService.get_bulk_post_reactions(db, post_ids, user_id)
            for p in formatted_posts:
                rxn = reactions_map.get(p["id"], {})
                p["reactions"] = rxn.get("counts", [])
                p["my_reactions"] = rxn.get("my_reactions", [])
                p["total_reactions"] = rxn.get("total_reactions", 0)

        return formatted_posts

    @staticmethod
    def get_all_clusters_with_counts(db: Session):
        """Get all community clusters and their actual member counts."""
        from sqlalchemy import func
        from model.community import Community
        
        results = db.query(
            Community.community_name,
            func.count(Community.id).label('member_count')
        ).group_by(Community.community_name).all()
        
        return [{"name": row[0], "memberCount": row[1]} for row in results]

    @staticmethod
    def get_feed_for_user(db: Session, user_id: int):
        """Return the community feed for a user — looks up their community, then returns
        all posts across every community row that shares the same community_name (cluster).

        If the ML feed ranking model is loaded, posts are ranked by personalized
        relevance (70% relevance + 30% recency). Otherwise, chronological order."""
        from model.post import Post
        from model.users import User
        from model.activity_response import ActivityResponse
        from fastapi import HTTPException

        # 1. Find this user's community row
        user_community = db.query(Community).filter(Community.user_id == user_id).first()
        if not user_community:
            raise HTTPException(status_code=404, detail="User is not assigned to any community")

        community_name = user_community.community_name

        # 2. Expand to all community rows in the same cluster
        if community_name:
            matching_ids = [
                c[0] for c in db.query(Community.id)
                .filter(Community.community_name == community_name)
                .all()
            ]
        else:
            matching_ids = [user_community.id]

        if not matching_ids:
            return []

        # 3. Fetch posts (chronological as base)
        posts_query = (
            db.query(Post, User)
            .join(User, Post.user_id == User.id)
            .filter(Post.community_id.in_(matching_ids))
            .order_by(Post.created_at.desc())
            .all()
        )

        posts = [
            {
                "id": post.id,
                "post_type": post.post_type.name if hasattr(post.post_type, "name") else post.post_type,
                "paragraph": post.paragraph,
                "author_id": user.id,
                "author_name": getattr(user, "guest_name", f"User {user.id}"),
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "likes": 0,
                "comments": 0,
            }
            for post, user in posts_query
        ]

        # 3b. Enrich posts with reaction data (bulk fetch for efficiency)
        post_ids = [p["id"] for p in posts]
        if post_ids:
            reactions_map = ReactionService.get_bulk_post_reactions(db, post_ids, user_id)
            for p in posts:
                rxn = reactions_map.get(p["id"], {})
                p["reactions"] = rxn.get("counts", [])
                p["my_reactions"] = rxn.get("my_reactions", [])
                p["total_reactions"] = rxn.get("total_reactions", 0)

        # 4. ML-based personalized ranking (Component 4)
        if feed_ranker_loaded() and posts:
            # Get user's mental health scores from their latest activity response
            user_scores = CommunityService._get_user_scores(db, user_id)
            if user_scores:
                posts = rank_feed_posts(
                    posts=posts,
                    user_scores=user_scores,
                    relevance_weight=0.7
                )

        return posts

    @staticmethod
    def _get_user_scores(db: Session, user_id: int) -> dict:
        """Extract user's 7-dimensional mental health profile from their latest activity response."""
        from model.activity_response import ActivityResponse
        import json as json_lib

        response = db.query(ActivityResponse).filter(
            ActivityResponse.user_id == user_id
        ).order_by(ActivityResponse.id.desc()).first()

        if not response or not response.result_json:
            return None

        result = response.result_json
        if isinstance(result, str):
            try:
                result = json_lib.loads(result)
            except Exception:
                return None

        # Extract scores from the community_assignment or conditions_detected
        community_info = result.get('community_assignment', {})
        conditions = result.get('conditions_detected', [])
        filters = result.get('filters_applied', {})

        # Try to reconstruct the 7 scores
        stress = 50.0
        anxiety = 50.0
        depression = 50.0

        for cond in conditions:
            level = float(cond.get('level', 0))
            # Convert 0-10 scale to 0-100
            if level <= 10:
                level *= 10.0
            if cond['condition'] == 'stress':
                stress = level
            elif cond['condition'] == 'anxiety':
                anxiety = level
            elif cond['condition'] == 'depression':
                depression = level

        # Category scores from identified_problems
        problems = result.get('identified_problems', [])
        body = 50.0
        behavior = 50.0
        emotional = 50.0
        social = 50.0

        for prob in problems:
            score = float(prob.get('score', 50))
            cat = prob.get('category', '')
            if cat == 'body':
                body = score
            elif cat == 'behavior':
                behavior = score
            elif cat == 'social':
                social = score

        return {
            'stress_score': stress,
            'anxiety_score': anxiety,
            'depression_score': depression,
            'body_score': body,
            'behavior_score': behavior,
            'emotional_score': emotional,
            'social_score': social,
        }

    @staticmethod
    def get_posts_by_community(db: Session, community_id: int):
        """Return all posts for a community cluster (all rows sharing the same community_name)."""
        from model.post import Post
        from model.users import User
        from fastapi import HTTPException

        target_community = db.query(Community).filter(Community.id == community_id).first()
        if not target_community:
            raise HTTPException(status_code=404, detail="Community not found")

        community_name = target_community.community_name
        if not community_name:
            # No community_name assigned — return only this community's own posts
            matching_ids = [community_id]
        else:
            # Collect all community rows that share the same cluster name
            matching_ids = [
                c[0] for c in db.query(Community.id)
                .filter(Community.community_name == community_name)
                .all()
            ]

        if not matching_ids:
            return []

        posts_query = (
            db.query(Post, User)
            .join(User, Post.user_id == User.id)
            .filter(Post.community_id.in_(matching_ids))
            .order_by(Post.created_at.desc())
            .all()
        )

        posts_list = [
            {
                "id": post.id,
                "post_type": post.post_type.name if hasattr(post.post_type, "name") else post.post_type,
                "paragraph": post.paragraph,
                "author_id": user.id,
                "author_name": getattr(user, "guest_name", f"User {user.id}"),
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "likes": 0,
                "comments": 0,
            }
            for post, user in posts_query
        ]

        # Enrich with reaction data (no user context for public endpoint)
        post_ids = [p["id"] for p in posts_list]
        if post_ids:
            reactions_map = ReactionService.get_bulk_post_reactions(db, post_ids)
            for p in posts_list:
                rxn = reactions_map.get(p["id"], {})
                p["reactions"] = rxn.get("counts", [])
                p["my_reactions"] = []
                p["total_reactions"] = rxn.get("total_reactions", 0)

        return posts_list

    @staticmethod
    def get_community_users(db: Session, community_id: int):
        from model.community import Community
        from model.users import User
        from fastapi import HTTPException
        
        target_community = db.query(Community).filter(Community.id == community_id).first()
        if not target_community:
            raise HTTPException(status_code=404, detail="Community not found")
            
        users_query = (
            db.query(User.id, User.guest_name)
            .join(Community, Community.user_id == User.id)
            .filter(Community.community_name == target_community.community_name)
            .all()
        )
        
        return [{"user_id": u.id, "guest_name": u.guest_name} for u in users_query]

    # ================================================================
    # MOOD CHECK-IN PULSE
    # ================================================================

    @staticmethod
    def submit_mood_checkin(db: Session, user_id: int, mood: str):
        """Submit or update today's mood check-in for a user.
        Only one check-in per user per day (upsert pattern)."""
        from fastapi import HTTPException

        # Validate mood value
        valid_moods = [m.value for m in MoodType]
        if mood not in valid_moods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mood. Must be one of: {valid_moods}"
            )

        today = date.today()
        mood_enum = MoodType(mood)

        # Check if user already checked in today
        existing = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date == today
        ).first()

        if existing:
            # Update today's check-in
            existing.mood = mood_enum
            existing.created_at = datetime.now()
            db.commit()
            db.refresh(existing)
            return {
                "id": existing.id,
                "mood": existing.mood.value,
                "checkin_date": str(existing.checkin_date),
                "updated": True,
                "message": "Mood updated for today"
            }
        else:
            # Create new check-in
            new_checkin = MoodCheckIn(
                user_id=user_id,
                mood=mood_enum,
                checkin_date=today
            )
            db.add(new_checkin)
            db.commit()
            db.refresh(new_checkin)
            return {
                "id": new_checkin.id,
                "mood": new_checkin.mood.value,
                "checkin_date": str(new_checkin.checkin_date),
                "updated": False,
                "message": "Mood check-in recorded"
            }

    @staticmethod
    def get_my_mood_today(db: Session, user_id: int):
        """Get the user's mood check-in for today (or None if not submitted)."""
        today = date.today()
        checkin = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date == today
        ).first()

        if not checkin:
            return {"checked_in": False, "mood": None}

        return {
            "checked_in": True,
            "mood": checkin.mood.value,
            "checkin_date": str(checkin.checkin_date)
        }

    @staticmethod
    def get_community_mood_pulse(db: Session, user_id: int):
        """Get the aggregated mood pulse for the user's community today.
        Returns mood distribution and a summary message."""
        from fastapi import HTTPException

        # 1. Find user's community
        user_community = db.query(Community).filter(
            Community.user_id == user_id
        ).first()
        if not user_community:
            raise HTTPException(status_code=404, detail="User not in a community")

        community_name = user_community.community_name

        # 2. Get all user_ids in the same community
        community_user_ids = [
            c.user_id for c in db.query(Community).filter(
                Community.community_name == community_name
            ).all()
        ]

        if not community_user_ids:
            return {"total_checkins": 0, "distribution": {}, "message": "No data yet"}

        # 3. Count today's mood check-ins for this community
        today = date.today()
        checkins = db.query(
            MoodCheckIn.mood, func.count(MoodCheckIn.id)
        ).filter(
            MoodCheckIn.user_id.in_(community_user_ids),
            MoodCheckIn.checkin_date == today
        ).group_by(MoodCheckIn.mood).all()

        # 4. Build distribution
        mood_counts = {m.value: 0 for m in MoodType}
        total = 0
        for mood_val, count in checkins:
            mood_key = mood_val.value if hasattr(mood_val, 'value') else mood_val
            mood_counts[mood_key] = count
            total += count

        # 5. Calculate percentages
        distribution = {}
        for mood_key, count in mood_counts.items():
            distribution[mood_key] = {
                "count": count,
                "percentage": round((count / total * 100), 1) if total > 0 else 0.0
            }

        # 6. Generate a human-friendly summary message
        if total == 0:
            message = "No one in your community has checked in yet today. Be the first!"
        else:
            positive_count = mood_counts.get("great", 0) + mood_counts.get("good", 0)
            positive_pct = round(positive_count / total * 100) if total > 0 else 0
            if positive_pct >= 70:
                message = f"{positive_pct}% of your community is feeling good or great today!"
            elif positive_pct >= 50:
                message = f"{positive_pct}% of your community is having a positive day. You're not alone."
            elif positive_pct >= 30:
                message = f"It's a mixed day for your community. {total} members checked in — we're all in this together."
            else:
                message = f"Your community is having a tough day. {total} members checked in — let's support each other."

        # 7. Get user's own mood for context
        user_mood = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date == today
        ).first()

        return {
            "community_name": community_name,
            "total_checkins": total,
            "total_members": len(community_user_ids),
            "participation_rate": round((total / len(community_user_ids) * 100), 1) if community_user_ids else 0.0,
            "distribution": distribution,
            "message": message,
            "my_mood": user_mood.mood.value if user_mood else None
        }

    @staticmethod
    def get_my_mood_history(db: Session, user_id: int, days: int = 7):
        """Get the user's mood check-in history for the last N days."""
        from datetime import timedelta

        start_date = date.today() - timedelta(days=days - 1)
        checkins = db.query(MoodCheckIn).filter(
            MoodCheckIn.user_id == user_id,
            MoodCheckIn.checkin_date >= start_date
        ).order_by(MoodCheckIn.checkin_date.asc()).all()

        history = []
        for c in checkins:
            history.append({
                "date": str(c.checkin_date),
                "mood": c.mood.value
            })

        return {
            "user_id": user_id,
            "days": days,
            "history": history,
            "total_checkins": len(history)
        }