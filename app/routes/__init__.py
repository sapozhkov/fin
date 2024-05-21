from .common import bp as common_bp
from .instruments import bp as instruments_bp
from .runs import bp as runs_bp
from .deals import bp as deals_bp


def register_blueprints(app):
    app.register_blueprint(common_bp)
    app.register_blueprint(instruments_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(deals_bp)
