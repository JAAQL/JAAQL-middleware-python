from jaaql.jaaql import create_app

if __name__ == '__main__':
    port, flask_app = create_app()
    flask_app.run(port=port, host="0.0.0.0", threaded=True)
else:
    def build_app(*args, **kwargs):
        return create_app(was_gunicorn=True, **kwargs)
