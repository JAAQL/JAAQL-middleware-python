from jaaql.jaaql import create_app
import jaaql.documentation as documentation

if __name__ == '__main__':
    port, flask_app = create_app(supplied_documentation=documentation)
    flask_app.run(port=port, host="0.0.0.0", threaded=True)
else:
    def build_app(*args, **kwargs):
        return create_app(is_gunicorn=True, **kwargs)
