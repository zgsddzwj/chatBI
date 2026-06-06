"""反馈接口：对话质量评分。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_app_db
from app.models import Feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    message_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: int
    message_id: int
    rating: int
    comment: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=FeedbackOut)
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_app_db)):
    fb = Feedback(
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/message/{message_id}", response_model=FeedbackOut | None)
def get_feedback(message_id: int, db: Session = Depends(get_app_db)):
    return db.query(Feedback).filter(Feedback.message_id == message_id).first()
