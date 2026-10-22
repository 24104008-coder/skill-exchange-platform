import sys
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

from config import Config
from models.user_model import UserModel
from models.skill_model import SkillModel
from models.request_model import RequestModel
from models.review_model import ReviewModel
from models.material_model import MaterialModel
from utils.helpers import (
    login_required,
    parse_object_id,
    format_datetime,
    time_ago,
    format_file_size,
    get_youtube_embed_info,
    detect_material_type,
    init_db_indexes,
    seed_sample_data
)

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'materials')), exist_ok=True)

# Register custom Jinja2 template filters
app.jinja_env.filters['format_date'] = format_datetime
app.jinja_env.filters['time_ago'] = time_ago
app.jinja_env.filters['file_size'] = format_file_size

# Connect to MongoDB
try:
    client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=5000)
    db = client[app.config["DATABASE_NAME"]]
    # Ensure indexes are created
    init_db_indexes(db)
    print(f"[OK] Connected to MongoDB database: {app.config['DATABASE_NAME']}")
except Exception as e:
    print(f"[WARNING] MongoDB connection warning: {e}")
    db = None

# Initialize Models
user_model = UserModel(db) if db is not None else None
skill_model = SkillModel(db) if db is not None else None
request_model = RequestModel(db) if db is not None else None
review_model = ReviewModel(db) if db is not None else None
material_model = MaterialModel(db) if db is not None else None


@app.context_processor
def inject_globals():
    """
    Inject global configuration lists and session data into all templates.
    """
    return {
        "categories": Config.CATEGORIES,
        "skill_levels": Config.SKILL_LEVELS,
        "departments": Config.DEPARTMENTS,
        "years": Config.YEARS,
        "resource_tags": getattr(Config, 'RESOURCE_TAGS', [
            "Lecture Notes", "Video Tutorial", "Cheat Sheet", "Lab Exercise", "Slide Deck", "Reference Code", "Other"
        ]),
        "now": datetime.now(timezone.utc)
    }


# ==========================================
# Authentication & Landing Routes
# ==========================================

