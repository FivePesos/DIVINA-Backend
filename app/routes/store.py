"""
Store routes
    GET    /api/stores                        - list all active stores (public) # Done
    GET    /api/stores/map                    - all stores with coordinates for map #Done 
    GET    /api/stores/<id>                   - get store details with schedules #Done
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

@store_bp.route("/stores/map", methods=["GET"])
def get_stores_map():
    """
    Return all active stores with coordinates for map display.
    Only returns stores that have lat/lng set.
    """
    try:
        stores = Store.query.filter(
            Store.is_active == True,
            Store.latitude != None,
            Store.longitude != None,
        ).all()
    except Exception as e:
        return jsonify({
            "error", "Can't find Store"
        }), 404

    return jsonify({
        "total": len(stores),
        "stores": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "address": s.address,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "contact_number": s.contact_number,
                "owner": s.owner.full_name if s.owner else None,
            }
            for s in stores
        ],
    }), 200

@store_bp.route("/stores/<int:store_id>", methods=["GET"])
def get_store(store_id):
    """Get store details including active schedules."""
    store = Store.query.get(store_id)
    if not store or not store.is_active:
        return jsonify({"error": "Store not found"}), 404
    return jsonify({"store": store.to_dict(include_schedules=True)}), 200

@store_bp.route("/stores", methods=["POST"])
@jwt_required
def create_store():
    """
    Create a new store. Only approved dive operators can create stores.

    Request body:
    {
        "name": "Blue Sea Divers",
        "description": "Best dive shop in Cebu",
        "contact_number": "+63912345678",
        "address": "Malapascua Island, Cebu",
        "latitude": 11.3281,
        "longitude": 124.1128
    }
    """
    user = request.current_user

    # Only approved dive operators or admins can create stores
    if user.role == UserRole.REGULAR:
        return jsonify({"error": "Only dive operators can create stores"}), 403
    if user.role == UserRole.DIVE_OPERATOR and not user.is_approved:
        return jsonify({
            "error": "Your dive operator account must be approved before creating a store",
            "verification_status": user.verification_status,
        }), 403

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"error": "Store name is required"}), 400

    # Validate coordinates if provided
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if latitude is not None and longitude is not None:
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            if not (-90 <= latitude <= 90):
                return jsonify({"error": "Latitude must be between -90 and 90"}), 400
            if not (-180 <= longitude <= 180):
                return jsonify({"error": "Longitude must be between -180 and 180"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid latitude or longitude values"}), 400

    store = Store(
        owner_id=user.id,
        name=name,
        description=(data.get("description") or "").strip() or None,
        contact_number=(data.get("contact_number") or "").strip() or None,
        address=(data.get("address") or "").strip() or None,
        latitude=latitude,
        longitude=longitude,
    )
    db.session.add(store)
    db.session.commit()

    return jsonify({
        "message": f"Store '{name}' created successfully",
        "store": store.to_dict(),
    }), 201

