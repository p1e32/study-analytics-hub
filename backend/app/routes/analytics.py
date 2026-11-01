from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, func, Date

from app import db
from app.models import Subject, StudySession, Task
from app.constants import (
    DEFAULT_PERIOD,
    MINUTES_IN_HOUR,
    TASK_STATUS_DONE,
    VALID_PERIODS,
    VALID_TASK_STATUSES,
    WEEKLY_GOAL_PERIOD,
)
from app.utils.analytics import (
    calculate_percentage,
    calculate_streak,
    calculate_time_metrics,
    get_period_start,
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


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
            func.count(Task.id).filter(Task.status == TASK_STATUS_DONE).label('completed'),
        )
        .join(Subject, Task.subject_id == Subject.id)
        .where(Subject.user_id == user_id)
    )
    return db.session.execute(stmt).one()


def _get_weekly_goal_minutes(user_id: int) -> int:
    """Sum of target_hours_per_week over all subjects of the user, in minutes."""
    stmt = select(func.coalesce(func.sum(Subject.target_hours_per_week), 0)).where(Subject.user_id == user_id)
    return int(db.session.scalar(stmt)) * MINUTES_IN_HOUR


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


def _get_tasks_performance(user_id: int, status: str | None, subject_id: int | None):
    """
    One query for all tasks of the user together with the time really spent on them.

    - JOIN Subject: only tasks of this user (Subject.user_id) + subject data for the response.
    - OUTER JOIN StudySession: tasks that were never timed still appear (SUM is NULL -> 0).
    - GROUP BY: one row per task instead of one row per session.
    """
    actual_minutes = func.coalesce(func.sum(StudySession.duration_minutes), 0)

    stmt = (
        select(
            Task.id.label('task_id'),
            Task.title.label('task_title'),
            Task.status.label('status'),
            Task.estimated_minutes.label('estimated_minutes'),
            Subject.id.label('subject_id'),
            Subject.name.label('subject_name'),
            Subject.color.label('subject_color'),
            actual_minutes.label('actual_minutes'),
        )
        .join(Subject, Task.subject_id == Subject.id)
        .outerjoin(StudySession, StudySession.task_id == Task.id)
        .where(Subject.user_id == user_id)
        .group_by(Task.id, Subject.id)
        .order_by(Task.created_at.desc(), Task.id.desc())  # id = stable order for equal timestamps
    )
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if subject_id is not None:
        stmt = stmt.where(Task.subject_id == subject_id)

    return db.session.execute(stmt).all()


def _serialize_task_performance(row) -> dict:
    """Converts a DB row into the JSON contract of /tasks-performance."""
    actual = int(row.actual_minutes)
    difference, is_overdue = calculate_time_metrics(row.estimated_minutes, actual)
    return {
        'task_id': row.task_id,
        'task_title': row.task_title,
        'subject_id': row.subject_id,
        'subject_name': row.subject_name,
        'subject_color': row.subject_color,
        'status': row.status,
        'estimated_minutes': row.estimated_minutes,
        'actual_minutes': actual,
        'difference_minutes': difference,
        'is_overdue_time': is_overdue,
    }


# Endpoints
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
    minutes_last_week = _get_total_minutes(current_user_id, get_period_start(WEEKLY_GOAL_PERIOD))

    kpi = {
        'total_study_minutes': total_study_minutes,
        'total_tasks': task_stats.total,
        'completed_tasks': task_stats.completed,
        'weekly_goal_minutes': weekly_goal_minutes,
        'goal_progress_percent': calculate_percentage(minutes_last_week, weekly_goal_minutes),
        'current_streak_days': _get_current_streak(current_user_id),
    }

    return jsonify({'period': period, 'kpi': kpi, 'subjects': subjects}), 200


@analytics_bp.route('/tasks-performance', methods=['GET'])
@jwt_required()
def tasks_performance():
    current_user_id = int(get_jwt_identity())

    # status validation (optional)
    status = request.args.get('status')
    if status is not None and status not in VALID_TASK_STATUSES:
        return jsonify({'error': f"Invalid status. Must be one of: {', '.join(sorted(VALID_TASK_STATUSES))}"}), 400

    # subject_id validation (optional)
    subject_id = None
    raw_subject_id = request.args.get('subject_id')
    if raw_subject_id is not None:
        try:
            subject_id = int(raw_subject_id)
        except ValueError:
            return jsonify({'error': 'subject_id must be an integer'}), 400

    rows = _get_tasks_performance(current_user_id, status, subject_id)
    return jsonify([_serialize_task_performance(row) for row in rows]), 200
