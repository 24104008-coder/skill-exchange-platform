from functools import wraps
from flask import session, redirect, url_for, flash, request
from bson import ObjectId
from datetime import datetime, timezone
import pymongo
from werkzeug.security import generate_password_hash

def login_required(f):
    """
    Decorator to ensure user is logged in before accessing a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def parse_object_id(id_str):
    """
    Safely parse a string into a BSON ObjectId.
    Returns ObjectId or None if invalid.
    """
    try:
        if isinstance(id_str, ObjectId):
            return id_str
        return ObjectId(str(id_str))
    except Exception:
        return None

def format_datetime(value, format="%b %d, %Y"):
    """
    Format a datetime object for Jinja2 templates.
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

def time_ago(value):
    """
    Display a friendly relative time (e.g., '2 hours ago', 'Just now').
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    if not isinstance(value, datetime):
        return str(value)
    
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    
    diff = now - value

    seconds = diff.total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return value.strftime("%b %d, %Y")

def format_file_size(bytes_size):
    """
    Format bytes into human-readable size string (KB, MB, GB).
    """
    if not bytes_size or bytes_size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(bytes_size)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.1f} {units[i]}"

def get_youtube_embed_info(url):
    """
    Extract YouTube video ID, embed URL, and thumbnail URL from various YouTube link formats.
    """
    import re
    if not url:
        return None, None
    url = url.strip()
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            embed_url = f"https://www.youtube-nocookie.com/embed/{video_id}"
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            return embed_url, thumbnail_url
    return None, None

def detect_material_type(filename=None, external_url=None):
    """
    Detect resource type category: 'pdf', 'video', 'document', or 'link'.
    """
    if filename:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext == 'pdf':
            return 'pdf'
        elif ext in {'mp4', 'webm', 'mov', 'mkv', 'avi'}:
            return 'video'
        elif ext in {'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip'}:
            return 'document'
    if external_url:
        u_lower = external_url.lower()
        if any(k in u_lower for k in ['youtube.com', 'youtu.be', 'vimeo.com', '.mp4', '.webm']):
            return 'video'
        return 'link'
    return 'document'

def init_db_indexes(db):
    """
    Create MongoDB indexes for performance and uniqueness.
    """
    try:
        # User indexes
        db.users.create_index([("email", pymongo.ASCENDING)], unique=True)

        # Skill indexes
        db.skills.create_index([("title", pymongo.TEXT), ("description", pymongo.TEXT)])
        db.skills.create_index([("category", pymongo.ASCENDING)])
        db.skills.create_index([("level", pymongo.ASCENDING)])
        db.skills.create_index([("owner_id", pymongo.ASCENDING)])

        # Request indexes
        db.requests.create_index([("sender_id", pymongo.ASCENDING)])
        db.requests.create_index([("receiver_id", pymongo.ASCENDING)])
        db.requests.create_index([("skill_id", pymongo.ASCENDING)])
        db.requests.create_index([("status", pymongo.ASCENDING)])

        # Review indexes
        db.reviews.create_index([("skill_id", pymongo.ASCENDING)])
        db.reviews.create_index([("request_id", pymongo.ASCENDING)], unique=True)

        # Material indexes
        db.materials.create_index([("skill_id", pymongo.ASCENDING)])
        db.materials.create_index([("uploader_id", pymongo.ASCENDING)])
        db.materials.create_index([("material_type", pymongo.ASCENDING)])
    except Exception as e:
        print(f"Warning: Could not create some indexes: {e}")


def seed_sample_data(db):
    """
    Seed initial sample users and skills for testing or demonstration purposes.
    """
    # Check if users already exist
    existing_user_count = db.users.count_documents({})
    if existing_user_count > 0:
        return {"status": "info", "message": "Database already contains data. Seeding skipped to avoid duplicates."}

    sample_users = [
        {
            "name": "Alex Chen",
            "email": "alex.chen@college.edu",
            "password_hash": generate_password_hash("password123"),
            "department": "Computer Science & Engineering",
            "year": "3rd Year",
            "bio": "Passionate full-stack developer and open source enthusiast. Love building clean web apps with Flask, Python, and modern UI.",
            "profile_image": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
            "skills_offered": 3,
            "skills_learned": 2,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "name": "Sarah Miller",
            "email": "sarah.m@college.edu",
            "password_hash": generate_password_hash("password123"),
            "department": "Design & Media",
            "year": "2nd Year",
            "bio": "UI/UX Designer and digital illustrator. Creating intuitive user experiences and aesthetic visual identities.",
            "profile_image": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80",
            "skills_offered": 2,
            "skills_learned": 1,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "name": "Rohan Patel",
            "email": "rohan.p@college.edu",
            "password_hash": generate_password_hash("password123"),
            "department": "Data Science & AI",
            "year": "4th Year",
            "bio": "Machine learning researcher and competitive programmer. Happy to help with Python data analysis, NumPy, and Pandas.",
            "profile_image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
            "skills_offered": 2,
            "skills_learned": 3,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "name": "Emily Watson",
            "email": "emily.w@college.edu",
            "password_hash": generate_password_hash("password123"),
            "department": "Business Administration",
            "year": "3rd Year",
            "bio": "Public speaker, debate club president, and digital marketing specialist. Helping students build presentation confidence.",
            "profile_image": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=400&q=80",
            "skills_offered": 2,
            "skills_learned": 1,
            "created_at": datetime.now(timezone.utc)
        }
    ]

    inserted_users = db.users.insert_many(sample_users)
    user_ids = inserted_users.inserted_ids

    sample_skills = [
        {
            "title": "Python Programming Fundamentals & OOP",
            "description": "Master Python from basics to advanced object-oriented programming concepts. Learn data structures, algorithms, and practical scripting with hands-on exercises.",
            "category": "Programming",
            "level": "Beginner",
            "owner_id": user_ids[0],
            "owner_name": "Alex Chen",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Full-Stack Web Development with Flask & HTML/CSS",
            "description": "Learn to build complete, functional web applications using Flask backend, Jinja2 templating, and clean responsive CSS styling without external bloated frameworks.",
            "category": "Web Development",
            "level": "Intermediate",
            "owner_id": user_ids[0],
            "owner_name": "Alex Chen",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "UI/UX Design Principles & Figma Wireframing",
            "description": "Discover color theory, typography hierarchy, user journey mapping, and prototyping with Figma. Ideal for developers wanting to improve UI design skills.",
            "category": "Design",
            "level": "Beginner",
            "owner_id": user_ids[1],
            "owner_name": "Sarah Miller",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Graphic Design & Digital Illustration",
            "description": "Hands-on guidance on logo design, vector graphics, social media assets, and visual branding fundamentals for college clubs and projects.",
            "category": "Design",
            "level": "Intermediate",
            "owner_id": user_ids[1],
            "owner_name": "Sarah Miller",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Data Science with Pandas & NumPy",
            "description": "Learn data wrangling, exploratory data analysis, statistical modeling, and visualization with Matplotlib and Seaborn on real-world datasets.",
            "category": "Data Science",
            "level": "Intermediate",
            "owner_id": user_ids[2],
            "owner_name": "Rohan Patel",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Artificial Intelligence & Machine Learning Basics",
            "description": "Introduction to supervised and unsupervised learning algorithms: linear regression, decision trees, neural networks, and model evaluation metrics.",
            "category": "Artificial Intelligence",
            "level": "Advanced",
            "owner_id": user_ids[2],
            "owner_name": "Rohan Patel",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Public Speaking & Confident Presentation Skills",
            "description": "Overcome stage fright, structure persuasive speeches, master body language, and deliver captivating project presentations in front of audiences.",
            "category": "Communication",
            "level": "Beginner",
            "owner_id": user_ids[3],
            "owner_name": "Emily Watson",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "title": "Digital Marketing & Personal Branding for Students",
            "description": "Build an impressive LinkedIn presence, learn SEO basics, content strategy, and networking tips to land internships and opportunities.",
            "category": "Marketing",
            "level": "Beginner",
            "owner_id": user_ids[3],
            "owner_name": "Emily Watson",
            "created_at": datetime.now(timezone.utc)
        }
    ]

    inserted_skills = db.skills.insert_many(sample_skills)
    skill_ids = inserted_skills.inserted_ids

    # Add a sample completed request and review for demonstration
    sample_request = {
        "skill_id": skill_ids[0],
        "skill_title": "Python Programming Fundamentals & OOP",
        "sender_id": user_ids[1],
        "sender_name": "Sarah Miller",
        "receiver_id": user_ids[0],
        "receiver_name": "Alex Chen",
        "message": "Hi Alex! I would love to learn Python programming to build simple backend scripts for my design portfolio.",
        "status": "Completed",
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc)
    }
    inserted_request = db.requests.insert_one(sample_request)

    sample_review = {
        "skill_id": skill_ids[0],
        "request_id": inserted_request.inserted_id,
        "reviewer_id": user_ids[1],
        "reviewer_name": "Sarah Miller",
        "rating": 5,
        "comment": "Alex is an incredible mentor! He explained Python concepts with clear practical examples and was super patient with all my beginner questions.",
        "created_at": datetime.now(timezone.utc)
    }
    db.reviews.insert_one(sample_review)

    return {"status": "success", "message": f"Successfully seeded {len(sample_users)} users and {len(sample_skills)} skills with initial reviews!"}