@app.route('/')
def index():
    """
    Homepage showcasing platform highlights, features, and recent skills.
    """
    recent_skills = skill_model.get_recent_skills(limit=6) if skill_model else []
    return render_template('index.html', recent_skills=recent_skills)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new college student account.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        department = request.form.get('department', '').strip()
        year = request.form.get('year', '').strip()
        bio = request.form.get('bio', '').strip()

        # Validation
        if not name or not email or not password or not department or not year:
            flash('All required fields must be filled in.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        user, err = user_model.create_user(
            name=name,
            email=email,
            password=password,
            department=department,
            year=year,
            bio=bio
        )

        if err:
            flash(err, 'danger')
            return render_template('register.html')

        # Create session on successful registration
        session['user_id'] = str(user['_id'])
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_image'] = user.get('profile_image', '')

        flash('Registration successful! Welcome to the Skill Sharing Platform.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Log in an existing student using email and password.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        next_url = request.args.get('next')

        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('login.html')

        user = user_model.get_by_email(email)
        if not user or not user_model.verify_password(user, password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        # Store user details in Flask session
        session['user_id'] = str(user['_id'])
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_image'] = user.get('profile_image', '')

        flash(f'Welcome back, {user["name"]}!', 'success')
        if next_url:
            return redirect(next_url)
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Clear session and log out.
    """
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ==========================================
# Dashboard & Profile Routes
# ==========================================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Student dashboard with metrics, personal skills, and recent requests.
    """
    user_id = session.get('user_id')
    user = user_model.get_by_id(user_id)
    if not user:
        session.clear()
        flash('User session expired. Please log in again.', 'warning')
        return redirect(url_for('login'))

    my_skills = skill_model.get_by_owner_id(user_id)
    stats = request_model.get_user_stats(user_id)

    # Fetch recent requests sent or received
    sent_reqs = request_model.get_sent_requests(user_id)[:4]
    received_reqs = request_model.get_received_requests(user_id)[:4]
    all_recent_requests = sorted(sent_reqs + received_reqs, key=lambda r: r.get('created_at', datetime.min), reverse=True)[:5]

    # Recent community skills excluding self
    all_recent = skill_model.get_recent_skills(limit=6)
    recent_community_skills = [s for s in all_recent if str(s.get('owner_id')) != user_id][:3]

    # Shared materials by this student
    my_materials = material_model.get_by_uploader(user_id, limit=6) if material_model else []
    my_materials_count = material_model.count_by_uploader(user_id) if material_model else 0

    return render_template(
        'dashboard.html',
        user=user,
        my_skills=my_skills,
        stats=stats,
        recent_requests=all_recent_requests,
        recent_community_skills=recent_community_skills,
        my_materials=my_materials,
        my_materials_count=my_materials_count
    )


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    View and edit personal student profile.
    """
    user_id = session.get('user_id')
    user = user_model.get_by_id(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        year = request.form.get('year', '').strip()
        bio = request.form.get('bio', '').strip()
        profile_image = request.form.get('profile_image', '').strip()

        if not name or not department or not year:
            flash('Name, department, and year are required.', 'danger')
        else:
            success, err = user_model.update_profile(
                user_id=user_id,
                name=name,
                department=department,
                year=year,
                bio=bio,
                profile_image=profile_image
            )
            if success:
                session['user_name'] = name
                if profile_image:
                    session['user_image'] = profile_image
                flash('Profile updated successfully.', 'success')
                return redirect(url_for('profile'))
            else:
                flash(f'Failed to update profile: {err}', 'danger')

    my_skills = skill_model.get_by_owner_id(user_id)
    stats = request_model.get_user_stats(user_id)
    my_materials_count = material_model.count_by_uploader(user_id) if material_model else 0

    return render_template('profile.html', user=user, my_skills=my_skills, stats=stats, my_materials_count=my_materials_count)


# ==========================================
# Skills Management Routes
# ==========================================

@app.route('/skills')
def skills():
    """
    Explore and search all skills with case-insensitive search and filters.
    """
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'All').strip()
    level_filter = request.args.get('level', 'All').strip()

    skills_list = skill_model.get_all_skills(
        search=search_query if search_query else None,
        category=category_filter if category_filter != 'All' else None,
        level=level_filter if level_filter != 'All' else None
    )

    return render_template(
        'skills.html',
        skills=skills_list,
        current_search=search_query,
        current_category=category_filter,
        current_level=level_filter
    )


@app.route('/add-skill', methods=['GET', 'POST'])
@login_required
def add_skill():
    """
    Create a new skill offering with optional course PDF / material attachment.
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        level = request.form.get('level', '').strip()
        owner_id = session.get('user_id')
        owner_name = session.get('user_name')

        if not title or not description or not category or not level:
            flash('All fields are required to offer a skill.', 'danger')
            return render_template('add_skill.html')

        skill, err = skill_model.create_skill(
            title=title,
            description=description,
            category=category,
            level=level,
            owner_id=owner_id,
            owner_name=owner_name
        )

        if err:
            flash(err, 'danger')
            return render_template('add_skill.html')

        # Update user's skills offered count
        user_model.increment_skills_offered(owner_id, 1)

        # Check if user attached an initial PDF or course material
        if 'material_file' in request.files:
            file = request.files['material_file']
            if file and file.filename != '':
                orig_filename = secure_filename(file.filename)
                ext = orig_filename.rsplit('.', 1)[-1].lower() if '.' in orig_filename else ''
                if ext in Config.ALLOWED_EXTENSIONS:
                    skill_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(skill['_id']))
                    os.makedirs(skill_dir, exist_ok=True)
                    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    saved_filename = f"{timestamp_str}_{orig_filename}"
                    dest_path = os.path.join(skill_dir, saved_filename)
                    file.save(dest_path)
                    file_size_formatted = format_file_size(os.path.getsize(dest_path))
                    detected_type = detect_material_type(filename=orig_filename)
                    mat_title = request.form.get('material_title', '').strip() or f"{title} - Course Notes"
                    mat_tag = request.form.get('material_tag', 'Lecture Notes').strip()

                    material_model.create_material(
                        skill_id=skill['_id'],
                        uploader_id=owner_id,
                        uploader_name=owner_name,
                        uploader_role="Course Mentor",
                        title=mat_title,
                        description="Initial course material uploaded with skill listing.",
                        material_type=detected_type,
                        file_path=f"{skill['_id']}/{saved_filename}",
                        file_name=file.filename,
                        file_size=file_size_formatted,
                        file_ext=ext,
                        tag=mat_tag
                    )

        flash('Skill added successfully! It is now visible to other students.', 'success')
        return redirect(url_for('skill_details', skill_id=skill['_id']))

    return render_template('add_skill.html')


@app.route('/edit-skill/<skill_id>', methods=['GET', 'POST'])
@login_required
def edit_skill(skill_id):
    """
    Edit an existing skill listing and manage course materials (Owner only).
    """
    skill = skill_model.get_by_id(skill_id)
    if not skill:
        flash('Skill not found.', 'danger')
        return redirect(url_for('skills'))

    user_id = session.get('user_id')
    owner_id = skill.get('owner_id') or (skill.get('mentor', {}).get('user_id') if isinstance(skill.get('mentor'), dict) else None)
    if str(owner_id) != str(user_id):
        flash('Unauthorized: You can only edit your own skills.', 'danger')
        return redirect(url_for('skill_details', skill_id=skill_id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        level = request.form.get('level', '').strip()

        if not title or not description or not category or not level:
            flash('All fields are required.', 'danger')
            materials = material_model.get_by_skill_id(skill_id) if material_model else []
            return render_template('edit_skill.html', skill=skill, materials=materials)

        success, err = skill_model.update_skill(
            skill_id=skill_id,
            owner_id=user_id,
            title=title,
            description=description,
            category=category,
            level=level
        )

        # Check if user also attached a new PDF or course material while editing
        if 'material_file' in request.files:
            file = request.files['material_file']
            if file and file.filename != '':
                orig_filename = secure_filename(file.filename)
                ext = orig_filename.rsplit('.', 1)[-1].lower() if '.' in orig_filename else ''
                if ext in Config.ALLOWED_EXTENSIONS:
                    skill_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(skill['_id']))
                    os.makedirs(skill_dir, exist_ok=True)
                    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    saved_filename = f"{timestamp_str}_{orig_filename}"
                    dest_path = os.path.join(skill_dir, saved_filename)
                    file.save(dest_path)
                    file_size_formatted = format_file_size(os.path.getsize(dest_path))
                    detected_type = detect_material_type(filename=orig_filename)
                    mat_title = request.form.get('material_title', '').strip() or f"{title} - Course Notes"
                    mat_tag = request.form.get('material_tag', 'Lecture Notes').strip()

                    material_model.create_material(
                        skill_id=skill['_id'],
                        uploader_id=user_id,
                        uploader_name=session.get('user_name', 'Course Mentor'),
                        uploader_role="Course Mentor",
                        title=mat_title,
                        description="Course material uploaded during skill update.",
                        material_type=detected_type,
                        file_path=f"{skill['_id']}/{saved_filename}",
                        file_name=file.filename,
                        file_size=file_size_formatted,
                        file_ext=ext,
                        tag=mat_tag
                    )
                    flash('New course material attached successfully!', 'info')

        if success:
            flash('Skill updated successfully.', 'success')
            return redirect(url_for('skill_details', skill_id=skill_id))
        else:
            flash(f'Failed to update skill: {err}', 'danger')

    materials = material_model.get_by_skill_id(skill_id) if material_model else []
    return render_template('edit_skill.html', skill=skill, materials=materials)


@app.route('/delete-skill/<skill_id>', methods=['POST'])
@login_required
def delete_skill(skill_id):
    """
    Delete a skill listing (Owner only).
    """
    user_id = session.get('user_id')
    success, err = skill_model.delete_skill(skill_id, user_id)

    if success:
        user_model.increment_skills_offered(user_id, -1)
        flash('Skill deleted successfully.', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash(f'Cannot delete skill: {err}', 'danger')
        return redirect(url_for('skills'))


@app.route('/skill/<skill_id>')
def skill_details(skill_id):
    """
    Display comprehensive skill details, mentor info, ratings, reviews, and course materials.
    """
    skill = skill_model.get_by_id(skill_id)
    if not skill:
        flash('Skill not found or has been removed.', 'warning')
        return redirect(url_for('skills'))

    owner_id = skill.get('owner_id') or (skill.get('mentor', {}).get('user_id') if isinstance(skill.get('mentor'), dict) else None)
    owner = user_model.get_by_id(owner_id) if owner_id else None
    if not owner:
        owner_name = skill.get('owner_name') or (skill.get('mentor', {}).get('name') if isinstance(skill.get('mentor'), dict) else "Student Mentor")
        owner_dept = skill.get('mentor', {}).get('department', "Student") if isinstance(skill.get('mentor'), dict) else "Student"
        owner_yr = skill.get('mentor', {}).get('year', "Campus Peer") if isinstance(skill.get('mentor'), dict) else "Campus Peer"
        owner = {"name": owner_name, "department": owner_dept, "year": owner_yr}

    reviews = review_model.get_by_skill_id(skill_id)
    review_stats = review_model.get_skill_stats(skill_id)

    # Fetch Course Materials (PDFs, Videos, Lab Exercises, Links)
    materials = material_model.get_by_skill_id(skill_id) if material_model else []

    user_id = session.get('user_id')
    is_owner = (user_id and str(owner_id) == str(user_id))
    has_pending = False

    if user_id and not is_owner:
        has_pending = request_model.has_pending_request(skill_id, user_id)

    # Annotate materials with user's like state and calculate category counts
    pdf_count = 0
    video_count = 0
    doc_count = 0
    link_count = 0

    for m in materials:
        m['is_liked'] = bool(user_id and str(user_id) in [str(u) for u in m.get('likes', [])])
        m_type = m.get('material_type', 'document')
        if m_type == 'pdf':
            pdf_count += 1
        elif m_type == 'video':
            video_count += 1
        elif m_type == 'document':
            doc_count += 1
        elif m_type == 'link':
            link_count += 1

    return render_template(
        'skill_details.html',
        skill=skill,
        owner=owner,
        reviews=reviews,
        review_stats=review_stats,
        materials=materials,
        pdf_count=pdf_count,
        video_count=video_count,
        doc_count=doc_count,
        link_count=link_count,
        total_materials=len(materials),
        is_owner=is_owner,
        has_pending=has_pending
    )


# ==========================================
# Course Materials & Media Sharing Routes
# ==========================================

@app.route('/skill/<skill_id>/materials/upload', methods=['POST'])
@login_required
def upload_material(skill_id):
    """
    Upload and share learning materials (PDFs, Videos, Documents, or Links) within a specific course/skill.
    """
    skill = skill_model.get_by_id(skill_id)
    if not skill:
        flash('Skill / Course not found.', 'danger')
        return redirect(url_for('skills'))

    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Student Peer')
    owner_id = skill.get('owner_id') or (skill.get('mentor', {}).get('user_id') if isinstance(skill.get('mentor'), dict) else None)
    is_owner = (str(owner_id) == str(user_id))
    uploader_role = "Course Mentor" if is_owner else "Student Peer"

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    tag = request.form.get('tag', 'Lecture Notes').strip()
    upload_type = request.form.get('upload_type', '').strip()

    file_path = None
    file_name = None
    file_size_formatted = None
    file_ext = None
    external_url = None
    embed_url = None
    detected_type = 'document'

    has_uploaded_file = ('material_file' in request.files and request.files['material_file'].filename != '')
    has_entered_url = bool(request.form.get('external_url', '').strip())

    if has_uploaded_file or upload_type == 'file':
        if 'material_file' not in request.files:
            flash('No file attached. Please select a PDF or document.', 'warning')
            return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

        file = request.files['material_file']
        if not file or file.filename == '':
            flash('Please select a PDF or media file to upload.', 'warning')
            return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

        orig_filename = secure_filename(file.filename)
        if not orig_filename:
            orig_filename = f"resource_{int(datetime.now(timezone.utc).timestamp())}"

        ext = orig_filename.rsplit('.', 1)[-1].lower() if '.' in orig_filename else ''
        if ext not in Config.ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(list(Config.ALLOWED_EXTENSIONS))).upper()
            flash(f'File type .{ext} is not allowed. Supported formats: {allowed_list}.', 'danger')
            return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

        if not title:
            base_name = file.filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').strip().title()
            title = base_name or "Course Learning Resource"

        # Subdirectory per skill
        skill_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(skill['_id']))
        os.makedirs(skill_dir, exist_ok=True)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp_str}_{orig_filename}"
        dest_path = os.path.join(skill_dir, saved_filename)
        file.save(dest_path)

        file_size_bytes = os.path.getsize(dest_path)
        file_size_formatted = format_file_size(file_size_bytes)
        file_path = f"{skill['_id']}/{saved_filename}"
        file_name = file.filename
        file_ext = ext
        detected_type = detect_material_type(filename=orig_filename)

    elif has_entered_url or upload_type == 'link':
        url = request.form.get('external_url', '').strip()
        if not url:
            flash('Please provide a valid URL for the resource or video.', 'warning')
            return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url

        external_url = url
        embed_url, _ = get_youtube_embed_info(url)
        detected_type = detect_material_type(external_url=url)
        file_size_formatted = "Online Media" if detected_type == 'video' else "Web Resource"

        if not title:
            title = "Video Lecture" if detected_type == 'video' else "Web Reference"
    else:
        flash('Please select a PDF file to upload or enter a link.', 'warning')
        return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

    material_doc, err = material_model.create_material(
        skill_id=skill_id,
        uploader_id=user_id,
        uploader_name=user_name,
        uploader_role=uploader_role,
        title=title,
        description=description,
        material_type=detected_type,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size_formatted,
        file_ext=file_ext,
        external_url=external_url,
        embed_url=embed_url,
        tag=tag
    )

    if err:
        flash(f'Error sharing resource: {err}', 'danger')
    else:
        label = "PDF Document" if detected_type == 'pdf' else ("Video Tutorial" if detected_type == 'video' else "Learning Material")
        flash(f'🎉 Success! "{title}" ({label}) has been added to this course.', 'success')

    return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')


