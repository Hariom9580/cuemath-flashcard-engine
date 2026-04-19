import os

from dotenv import load_dotenv
from flask import Flask

from .db import init_db
from .routes import register_routes


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        DATABASE_PATH=os.path.join(app.instance_path, "flashcards.db"),
        DEFAULT_MAX_CARDS=30,
        MAX_UPLOAD_MB=20,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    init_db(app.config["DATABASE_PATH"])
    register_routes(app)
    return app
