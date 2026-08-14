import os
from app import create_app, db

app = create_app(os.environ.get("FLASK_CONFIG", "default"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False
    )