@app.route('/skill/<skill_id>/material/<material_id>/download')
def download_material(skill_id, material_id):
    """
    Download a shared document/PDF and record download metrics.
    """
    material = material_model.get_by_id(material_id)
    if not material:
        flash('Requested material not found.', 'warning')
        return redirect(url_for('skill_details', skill_id=skill_id))

    material_model.increment_downloads(material_id)

    if material.get('file_path'):
        rel_path = material.get('file_path')
        abs_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        download_name = material.get('file_name') or filename

        if not os.path.exists(abs_path):
            flash('File is currently unavailable on storage server.', 'danger')
            return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')

        return send_from_directory(
            directory,
            filename,
            as_attachment=True,
            download_name=download_name
        )
    elif material.get('external_url'):
        return redirect(material.get('external_url'))
    else:
        flash('No file attached to this material.', 'info')
        return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')


@app.route('/skill/<skill_id>/material/<material_id>/preview')
def preview_material(skill_id, material_id):
    """
    Stream or view media inline in browser modal (for native PDF preview or video player).
    """
    material = material_model.get_by_id(material_id)
    if not material:
        abort(404)

    material_model.increment_views(material_id)

    if material.get('file_path'):
        rel_path = material.get('file_path')
        abs_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)
        if not os.path.exists(abs_path):
            abort(404)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        return send_from_directory(directory, filename, as_attachment=False)
    elif material.get('external_url'):
        return redirect(material.get('external_url'))
    abort(404)


