from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select

from app import db
from app.models import StudySession, Subject
from app.utils.db_helpers import task_belongs_to_subject, get_user_subject

timer_bp = Blueprint('timer', __name__, url_prefix='/api/timer')

# Limits and constraints
DEFAULT_SESSIONS_LIMIT = 10
MAX_SESSIONS_LIMIT = 50
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 720


def validate_int_field(value, field_name: str, required: bool = True) -> tuple[int | None, str | None]:
    """Validates that a field is an integer and not a boolean."""
    if value is None:
        if required:
            return None, f'{field_name} is required'
        return None, None
    if type(value) is not int:
        return None, f'{field_name} must be an integer'
    return value, None


@timer_bp.route('/sessions', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_sessions():
    current_user_id = int(get_jwt_identity())

    limit = DEFAULT_SESSIONS_LIMIT
    raw_limit = request.args.get('limit')
    if raw_limit is not None:
        try:
            limit = int(raw_limit)
        except ValueError:
            return jsonify({'error': 'limit must be an integer'}), 400
        if not (1 <= limit <= MAX_SESSIONS_LIMIT):
            return jsonify({'error': f'limit must be between 1 and {MAX_SESSIONS_LIMIT}'}), 400

    stmt = (
        select(StudySession)
        .join(Subject)
        .where(Subject.user_id == current_user_id)
        .order_by(StudySession.created_at.desc())
        .limit(limit)
    )
    sessions = db.session.scalars(stmt).all()

    return jsonify([session.to_dict() for session in sessions]), 200


@timer_bp.route('/sessions', methods=['POST'], strict_slashes=False)
@jwt_required()
def create_session():
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Validate duration_minutes
    duration_minutes, err = validate_int_field(data.get('duration_minutes'), 'duration_minutes')
    if err or duration_minutes is None:
        return jsonify({'error': err}), 400
    if not (MIN_DURATION_MINUTES <= duration_minutes <= MAX_DURATION_MINUTES):
        return jsonify({'error': f'duration_minutes must be between {MIN_DURATION_MINUTES} and {MAX_DURATION_MINUTES}'}), 400

    # Validate subject_id
    subject_id, err = validate_int_field(data.get('subject_id'), 'subject_id')
    if err or subject_id is None:
        return jsonify({'error': err}), 400
    if get_user_subject(subject_id, current_user_id) is None:
        return jsonify({'error': 'This subject does not exist or you do not have access to it'}), 400

    # Validate optional task_id
    task_id, err = validate_int_field(data.get('task_id'), 'task_id', required=False)
    if err:
        return jsonify({'error': err}), 400
    if task_id is not None and not task_belongs_to_subject(task_id, subject_id, current_user_id):
        return jsonify({'error': 'This task does not exist or does not belong to the given subject'}), 400

    new_study_session = StudySession(
        subject_id=subject_id,
        duration_minutes=duration_minutes,
        task_id=task_id,
    )
    db.session.add(new_study_session)
    db.session.commit()

    return jsonify(new_study_session.to_dict()), 201
