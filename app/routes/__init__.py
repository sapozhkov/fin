from .common import bp as common_bp


def register_blueprints(app):
    app.register_blueprint(common_bp)