@app.route('/skill/<skill_id>/material/<material_id>/like', methods=['POST'])
@login_required
def like_material(skill_id, material_id):
    """
    Toggle helpful / upvote reaction on a shared learning material.
    """
    user_id = session.get('user_id')
    success, new_count, liked = material_model.toggle_like(material_id, user_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': success,
            'likes_count': new_count,
            'liked': liked
        })

    flash('Resource vote updated.', 'success')
    return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')


@app.route('/skill/<skill_id>/material/<material_id>/delete', methods=['POST'])
@login_required
def delete_material(skill_id, material_id):
    """
    Remove a shared course material (allowed for uploader or course mentor).
    """
    skill = skill_model.get_by_id(skill_id)
    if not skill:
        flash('Skill not found.', 'danger')
        return redirect(url_for('skills'))

    user_id = session.get('user_id')
    owner_id = skill.get('owner_id') or (skill.get('mentor', {}).get('user_id') if isinstance(skill.get('mentor'), dict) else None)
    is_skill_owner = (str(owner_id) == str(user_id))

    success, material_doc, err = material_model.delete_material(
        material_id=material_id,
        user_id=user_id,
        is_skill_owner=is_skill_owner
    )

    if success:
        if material_doc and material_doc.get('file_path'):
            try:
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], material_doc.get('file_path'))
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception as e:
                print(f"Warning: could not delete file from disk: {e}")
        flash('Course material has been removed.', 'success')
    else:
        flash(f'Cannot delete material: {err}', 'danger')

    return redirect(url_for('skill_details', skill_id=skill_id) + '#materials')


