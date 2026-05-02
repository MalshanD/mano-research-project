"""
DB adapter for the Risk Trajectory Tracking feature.

This module is the ONLY place trajectory code talks to SQLAlchemy. The
core analysis (``lib.assesment.trajectory``) is kept DB-free so it can be
unit-tested without a database fixture. Anything in this file that needs
the ORM lives here.

Flow
----
1. Load the user's ``Response`` rows (oldest → newest) from the DB.
2. Validate the user exists — mirror the error contract of
   ``response_service.get_response_history`` so callers see consistent
   404s when the user is absent but an empty history when the user is
   known-but-new.
3. Convert each row to three ``SessionPoint``s (one per head).
4. Delegate to ``trajectory.analyse_all_conditions`` and return a
   fully-serialisable payload.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.response import Response
from model.users import User
from lib.assesment import trajectory as T
from lib.assesment.trajectory import (
    DEFAULT_GAP_RESET_DAYS,
    DEFAULT_WINDOW_SIZE,
    SessionPoint,
)


def _load_response_rows(db: Session, user_id: int) -> List[Response]:
    """Fetch all of a user's Response rows oldest → newest.

    Raises 404 if the user doesn't exist. Returns an empty list for a
    user with no history yet — the trajectory module handles that
    gracefully via the "Establishing baseline" path.
    """
    user_exists = db.query(User.id).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return (
        db.query(Response)
        .filter(Response.user_id == user_id)
        .order_by(Response.created_at.asc(), Response.id.asc())
        .all()
    )


def _rows_to_history(rows: List[Response]) -> Dict[str, List[SessionPoint]]:
    """Split one flat list of rows into three per-head time series.

    We skip rows where the per-head score is None — older schemas or
    partial saves shouldn't poison the slope math.
    """
    history: Dict[str, List[SessionPoint]] = {
        "stress": [], "anxiety": [], "depression": [],
    }
    for row in rows:
        ts = row.created_at
        if ts is None:
            continue  # defensive — created_at has a default, but never trust

        if row.stress_score is not None:
            history["stress"].append(SessionPoint(timestamp=ts, score=float(row.stress_score)))
        if row.anxiety_score is not None:
            history["anxiety"].append(SessionPoint(timestamp=ts, score=float(row.anxiety_score)))
        if row.depression_score is not None:
            history["depression"].append(SessionPoint(timestamp=ts, score=float(row.depression_score)))
    return history


def build_history_from_rows(rows: List[Response]) -> Dict[str, List[SessionPoint]]:
    """Public-for-tests alias for ``_rows_to_history``."""
    return _rows_to_history(rows)


def get_user_trajectory(
    db: Session,
    user_id: int,
    window_size: int = DEFAULT_WINDOW_SIZE,
    gap_reset_days: int = DEFAULT_GAP_RESET_DAYS,
) -> Dict:
    """Return a fully-serialisable trajectory payload for one user.

    Payload shape (keys stable — UI / dashboard contracts live on this):
    {
      "user_id": int,
      "total_sessions": int,               # total Response rows
      "window_size": int,
      "gap_reset_days": int,
      "per_head": {
        "stress":      {... TrajectoryResult.to_dict() ...},
        "anxiety":     {...},
        "depression":  {...},
      },
      "any_alert": bool,                   # any head has an alert/worsening flag
      "alerts": [str, ...],                # flattened alert strings for quick UI hookup
    }
    """
    rows = _load_response_rows(db, user_id)
    history = _rows_to_history(rows)
    results = T.analyse_all_conditions(
        history, window_size=window_size, gap_reset_days=gap_reset_days,
    )

    per_head = {head: r.to_dict() for head, r in results.items()}
    alerts = [r.alert for r in results.values() if r.alert]
    any_alert = bool(alerts) or any(r.worsening_in_low_flag for r in results.values())

    return {
        "user_id": user_id,
        "total_sessions": len(rows),
        "window_size": window_size,
        "gap_reset_days": gap_reset_days,
        "per_head": per_head,
        "any_alert": any_alert,
        "alerts": alerts,
    }
