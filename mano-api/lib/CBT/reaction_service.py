"""Service for managing post reactions (emoji-based reactions beyond simple likes)."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from model.post_reaction import PostReaction, ReactionType, REACTION_CATALOG


class ReactionService:

    @staticmethod
    def toggle_reaction(db: Session, user_id: int, post_id: int, reaction_type_str: str):
        """Toggle a reaction on a post.
        If the user already has this reaction → remove it.
        If the user doesn't have it → add it.
        Returns the current state after toggling."""
        from fastapi import HTTPException

        # Validate reaction type
        try:
            reaction_enum = ReactionType(reaction_type_str)
        except ValueError:
            valid = [r.value for r in ReactionType]
            raise HTTPException(status_code=400, detail=f"Invalid reaction type. Must be one of: {valid}")

        # Check existing
        existing = db.query(PostReaction).filter(
            PostReaction.user_id == user_id,
            PostReaction.post_id == post_id,
            PostReaction.reaction_type == reaction_enum,
        ).first()

        if existing:
            # Remove the reaction (toggle off)
            db.delete(existing)
            db.commit()
            action = "removed"
        else:
            # Add the reaction (toggle on)
            new_reaction = PostReaction(
                user_id=user_id,
                post_id=post_id,
                reaction_type=reaction_enum,
            )
            db.add(new_reaction)
            db.commit()
            action = "added"

        # Return updated counts for this post
        counts = ReactionService._get_reaction_counts(db, post_id)
        my_reactions = ReactionService._get_user_reactions(db, user_id, post_id)

        return {
            "action": action,
            "reaction_type": reaction_type_str,
            "counts": counts,
            "my_reactions": my_reactions,
        }

    @staticmethod
    def get_post_reactions(db: Session, post_id: int, user_id: int = None):
        """Get all reaction counts for a post, plus which ones the user has given."""
        counts = ReactionService._get_reaction_counts(db, post_id)
        my_reactions = []
        if user_id:
            my_reactions = ReactionService._get_user_reactions(db, user_id, post_id)

        total = sum(c["count"] for c in counts)

        return {
            "post_id": post_id,
            "total_reactions": total,
            "counts": counts,
            "my_reactions": my_reactions,
        }

    @staticmethod
    def get_bulk_post_reactions(db: Session, post_ids: list, user_id: int = None):
        """Get reactions for multiple posts at once (efficient for feed rendering).
        Returns a dict keyed by post_id."""
        if not post_ids:
            return {}

        # Aggregate counts per post per reaction type
        counts_query = (
            db.query(
                PostReaction.post_id,
                PostReaction.reaction_type,
                func.count(PostReaction.id).label("count"),
            )
            .filter(PostReaction.post_id.in_(post_ids))
            .group_by(PostReaction.post_id, PostReaction.reaction_type)
            .all()
        )

        # User's own reactions
        user_reactions_query = []
        if user_id:
            user_reactions_query = (
                db.query(PostReaction.post_id, PostReaction.reaction_type)
                .filter(
                    PostReaction.post_id.in_(post_ids),
                    PostReaction.user_id == user_id,
                )
                .all()
            )

        # Build per-post dicts
        result = {}
        for pid in post_ids:
            result[pid] = {"counts": [], "my_reactions": [], "total_reactions": 0}

        for post_id, reaction_type, count in counts_query:
            catalog = REACTION_CATALOG.get(reaction_type, {})
            result[post_id]["counts"].append({
                "type": reaction_type.value,
                "emoji": catalog.get("emoji", ""),
                "label": catalog.get("label", ""),
                "count": count,
            })
            result[post_id]["total_reactions"] += count

        for post_id, reaction_type in user_reactions_query:
            result[post_id]["my_reactions"].append(reaction_type.value)

        # Sort counts by count descending within each post
        for pid in post_ids:
            result[pid]["counts"].sort(key=lambda x: x["count"], reverse=True)

        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_reaction_counts(db: Session, post_id: int):
        """Get aggregated reaction counts for a single post."""
        rows = (
            db.query(
                PostReaction.reaction_type,
                func.count(PostReaction.id).label("count"),
            )
            .filter(PostReaction.post_id == post_id)
            .group_by(PostReaction.reaction_type)
            .all()
        )

        counts = []
        for reaction_type, count in rows:
            catalog = REACTION_CATALOG.get(reaction_type, {})
            counts.append({
                "type": reaction_type.value,
                "emoji": catalog.get("emoji", ""),
                "label": catalog.get("label", ""),
                "count": count,
            })

        # Sort by count descending
        counts.sort(key=lambda x: x["count"], reverse=True)
        return counts

    @staticmethod
    def _get_user_reactions(db: Session, user_id: int, post_id: int):
        """Get list of reaction types the user has given to a post."""
        rows = (
            db.query(PostReaction.reaction_type)
            .filter(
                PostReaction.user_id == user_id,
                PostReaction.post_id == post_id,
            )
            .all()
        )
        return [r[0].value for r in rows]
