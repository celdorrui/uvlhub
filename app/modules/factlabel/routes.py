import os
import uuid
import logging
from datetime import datetime
from flask import jsonify, make_response, request
from flask_login import current_user

from app import db
from app.modules.factlabel import factlabel_bp
from app.modules.hubfile.models import HubfileViewRecord
from app.modules.hubfile.services import HubfileService
from app.modules.factlabel.services import FactlabelService

logger = logging.getLogger(__name__)


@factlabel_bp.route("/factlabel/view/<int:file_id>", methods=["GET"])
def view_factlabel(file_id):
    file = HubfileService().get_or_404(file_id)
    filename = file.name

    directory_path = os.path.join(
        "uploads",
        f"user_{file.feature_model.dataset.user_id}",
        f"dataset_{file.feature_model.dataset_id}",
        "uvl",
    )

    file_path = os.path.join(directory_path, filename)

    try:
        if os.path.exists(file_path):
            content = FactlabelService().get_characterization(file)
            # logger.info(f'JSON Content: {content}')
            user_cookie = request.cookies.get("view_cookie")
            if not user_cookie:
                user_cookie = str(uuid.uuid4())

            # Check if the view record already exists for this cookie
            existing_record = HubfileViewRecord.query.filter_by(
                user_id=current_user.id if current_user.is_authenticated else None,
                file_id=file_id,
                view_cookie=user_cookie,
            ).first()

            if not existing_record:
                # Register file view
                new_view_record = HubfileViewRecord(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    file_id=file_id,
                    view_date=datetime.now(),
                    view_cookie=user_cookie,
                )
                db.session.add(new_view_record)
                db.session.commit()

            # Prepare response
            response = jsonify({"success": True, "content": content})
            if not request.cookies.get("view_cookie"):
                response = make_response(response)
                response.set_cookie(
                    "view_cookie", user_cookie, max_age=60 * 60 * 24 * 365 * 2
                )
            return response
        else:
            logger.info("path doesn't exist")
            return jsonify({"success": False, "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
