import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_document(file, doc_type: str) -> dict:
    """
    Validate and save an uploaded document file.
    Returns a dict with stored_filename, file_path, file_size, mime_type.
    Raises ValueError on invalid files.
    """
    if not file or not file.filename:
        raise ValueError("No file provided")

    if not allowed_file(file.filename):
        raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS).upper()}")

    # Read content to check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB")

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"{doc_type}_{uuid.uuid4().hex}.{ext}"

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], doc_type)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, stored_filename)
    file.save(file_path)

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "file_size": file_size,
        "mime_type": file.mimetype or "application/octet-stream",
    }


def delete_document_file(file_path: str) -> None:
    """Delete a document file from disk if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass