import io
import os
import uuid
import zipfile
import threading
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from flask import Flask, jsonify, redirect, render_template, request, send_file, session
from flask_jwt_extended import (JWTManager, get_jwt, get_jwt_identity, jwt_required, verify_jwt_in_request,)
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from flask_cors import CORS
import pymysql

from config import Config
from models import AnswerKey, ScoringRule, StudentOMR, User, db
from routes.admin_routes import admin_bp
from routes.answer_key_routes import answer_key_bp
from routes.auth_routes import auth_bp
from services.omr_service import process_single_file
from services.export_service import generate_export_excel
from services.pdf_service import is_pdf_support_available, pdf_bytes_to_images
from multiprocessing import freeze_support


pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]
jwt = JWTManager(app)
CORS(app, supports_credentials=True)


db.init_app(app)

UPLOAD_FOLDER = app.config.get("UPLOAD_FOLDER", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | {".pdf"}
MAX_FILE_SIZE_MB = 20
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
progress_store = {}

with app.app_context():
    db.create_all()


app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


def _save_uploaded_image(file_obj, original_filename: str) -> str | None:
    ext = os.path.splitext(original_filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None
    stem = os.path.splitext(os.path.basename(original_filename))[0]
    new_filename = f"{stem}_{uuid.uuid4()}{ext}"
    path = os.path.join(UPLOAD_FOLDER, new_filename)
    try:
        file_obj.save(path)
        return path
    except OSError:
        return None


def _expand_zip(file_obj, zip_filename: str) -> tuple[list[str], list[str]]:
    paths = []
    warnings = []
    try:
        zip_ref = zipfile.ZipFile(file_obj.stream, "r")
    except zipfile.BadZipFile:
        warnings.append(f"Invalid zip file: {zip_filename}")
        return paths, warnings
    except Exception as exc:
        warnings.append(f"Failed to open zip '{zip_filename}': {exc}")
        return paths, warnings

    try:
        for name in zip_ref.namelist():
            if os.path.isabs(name) or ".." in name:
                continue
            lower = name.lower()
            ext = os.path.splitext(lower)[1]

            if ext in ALLOWED_IMAGE_EXTENSIONS:
                try:
                    data = zip_ref.read(name)
                except Exception:
                    continue
                original_name = os.path.basename(name)
                if not original_name:
                    continue
                stem = os.path.splitext(original_name)[0]
                new_filename = f"{stem}_{uuid.uuid4()}{ext}"
                temp_path = os.path.join(UPLOAD_FOLDER, new_filename)
                try:
                    with open(temp_path, "wb") as f:
                        f.write(data)
                    paths.append(temp_path)
                except OSError as exc:
                    warnings.append(f"Failed to write extracted '{name}': {exc}")

            elif ext == ".pdf":
                if not is_pdf_support_available():
                    warnings.append(f"PDF found inside zip but pdf support is not available; skipping: {name}")
                    continue
                try:
                    pdf_bytes = zip_ref.read(name)
                except Exception:
                    continue
                original_name = os.path.basename(name)
                stem = os.path.splitext(original_name)[0]
                try:
                    img_paths = pdf_bytes_to_images(
                        pdf_bytes,
                        output_dir=UPLOAD_FOLDER,
                        base_name=stem,
                    )
                    paths.extend(img_paths)
                except Exception as exc:
                    warnings.append(f"PDF-in-zip conversion failed for '{name}': {exc}")
    finally:
        zip_ref.close()

    return paths, warnings


def _expand_pdf(file_obj, pdf_filename: str) -> tuple[list[str], list[str]]:
    warnings = []
    if not is_pdf_support_available():
        warnings.append(f"PDF upload received ('{pdf_filename}') but pdf support is not available.")
        return [], warnings

    stem = os.path.splitext(os.path.basename(pdf_filename))[0]
    try:
        pdf_bytes = file_obj.read()
        img_paths = pdf_bytes_to_images(
            pdf_bytes,
            output_dir=UPLOAD_FOLDER,
            base_name=stem,
        )
        return img_paths, warnings
    except Exception as exc:
        warnings.append(f"PDF conversion failed for '{pdf_filename}': {exc}")
        return [], warnings



@app.route("/api/start", methods=["POST"])
@jwt_required()
def start_upload():
    batch_id = str(uuid.uuid4())

    progress_store[batch_id] = {
        "total": 0,
        "processed": 0,
        "status": "Starting",
        "results": [],
        "warnings": [],
        "errors": [],
    }

    return jsonify({"batch_id": batch_id})


@app.route("/api/upload", methods=["POST"])
@jwt_required()
def upload():
    user_id = int(get_jwt_identity())

    batch_id = request.form.get("batch_id")
    if not batch_id:
        return jsonify({"error": "No batch_id"}), 400
    if batch_id not in progress_store:
        return jsonify({"error": "Invalid or expired batch_id"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    extracted_files = []

    for file in files:
        if not file or not file.filename:
            continue

        filename_lower = file.filename.lower()
        ext = os.path.splitext(filename_lower)[1]

        if filename_lower.endswith(".zip"):
            imgs, warns = _expand_zip(file, file.filename)
            progress_store[batch_id]["warnings"].extend(warns)
            if not imgs:
                progress_store[batch_id]["warnings"].append(f"No images extracted from zip: {file.filename}")
            extracted_files.extend(imgs)

        elif ext == ".pdf":
            page_images, warns = _expand_pdf(file, file.filename)
            progress_store[batch_id]["warnings"].extend(warns)
            if not page_images:
                progress_store[batch_id]["warnings"].append(f"No images extracted from PDF: {file.filename}")
            extracted_files.extend(page_images)

        elif ext in ALLOWED_IMAGE_EXTENSIONS:
            saved = _save_uploaded_image(file, file.filename)
            if saved:
                extracted_files.append(saved)
            else:
                progress_store[batch_id]["warnings"].append(f"Failed to save image: {file.filename}")

        else:
            progress_store[batch_id]["warnings"].append(f"Unsupported file type skipped: {file.filename}")
            continue

    if not extracted_files:
        return jsonify({"error": "No valid image files found (supported: jpg, jpeg, png, pdf, zip)"}), 400

    progress_store[batch_id]["total"] = len(extracted_files)

    def background_process(user_id):
        with app.app_context():
            try:
                keys = AnswerKey.query.all()
                key_dict = {
                    (k.level.strip().lower().replace(" ", "_"), k.question_number): k.correct_answer
                    for k in keys
                }

                rules_db = ScoringRule.query.order_by(ScoringRule.level, ScoringRule.range_from).all()
                scoring_rules_by_level = {}
                for r in rules_db:
                    lvl = r.level.strip().lower().replace(" ", "_")
                    scoring_rules_by_level.setdefault(lvl, []).append({
                        "from": r.range_from,
                        "to": r.range_to,
                        "correct": r.correct_marks,
                        "wrong": r.wrong_marks,
                        "empty": r.empty_marks,
                    })
            except Exception as e:
                progress_store[batch_id]["errors"].append(f"Failed to load answer keys from database: {e}")
                progress_store[batch_id]["status"] = "Failed"
                return

            files = extracted_files
            cpu = os.cpu_count()
            MAX_WORKERS = max(2, (cpu - 1) if cpu else 2)

            try:
                with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_idx = {
                        executor.submit(
                            process_single_file, path, key_dict, batch_id, scoring_rules_by_level
                        ): idx
                        for idx, path in enumerate(files)
                    }

                    futures_in_order = [None] * len(files)
                    for future, idx in future_to_idx.items():
                        futures_in_order[idx] = future

                    for i, future in enumerate(futures_in_order):
                        try:
                            res = future.result()
                        except Exception as e:
                            progress_store[batch_id]["errors"].append(f"Processing failed for file {i+1}: {e}")
                            progress_store[batch_id]["processed"] = i + 1
                            progress_store[batch_id]["status"] = f"Processing ({i+1}/{len(files)})"
                            continue

                        if not res:
                            progress_store[batch_id]["errors"].append(f"No result returned for file {i+1}.")
                            progress_store[batch_id]["processed"] = i + 1
                            continue

                        try:
                            student_omr = StudentOMR(**res["db_data"])
                            student_omr.user_id = user_id
                            db.session.add(student_omr)
                            user = db.session.get(User, int(user_id))
                            if user:
                                user.scanned_sheets_count += 1

                            db.session.commit()
                        except Exception as e:
                            progress_store[batch_id]["errors"].append(f"Failed to save result for file {i+1} to database: {e}")
                            db.session.rollback()
                            progress_store[batch_id]["processed"] = i + 1
                            continue

                        row = {
                            "key": str(student_omr.id),
                            **res["row_data"]
                        }

                        progress_store[batch_id]["results"].append(row)
                        progress_store[batch_id]["processed"] = i + 1
                        progress_store[batch_id]["status"] = f"Processing ({i+1}/{len(files)})"

                errors = progress_store[batch_id].get("errors", [])
                warnings = progress_store[batch_id].get("warnings", [])
                if errors or warnings:
                    parts = []
                    if errors:
                        parts.append(f"{len(errors)} error(s): " + "; ".join(errors[:3]))
                    if warnings:
                        parts.append(f"{len(warnings)} warning(s): " + "; ".join(warnings[:3]))
                    progress_store[batch_id]["completion_note"] = " | ".join(parts)
                progress_store[batch_id]["status"] = "Completed"

            except Exception as e:
                progress_store[batch_id]["errors"].append(f"Processing executor failed: {e}")
                progress_store[batch_id]["status"] = "Failed"
                return

            finally:
                for temp_file in extracted_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as cleanup_error:
                        progress_store[batch_id]["warnings"].append(f"Temp file cleanup failed: {cleanup_error}")

    threading.Thread(target=background_process, args=(user_id,), daemon=True).start()

    return jsonify({"message": "Processing started"})


@app.route("/api/results/<batch_id>")
@jwt_required()
def get_results(batch_id):
    data = progress_store.get(batch_id)
    if not data:
        return jsonify({"results": [], "offset": 0, "total": 0, "processed": 0, "percent": 0, "status": "Not found", "warnings": [], "errors": []})

    offset = int(request.args.get("offset", 0))
    results = data["results"]
    new_results = results[offset:]
    total = data["total"]
    processed = data["processed"]
    percent = int((processed / total) * 100) if total else 0

    return jsonify({
        "results": new_results,
        "offset": offset + len(new_results),
        "total": total,
        "processed": processed,
        "percent": percent,
        "status": data["status"],
        "warnings": data.get("warnings", []),
        "errors": data.get("errors", []),
        "completion_note": data.get("completion_note", ""),
    })


@app.route("/api/export_latest")
@jwt_required()
def export_excel():
    batch_id = request.args.get("batch_id")
    if not batch_id:
        return jsonify({"error": "No batch"}), 400
    return generate_export_excel(batch_id)


@app.route("/api/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    role = get_jwt().get("role")
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"msg": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
    })


@app.route("/admin/users-page")
def users_page():
    try:
        verify_jwt_in_request()
        role = get_jwt().get("role")
        if role != "ADMIN":
            return redirect("/omr-analyzer")
        return render_template("users.html")
    except Exception:
        return redirect("/login")


app.register_blueprint(answer_key_bp)

if __name__ == "__main__":
    freeze_support()
    app.run()