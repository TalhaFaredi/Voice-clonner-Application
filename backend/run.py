from app import create_app
from app.serving import server_options

app = create_app()

if __name__ == '__main__':
    from waitress import serve
    serve(app, **server_options())
