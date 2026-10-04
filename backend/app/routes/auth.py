from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from app import db
from app.models import User
from email_validator import validate_email, EmailNotValidError

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def normalize_email(email: str) -> tuple[str | None, str | None]:
    """Validates and normalizes email."""
    if not isinstance(email, str):
        return None, "Email must be a string"
    try:
        valid = validate_email(email.strip(), check_deliverability=False)
        return valid.normalized, None
    except EmailNotValidError as e:
        return None, str(e)


def build_auth_response(user: User, status_code: int = 200):
    """Unified function for token generation and authorization response."""
    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token
    }), status_code


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    username = data.get('username', '').strip()
    password = data.get('password', '')
    raw_email = data.get('email', '').strip()

    if not username or not password or not raw_email:
        return jsonify({'error': 'Username, email and password are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400

    email, error = normalize_email(raw_email)
    if error:
        return jsonify({'error': error}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return build_auth_response(new_user, status_code=201)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    raw_email = data.get('email', '').strip()
    password = data.get('password', '')

    if not raw_email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    email, error = normalize_email(raw_email)
    if error:
        return jsonify({'error': error}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    return build_auth_response(user, status_code=200)

