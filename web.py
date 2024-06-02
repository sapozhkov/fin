from app import create_app
from web import create_web
from app.config import AppConfig

app = create_app()
web = create_web(app)

if __name__ == '__main__':
    web.run(host='0.0.0.0', port=5001, debug=AppConfig.DEBUG_MODE)
