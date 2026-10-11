from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select

from app import db
from app.models import Task, Subject

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

VALID_STATUSES = {'todo', 'in_progress', 'done'}

@tasks_bp.route('/', methods=['GET'])
@jwt_required()
def get_tasks():
    current_user_id = int(get_jwt_identity())

    stmt = select(Task).join(Subject).where(Subject.user_id == current_user_id)

    status = request.args.get('status')
    if status is not None:
        if status not in VALID_STATUSES:
            return jsonify({'error': f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}), 400
        stmt = stmt.where(Task.status == status)

    raw_subject_id = request.args.get('subject_id')
    if raw_subject_id is not None:
        try:
            subject_id = int(raw_subject_id)
        except ValueError:
            return jsonify({'error': 'subject_id must be an integer'}), 400
        stmt = stmt.where(Task.subject_id == subject_id)

    stmt = stmt.order_by(Task.deadline.asc().nulls_last())

    tasks = db.session.scalars(stmt).all()
    return jsonify([task.to_dict() for task in tasks]), 200

@tasks_bp.route('/', methods=['POST'])
@jwt_required()
def create_task():
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Title validation
    raw_title = data.get('title')
    if not isinstance(raw_title, str) or not raw_title.strip():
        return jsonify({'error': 'Title name is required and cannot be empty'}), 400
    title = raw_title.strip()

    if len(title) > 100:
        return jsonify({'error': 'Title name cannot exceed 100 characters'}), 400

    # Subject_id validation
    subject_id = data.get('subject_id')
    if subject_id is not None:
        if not isinstance(subject_id, int):
            return jsonify({'error': 'subject_id must be an integer'}), 400
    else:
        return jsonify({'error': 'subject_id is required'}), 400

    stmt = select(Subject).where(Subject.id == subject_id, Subject.user_id == current_user_id)
    subject = db.session.execute(stmt).scalar_one_or_none()
    if subject is None:
        return jsonify({'error': 'This subject does not exist or you do not have access to it'}), 400

    # Estimated minutes validation
    estimated_minutes = data.get('estimated_minutes')
    if estimated_minutes is not None:
        if isinstance(estimated_minutes, bool) or not isinstance(estimated_minutes, int):
            return jsonify({'error': 'estimated_minutes must be an integer'}), 400
        if not 1 <= estimated_minutes:
            return jsonify({'error': 'estimated_minutes must be at least 1'}), 400

    # Deadline validation
    raw_deadline = data.get('deadline')
    deadline = None
    if raw_deadline is not None:
        if not isinstance(raw_deadline, str):
            return jsonify({'error': 'deadline must be a string'}), 400
        try:
            deadline = datetime.fromisoformat(raw_deadline)
        except ValueError:
            return jsonify({'error': 'deadline must be in the format YYYY-MM-DDTHH:MM:SS'}), 400

    # Save to DB
    new_task = Task(
        subject_id=subject_id,
        title=title,
        estimated_minutes=estimated_minutes,
        deadline=deadline
    )
    db.session.add(new_task)
    db.session.commit()

    return jsonify(new_task.to_dict()), 201


@tasks_bp.route('/<int:task_id>', methods=['PATCH'])
@jwt_required()
def change_task(task_id: int):
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Task id validation
    stmt = select(Task).join(Subject).where(Task.id == task_id, Subject.user_id == current_user_id)
    task = db.session.execute(stmt).scalar_one_or_none()
    if task is None:
        return jsonify({'error': 'This task does not exist or you do not have access to it'}), 404

    # Status validation
    if 'status' in data and data['status'] is not None:
        status = data['status']
        if status not in VALID_STATUSES:
            return jsonify({'error': f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}), 400
        task.status = status

    # Title validation
    if 'title' in data and data['title'] is not None:
        title = data['title']
        if not isinstance(title, str) or not title.strip():
            return jsonify({'error': 'Title cannot be empty'}), 400
        if len(title.strip()) > 100:
            return jsonify({'error': 'Title cannot exceed 100 characters'}), 400
        task.title = title.strip()

    # Estimated minutes validation
    if 'estimated_minutes' in data:
        est = data['estimated_minutes']
        if est is not None:
            if not isinstance(est, int) or isinstance(est, bool) or est < 1:
                return jsonify({'error': 'estimated_minutes must be a non-negative integer'}), 400
        task.estimated_minutes = est

    # Deadline validation
    if 'deadline' in data:
        raw_deadline = data['deadline']
        if raw_deadline is not None:
            try:
                task.deadline = datetime.fromisoformat(raw_deadline)
            except (ValueError, TypeError):
                return jsonify({'error': 'deadline must be a valid ISO 8601 string'}), 400
        else:
            task.deadline = None

    db.session.commit()

    return jsonify(task.to_dict()), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id: int):
    current_user_id = int(get_jwt_identity())

    stmt = select(Task).join(Subject).where(Task.id == task_id, Subject.user_id == current_user_id)
    task = db.session.execute(stmt).scalar_one_or_none()
    if task is None:
        return jsonify({'error': 'This task does not exist or you do not have access to it'}), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({'message': 'Task deleted successfully'}), 200
