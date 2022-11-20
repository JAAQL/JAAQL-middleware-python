from jaaql.jaaql import create_app


def build_app(*args, **kwargs):
    return create_app(**kwargs)


if __name__ == '__main__':
    build_app()
