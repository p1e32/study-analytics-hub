from sqlalchemy import select

from app import db
from app.models import Task, Subject


def get_user_task(task_id: int, user_id: int) -> Task | None:
    """Returns a Task owned by user_id, or None if not found / access denied."""
    stmt = select(Task).join(Subject).where(Task.id == task_id, Subject.user_id == user_id)
    return db.session.execute(stmt).scalar_one_or_none()


def get_user_subject(subject_id: int, user_id: int) -> Subject | None:
    """Returns a Subject owned by user_id, or None if not found / access denied."""
    stmt = select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
    return db.session.execute(stmt).scalar_one_or_none()


def task_belongs_to_subject(task_id: int, subject_id: int, user_id: int) -> bool:
    """
    Returns True if the task exists, belongs to subject_id,
    and that subject belongs to user_id. False otherwise.
    """
    stmt = (
        select(Task)
        .join(Subject)
        .where(
            Task.id == task_id,
            Task.subject_id == subject_id,
            Subject.user_id == user_id,
        )
    )
    return db.session.execute(stmt).scalar_one_or_none() is not None