# ==========================================
# Requests Management Routes
# ==========================================

@app.route('/requests')
@login_required
def requests_page():
    """
    Manage received requests and outgoing sent requests.
    """
    user_id = session.get('user_id')
    received_requests = request_model.get_received_requests(user_id)
    sent_requests = request_model.get_sent_requests(user_id)

    return render_template(
        'requests.html',
        received_requests=received_requests,
        sent_requests=sent_requests
    )


@app.route('/request-skill/<skill_id>', methods=['POST'])
@login_required
def request_skill(skill_id):
    """
    Send a learning request to the skill mentor.
    """
    skill = skill_model.get_by_id(skill_id)
    if not skill:
        flash('Skill not found.', 'danger')
        return redirect(url_for('skills'))

    sender_id = session.get('user_id')
    sender_name = session.get('user_name')
    receiver_id = skill.get('owner_id')
    receiver_name = skill.get('owner_name')

    if str(receiver_id) == sender_id:
        flash('You cannot request to learn your own skill.', 'warning')
        return redirect(url_for('skill_details', skill_id=skill_id))

    message = request.form.get('message', '').strip()

    req, err = request_model.create_request(
        skill_id=skill_id,
        skill_title=skill.get('title'),
        sender_id=sender_id,
        sender_name=sender_name,
        receiver_id=receiver_id,
        receiver_name=receiver_name,
        message=message
    )

    if err:
        flash(err, 'warning')
    else:
        flash('Request sent successfully! The mentor has been notified.', 'success')

    return redirect(url_for('skill_details', skill_id=skill_id))


