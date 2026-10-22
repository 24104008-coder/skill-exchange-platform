import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key-change-in-production")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "student_skill_sharing")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

    # Categories supported
    CATEGORIES = [
        "Programming",
        "Web Development",
        "Mobile Development",
        "Database",
        "Data Science",
        "Artificial Intelligence",
        "Design",
        "Communication",
        "Marketing",
        "Music",
        "Sports",
        "Photography",
        "Other"
    ]

    # Skill levels
    SKILL_LEVELS = [
        "Beginner",
        "Intermediate",
        "Advanced"
    ]

    # Department list for college student profile
    DEPARTMENTS = [
        "Computer Science & Engineering",
        "Information Technology",
        "Electronics & Communication",
        "Electrical & Electronics",
        "Mechanical Engineering",
        "Civil Engineering",
        "Data Science & AI",
        "Business Administration",
        "Design & Media",
        "Other"
    ]

    YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Postgraduate"]

    # Course material upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'materials')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file upload
    ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'webm', 'mov', 'mkv', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip'}
    RESOURCE_TAGS = [
        "Lecture Notes",
        "Video Tutorial",
        "Cheat Sheet",
        "Lab Exercise",
        "Slide Deck",
        "Reference Code",
        "Practice Problems",
        "Study Guide",
        "Other"
    ]
