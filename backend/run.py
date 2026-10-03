from app import create_app, db
from app import models

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Creates tables
        db.create_all()
        print("Tables created.")

    app.run(debug=True, port=5000)