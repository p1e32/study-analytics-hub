from datetime import datetime, timezone
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db


class User(db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    subjects: Mapped[list['Subject']] = relationship(
        back_populates='user',
        cascade='all, delete-orphan'
    )
    settings: Mapped[Optional['Settings']] = relationship(
        back_populates='user',
        cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        """Hashes the password before saving to the database"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Compares the entered password with the saved hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Subject(db.Model):
    __tablename__ = 'subjects'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default='#3B82F6')
    target_hours_per_week: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped['User'] = relationship(back_populates='subjects')
    tasks: Mapped[list['Task']] = relationship(
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    study_sessions: Mapped[list['StudySession']] = relationship(
        back_populates='subject',
        cascade='all, delete-orphan'
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'target_hours_per_week': self.target_hours_per_week,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Settings(db.Model):
    __tablename__ = 'settings'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    university_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=120)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='settings')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'university_name': self.university_name,
            'country': self.country,
            'daily_goal_minutes': self.daily_goal_minutes
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='todo')  # 'todo', 'in_progress', 'done'
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    subject: Mapped['Subject'] = relationship(back_populates='tasks')
    study_sessions: Mapped[list['StudySession']] = relationship(back_populates='task')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'title': self.title,
            'status': self.status,
            'estimated_minutes': self.estimated_minutes,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StudySession(db.Model):
    __tablename__ = 'study_sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    subject: Mapped['Subject'] = relationship(back_populates='study_sessions')
    task: Mapped[Optional['Task']] = relationship(back_populates='study_sessions')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'task_id': self.task_id,
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
