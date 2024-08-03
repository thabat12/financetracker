from flask import Flask
# from api.routes.routes import subscription_blueprint
from api.config import Config
from sqlalchemy import create_engine
# from db.models import db

app = Flask(__name__)
app.config.from_object(Config)
db_engine = create_engine()

# db.init_app(app)

# app.register_blueprint(subscription_blueprint, url_prefix='/api/subscriptions')

if __name__ == "__main__":
    app.run(debug=True)