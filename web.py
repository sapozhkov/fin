from app import create_app, AppConfig

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=AppConfig.DEBUG_MODE)
