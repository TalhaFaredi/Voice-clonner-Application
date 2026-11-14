"""Independent voice SaaS API application factory."""
import logging
import time
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import Settings
from .models.database import init_database


def create_app(overrides=None):
    app = Flask(__name__)
    class PaymentRequired(HTTPException):
        code = 402
        description = 'Insufficient credits.'
    app.aborter.mapping[402] = PaymentRequired
    app.config.from_object(Settings)
    if overrides:
        app.config.update(overrides)
    init_database(app)
    from .routes import auth, library, billing
    app.register_blueprint(auth.bp, url_prefix="/api")
    app.register_blueprint(library.bp, url_prefix="/api")
    app.register_blueprint(billing.bp, url_prefix="/api")
    from .middleware.security import before_request
    app.before_request(before_request)

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', service='mellifon', time=time.time())

    @app.after_request
    def headers(response):
        origin = request.headers.get('Origin')
        if origin in app.config['ALLOWED_ORIGINS']:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRF-Token, Idempotency-Key'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PATCH,DELETE,OPTIONS'
            response.headers.add('Vary', 'Origin')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control'] = 'no-store'
        if app.config['APP_ENV'] == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception('Request failed')
        return jsonify(error='Something went wrong. Please try again.'), 500

    logging.basicConfig(level=logging.INFO)
    return app
