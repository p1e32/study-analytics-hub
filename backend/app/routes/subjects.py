import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import Subject

HOURS_IN_WEEK = 7 * 24  # 168 часов
HEX_COLOR_REGEX = re.compile(r'^#[0-9a-fA-F]{6}$')
DEFAULT_COLOR = '#3B82F6'

subjects_bp = Blueprint('subjects', __name__, url_prefix='/api/subjects')

@subjects_bp.route('/', methods=['GET'])
@jwt_required()
def get_subjects():
    current_user_id = int(get_jwt_identity())

    subjects = Subject.query.filter_by(user_id=current_user_id).all()
    return jsonify([s.to_dict() for s in subjects]), 200


@subjects_bp.route('/', methods=['POST'])
@jwt_required()
def create_subject():
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Name validation
    raw_name = data.get('name')
    if not isinstance(raw_name, str) or not raw_name.strip():
        return jsonify({'error': 'Subject name is required and cannot be empty'}), 400
    name = raw_name.strip()

    if len(name) > 100:
        return jsonify({'error': 'Subject name cannot exceed 100 characters'}), 400

    # Color validation
    raw_color = data.get('color')
    if raw_color is not None:
        if not isinstance(raw_color, str):
            return jsonify({'error': 'Color must be a string'}), 400
        color = raw_color.strip()
        if not HEX_COLOR_REGEX.match(color):
            return jsonify({'error': 'Invalid color format. Must be a 6-digit hex code like #3B82F6'}), 400
    else:
        color = DEFAULT_COLOR

    # Target hours per week validation
    raw_hours = data.get('target_hours_per_week')
    if raw_hours is not None:
        if isinstance(raw_hours, bool) or not isinstance(raw_hours, int):
            return jsonify({'error': 'target_hours_per_week must be an integer'}), 400
        if not (1 <= raw_hours <= HOURS_IN_WEEK):
            return jsonify({'error': f'target_hours_per_week must be between 1 and {HOURS_IN_WEEK}'}), 400
        target_hours = raw_hours
    else:
        target_hours = 5

    # Save to DB
    new_subject = Subject(
        user_id=current_user_id,
        name=name,
        color=color,
        target_hours_per_week=target_hours
    )
    db.session.add(new_subject)
    db.session.commit()

    return jsonify(new_subject.to_dict()), 201


@subjects_bp.route('/<int:subject_id>', methods=['DELETE'])
@jwt_required()
def delete_subject(subject_id):
    current_user_id = int(get_jwt_identity())

    subject = Subject.query.filter_by(id=subject_id, user_id=current_user_id).first()
    if not subject:
        return jsonify({'error': 'Subject not found'}), 404

    if subject.user_id != current_user_id:
        return jsonify({'error': 'You are not authorized to delete this subject'}), 403

    db.session.delete(subject)
    db.session.commit()

    return jsonify({'message': 'Subject deleted successfully'}), 200

