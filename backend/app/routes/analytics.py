from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, func, Date

from app import db
from app.models import Subject, StudySession, Task
from app.utils.analytics import (
    VALID_PERIODS,
    calculate_percentage,
    calculate_streak,
    get_period_start,
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

DEFAULT_PERIOD = 'week'
WEEK_PERIOD = 'week'


# Database queries (private helpers of this module)

def _get_minutes_per_subject(user_id: int, start_date: datetime | None) -> list[dict]:
    """
    Study minutes per subject, biggest first.
    Subjects without sessions in the period are still returned (with 0 minutes).
    """
    # The date filter lives in the JOIN condition (not in WHERE), otherwise the
    # LEFT JOIN would turn into an INNER JOIN and subjects with 0 minutes would disappear.
    join_condition = StudySession.subject_id == Subject.id
    if start_date is not None:
        join_condition &= StudySession.created_at >= start_date

    total_minutes = func.coalesce(func.sum(StudySession.duration_minutes), 0)

    stmt = (
        select(
            Subject.id,
            Subject.name,
            Subject.color,
            total_minutes.label('total_minutes'),
        )
        .outerjoin(StudySession, join_condition)
        .where(Subject.user_id == user_id)
        .group_by(Subject.id, Subject.name, Subject.color)
        .order_by(total_minutes.desc(), Subject.name)  # name = stable order for ties
    )
    return [dict(row) for row in db.session.execute(stmt).mappings()]


def _get_total_minutes(user_id: int, start_date: datetime | None) -> int:
    """Total study minutes of the user since start_date (all time if None)."""
    stmt = (
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .join(Subject, StudySession.subject_id == Subject.id)
        .where(Subject.user_id == user_id)
    )
    if start_date is not None:
        stmt = stmt.where(StudySession.created_at >= start_date)
    return int(db.session.scalar(stmt))


def _get_task_stats(user_id: int):
    """Returns a row with `.total` and `.completed` task counters."""
    stmt = (
        select(
            func.count(Task.id).label('total'),
            func.count(Task.id).filter(Task.status == 'done').label('completed'),
        )
        .join(Subject, Task.subject_id == Subject.id)
        .where(Subject.user_id == user_id)
    )
    return db.session.execute(stmt).one()


def _get_weekly_goal_minutes(user_id: int) -> int:
    """Sum of target_hours_per_week over all subjects of the user, in minutes."""
    stmt = select(func.coalesce(func.sum(Subject.target_hours_per_week), 0)).where(Subject.user_id == user_id)
    return int(db.session.scalar(stmt)) * 60


def _get_current_streak(user_id: int) -> int:
    """Number of consecutive days (up to today/yesterday) with at least one session."""
    study_day = func.date(StudySession.created_at, type_=Date)
    stmt = (
        select(study_day)
        .join(Subject, StudySession.subject_id == Subject.id)
        .where(Subject.user_id == user_id)
        .distinct()
        .order_by(study_day.desc())
    )
    return calculate_streak(list(db.session.scalars(stmt)))


# Endpoint
@analytics_bp.route('/summary', methods=['GET'])
@jwt_required()
def summary():
    current_user_id = int(get_jwt_identity())

    period = request.args.get('period', default=DEFAULT_PERIOD)
    if period not in VALID_PERIODS:
        return jsonify({'error': f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}"}), 400

    subjects = _get_minutes_per_subject(current_user_id, get_period_start(period))
    total_study_minutes = sum(s['total_minutes'] for s in subjects)
    for subject in subjects:
        subject['percentage'] = calculate_percentage(subject['total_minutes'], total_study_minutes)

    task_stats = _get_task_stats(current_user_id)

    # The goal is *weekly*, so progress is always measured over the last 7 days,
    # no matter which period was requested for the rest of the report.
    weekly_goal_minutes = _get_weekly_goal_minutes(current_user_id)
    minutes_last_week = _get_total_minutes(current_user_id, get_period_start(WEEK_PERIOD))

    kpi = {
        'total_study_minutes': total_study_minutes,
        'total_tasks': task_stats.total,
        'completed_tasks': task_stats.completed,
        'weekly_goal_minutes': weekly_goal_minutes,
        'goal_progress_percent': calculate_percentage(minutes_last_week, weekly_goal_minutes),
        'current_streak_days': _get_current_streak(current_user_id),
    }

    return jsonify({'period': period, 'kpi': kpi, 'subjects': subjects}), 200
