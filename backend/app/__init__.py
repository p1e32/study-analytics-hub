from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # blueprints init
    from app.routes.subjects import subjects_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(subjects_bp)
    app.register_blueprint(auth_bp)

    return app