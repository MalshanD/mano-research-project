from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from schemas.chat.chatInputSchema import ChatRequest, ChatResponse
from lib.chat.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/session/create/{user_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Creates a new chat session and returns a unique session ID.",
)
async def create_session(user_id: int, db: Session = Depends(get_db)):
    """Create a new chat session in the database."""
    return await chat_service.create_session(db, user_id)


@router.get(
    "/session/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get all chat sessions for a user",
    description="Retrieves a list of all chat sessions for a given user ID.",
)
async def get_all_sessions(user_id: int, db: Session = Depends(get_db)):
    """Get all chat sessions for a specific user."""
    return await chat_service.get_all_sessions(db, user_id)


@router.delete(
    "/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a chat session",
    description="Deletes a chat session and all its associated messages.",
)
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a chat session by ID."""
    deleted = await chat_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"message": "Chat session deleted successfully"}


@router.get(
    "/message/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Get all messages for a session",
    description="Retrieves a list of all chat messages for a given session ID.",
)
async def get_all_messages(session_id: int, db: Session = Depends(get_db)):
    """Get all chat messages for a specific session."""
    return await chat_service.get_all_messages_by_session(db, session_id)



@router.post(
    "/message",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a chat message",
    description=(
        "Send a user message and receive a bot response. "
        "The intent is classified using a BERT model and the response "
        "is generated using a hybrid (template + generative) engine."
    ),
)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Accept a user message, classify intent, generate a bot response,
    and persist both messages into the database.
    """
    try:
        response_data = await chat_service.process_message(
            db=db,
            session_id=request.session_id,
            message=request.message,
            persona=request.persona,
        )
        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing error: {str(e)}",
        )
