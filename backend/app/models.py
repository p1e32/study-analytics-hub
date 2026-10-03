from datetime import datetime
from app import db


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), default='#3B82F6')
    target_hours_per_week = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='subject', cascade='all, delete-orphan', lazy=True)
    study_sessions = db.relationship('StudySession', backref='subject', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'target_hours_per_week': self.target_hours_per_week,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='todo')  # 'todo', 'in_progress', 'done'
    estimated_minutes = db.Column(db.Integer, nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    study_sessions = db.relationship('StudySession', backref='task', lazy=True)

    def to_dict(self):
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

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'task_id': self.task_id,
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Settings(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(150), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    daily_goal_minutes = db.Column(db.Integer, default=120)

    def to_dict(self):
        return {
            'id': self.id,
            'university_name': self.university_name,
            'country': self.country,
            'daily_goal_minutes': self.daily_goal_minutes
        }