from flask import Flask
from config import Config
from models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Create default categories if they don't exist
        from models import Category
        if not Category.query.first():
            default_categories = ['Food', 'Transport', 'Entertainment', 'Utilities', 'Rent', 'Other']
            for cat_name in default_categories:
                db.session.add(Category(name=cat_name))
            db.session.commit()

    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
