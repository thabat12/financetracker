from flask import Blueprint, jsonify, request
from models import db, Subscription

subscription_blueprint = Blueprint('subscriptions', __name__)

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
    db.session.add(new_subscription)
    db.session.commit()
    return jsonify(new_subscription.to_dict()), 201

@subscription_blueprint.route('/<int:id>', methods=['DELETE'])
def delete_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    db.session.delete(subscription)
    db.session.commit()
    return '', 204
