from flask import Flask, jsonify, request
from api.routes.routes import subscription_blueprint
from api.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db.models import *
import requests

app = Flask(__name__)
app.config.from_object(Config)
db_engine = create_engine()

# app.register_blueprint(subscription_blueprint, url_prefix='/api/subscriptions')
@subscription_blueprint.route('/', methods=['GET'])
def get_subscriptions():
    subscriptions = Subscription.query.all()
    return jsonify([subscription.to_dict() for subscription in subscriptions])

@subscription_blueprint.route('/', methods=['POST'])
def add_subscription():
    data = request.get_json()
    new_subscription = Subscription(
        name=data['name'],
        price=data['price'],
        renewal_date=data['renewal_date']
    )
    return jsonify(new_subscription.to_dict()), 201

@subscription_blueprint.route('/<int:id>', methods=['DELETE'])
def delete_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    return '', 204





if __name__ == "__main__":
    app.run(debug=True)