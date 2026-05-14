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
from multiprocessing import freeze_support


pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]
jwt = JWTManager(app)
CORS(app, supports_credentials=True)


db.init_app(app)

UPLOAD_FOLDER = app.config.get("UPLOAD_FOLDER", "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB = 20
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
progress_store = {}

with app.app_context():
    db.create_all()
    

app.register_blueprint(auth_bp)     # Login & Logout API's
app.register_blueprint(admin_bp)    # Admin Access API's


@app.route("/api/start", methods=["POST"])
@jwt_required()
def start_upload():
    batch_id = str(uuid.uuid4())
    
    progress_store[batch_id] = {
        "total": 0,
        "processed": 0,
        "status": "Starting",
        "results": []
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

        if filename_lower.endswith(".zip"):
            try:
                zip_ref = zipfile.ZipFile(file.stream, 'r')
            except zipfile.BadZipFile:
                return jsonify({"error": f"Invalid zip file: {file.filename}"}), 400
            except Exception as e:
                return jsonify({"error": f"Failed to open zip: {str(e)}"}), 400

            try:
                for name in zip_ref.namelist():
                    if os.path.isabs(name) or ".." in name:
                        continue
                    if name.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
                        try:
                            data = zip_ref.read(name)
                        except Exception:
                            continue
                        original_name = os.path.basename(name)
                        if not original_name:
                            continue
                        file_name = os.path.splitext(original_name)[0]
                        ext = os.path.splitext(original_name)[1]
                        new_filename = f"{file_name}_{uuid.uuid4()}{ext}"
                        temp_path = os.path.join(UPLOAD_FOLDER, new_filename)
                        try:
                            with open(temp_path, "wb") as f:
                                f.write(data)
                            extracted_files.append(temp_path)
                        except OSError as e:
                            print(f"Failed to write extracted file {name}: {e}")
                            continue
            finally:
                zip_ref.close()

        else:
            ext = os.path.splitext(filename_lower)[1]
            if ext not in ALLOWED_EXTENSIONS:
                continue
            original_name = os.path.basename(file.filename)
            file_name = os.path.splitext(original_name)[0]
            new_filename = f"{file_name}_{uuid.uuid4()}{ext}"
            path = os.path.join(UPLOAD_FOLDER, new_filename)
            try:
                file.save(path)
                extracted_files.append(path)
            except OSError as e:
                print(f"Failed to save file {file.filename}: {e}")
                continue

    if not extracted_files:
        return jsonify({"error": "No valid image files found"}), 400

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
                print(f"DB fetch error in background_process: {e}")
                progress_store[batch_id]["status"] = "Failed"
                return

            files = extracted_files
            cpu = os.cpu_count()
            MAX_WORKERS = max(2, (cpu - 1) if cpu else 2)

            try:
                with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_map = {
                        executor.submit(process_single_file, path, key_dict, batch_id, scoring_rules_by_level): idx
                        for idx, path in enumerate(files)
                    }

                    for i, future in enumerate(as_completed(future_map)):
                        try:
                            res = future.result()
                        except Exception as e:
                            print(f"Worker future error: {e}")
                            progress_store[batch_id]["processed"] = i + 1
                            progress_store[batch_id]["status"] = f"Processing ({i+1}/{len(files)})"
                            continue

                        if not res:
                            print("Worker returned None")
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
                            print(f"DB insert error: {e}")
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
                progress_store[batch_id]["status"] = "Completed"

            except Exception as e:
                print(f"ProcessPoolExecutor error: {e}")
                progress_store[batch_id]["status"] = "Failed"
                return

            finally:

                for temp_file in extracted_files:

                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

                    except Exception as cleanup_error:
                        print(f"Cleanup failed: {cleanup_error}")


    threading.Thread(target=background_process, args=(user_id,), daemon=True).start()

    return jsonify({"message": "Processing started"})


@app.route("/api/results/<batch_id>")
@jwt_required()
def get_results(batch_id):
    data = progress_store.get(batch_id)
    if not data:
        return jsonify({"results": [], "offset": 0, "total": 0, "processed": 0, "percent": 0, "status": "Not found"})

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
        "status": data["status"]
    })


@app.route("/api/export_latest")
@jwt_required()
def export_excel():

    batch_id = request.args.get("batch_id")

    if not batch_id:
        return jsonify({
            "error": "No batch"
        }), 400

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