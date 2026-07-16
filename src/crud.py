# Phase 3 - crud.py
# All database query functions (Create, Read)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Message


async def get_user_id_by_email(db: AsyncSession, email: str) -> int | None:
    """Check if a user exists by email and return their user_id, else None."""
    result = await db.execute(
        select(User.id).where(User.email == email)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, email: str) -> User:
    """Start a new chat session for a user."""
    user = User(email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def save_message(db: AsyncSession, user_id: int, role: str, content: str) -> Message:
    """Persist a single message."""
    msg = Message(user_id=user_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_history(db: AsyncSession, user_id: int) -> list[Message]:
    """Return all messages for a session, oldest first."""
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


# async def get_sessions_by_email(db: AsyncSession, email: str) -> list[ChatSession]:
#     """Return all sessions for a given email, newest first."""
#     result = await db.execute(
#         select(ChatSession)
#         .where(ChatSession.email == email)
#         .order_by(ChatSession.created_at.desc())
#     )
#     return list(result.scalars().all())
