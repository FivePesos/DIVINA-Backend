"""
Store routes
    GET    /api/stores                        - list all active stores (public)
    GET    /api/stores/map                    - all stores with coordinates for map
    GET    /api/stores/<id>                   - get store details with schedules
    POST   /api/stores                        - create store (approved dive operator only)
    PUT    /api/stores/<id>                   - update store (owner or admin)
    DELETE /api/stores/<id>                   - deactivate store (owner or admin)

Schedule routes
    GET    /api/stores/<id>/schedules         - list schedules for a store
    POST   /api/stores/<id>/schedules         - add schedule (owner or admin)
    PUT    /api/stores/<id>/schedules/<sid>   - update schedule (owner or admin)
    DELETE /api/stores/<id>/schedules/<sid>   - cancel schedule (owner or admin)
"""
from datetime import datetime, date, time
from flask import Blueprint, request, jsonify
from app import db
from app.models.store import Store, DivingSchedule
from app.models.user import UserRole, VerificationStatus
from app.utils.jwt_helper import jwt_required

store_bp = Blueprint("stores", __name__)

def _is_store_owner_or_admin(user, store):
    return user.role == UserRole.ADMIN or store.owner_id == user.id


@store_bp.route("/stores", methods=["GET"])
def get_all_stores():

    stores = Store.query.filter_bu(is_active=True).order_by(Store.created_at.desc()).all()
    return jsonify({
        "total": len(stores),
        "stores": [s.to_dict() for s in stores],
    }), 200