@app.route('/accept-request/<request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    """
    Accept an incoming learning request.
    """
    user_id = session.get('user_id')
    success, err = request_model.update_status(request_id, 'Accepted', user_id)

    if success:
        flash('Request accepted. You can now coordinate session timings with your peer.', 'success')
    else:
        flash(f'Unable to accept request: {err}', 'danger')

    return redirect(url_for('requests_page'))


@app.route('/reject-request/<request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    """
    Decline an incoming learning request.
    """
    user_id = session.get('user_id')
    success, err = request_model.update_status(request_id, 'Rejected', user_id)

    if success:
        flash('Request declined.', 'info')
    else:
        flash(f'Unable to decline request: {err}', 'danger')

    return redirect(url_for('requests_page'))


@app.route('/complete-request/<request_id>', methods=['POST'])
@login_required
def complete_request(request_id):
    """
    Mark an active session as completed.
    """
    user_id = session.get('user_id')
    req = request_model.get_by_id(request_id)
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('requests_page'))

    success, err = request_model.update_status(request_id, 'Completed', user_id)

    if success:
        # Increment skills learned count for student
        user_model.increment_skills_learned(req.get('sender_id'), 1)
        flash('Session marked as completed! You can now leave a rating and review.', 'success')
    else:
        flash(f'Unable to complete request: {err}', 'danger')

    return redirect(url_for('requests_page'))


# ==========================================
# Reviews & Ratings Routes
# ==========================================

@app.route('/review/<request_id>', methods=['POST'])
@login_required
def submit_review(request_id):
    """
    Submit rating (1-5) and review for a completed learning session.
    """
    user_id = session.get('user_id')
    req = request_model.get_by_id(request_id)

    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('requests_page'))

    if str(req.get('sender_id')) != user_id:
        flash('Only the student who requested and learned the skill can review this session.', 'danger')
        return redirect(url_for('requests_page'))

    if req.get('status') != 'Completed':
        flash('Only completed sessions can be reviewed.', 'warning')
        return redirect(url_for('requests_page'))

    rating = request.form.get('rating')
    comment = request.form.get('comment', '').strip()

    review, err = review_model.create_review(
        skill_id=req.get('skill_id'),
        request_id=req.get('_id'),
        reviewer_id=user_id,
        reviewer_name=session.get('user_name', 'Student'),
        rating=rating,
        comment=comment
    )

    if err:
        flash(err, 'danger')
    else:
        request_model.mark_reviewed(request_id)
        flash('Review submitted successfully! Thank you for supporting peer learning.', 'success')

    return redirect(url_for('skill_details', skill_id=req.get('skill_id')))


@app.route('/reviews')
def reviews_page():
    """
    Public reviews and testimonials gallery.
    """
    if not review_model:
        return render_template('reviews.html', reviews=[])
    all_reviews = list(db.reviews.find().sort("created_at", -1).limit(50))
    return render_template('reviews.html', reviews=all_reviews)


@app.route('/seed-data')
def seed_data_route():
    """
    Optional development helper route to populate initial sample skills and users.
    """
    if db is None:
        return "Database is not connected.", 500
    res = seed_sample_data(db)
    flash(res["message"], res["status"])
    return redirect(url_for('skills'))


# ==========================================
# Error Handlers
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Check for cli argument to seed data
    if len(sys.argv) > 1 and sys.argv[1] == 'seed':
        if db is not None:
            res = seed_sample_data(db)
            print(res["message"])
        sys.exit(0)

    port = int(os.environ.get("PORT", 5000))
    app.run(host='127.0.0.1', port=port, debug=Config.DEBUG)
