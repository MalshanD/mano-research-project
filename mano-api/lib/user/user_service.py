"""User authentication service — handles both login and registration.

Design decision: login and registration are combined into a single endpoint
(create_user). If the guest_name already exists, it verifies the password
and logs in. If not, it creates a new account. This simplifies the frontend
flow to a single form.
"""
from sqlalchemy.orm import Session
from model.users import User
from schemas.user import userInSchema as UIS
from util.security import hash_password, verify_password
from fastapi import HTTPException, status


async def create_user(db: Session, data: UIS.UserIn):
    """Create a new user or log in an existing one.

    Args:
        db: SQLAlchemy database session.
        data: Pydantic schema with guest_name and password.

    Returns:
        Dict with message, user_id, and guest_name.

    Raises:
        HTTPException 401: If the guest_name exists but the password is wrong.
    """
    # 1. Check if a user with this guest_name already exists
    existing_user = db.query(User).filter(
        User.guest_name == data.guest_name
    ).first()

    # 2. User exists → verify password and log them in
    if existing_user:
        if verify_password(data.password, existing_user.password):
            return {
                "message": "Login successful",
                "user_id": existing_user.id,
                "guest_name": existing_user.guest_name,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this guest name."
            )

    # 3. User does NOT exist → hash password and create new account
    hashed_password = hash_password(data.password)

    new_user = User(
        guest_name=data.guest_name,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Populate the auto-generated id

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "guest_name": new_user.guest_name,
    }
