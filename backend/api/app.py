from flask import Flask
from backend.api.routes.routes import subscription_blueprint
from backend.api.config import Config
from backend.db.models import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(subscription_blueprint, url_prefix='/api/subscriptions')

if __name__ == "__main__":
    app.run(debug=True)
