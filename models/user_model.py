from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import parse_object_id

class UserModel:
    def __init__(self, db):
        self.collection = db.users

    def create_user(self, name, email, password, department, year, bio="", profile_image=""):
        """
        Create a new user document with hashed password.
        """
        email_clean = email.strip().lower()
        if self.get_by_email(email_clean):
            return None, "An account with this email already exists."

        if not profile_image or not profile_image.strip():
            # Clean initial-based avatar fallback or modern illustrated avatar
            profile_image = f"https://api.dicebear.com/7.x/initials/svg?seed={name.replace(' ', '+')}&backgroundColor=6366f1,8b5cf6,4f46e5&textColor=ffffff"

        user_doc = {
            "name": name.strip(),
            "email": email_clean,
            "password_hash": generate_password_hash(password),
            "department": department.strip(),
            "year": year.strip(),
            "bio": bio.strip() if bio else "Eager to share skills and learn from fellow students!",
            "profile_image": profile_image.strip(),
            "skills_offered": 0,
            "skills_learned": 0,
            "created_at": datetime.now(timezone.utc)
        }

        result = self.collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return user_doc, None

    def get_by_email(self, email):
        """
        Find user by lowercase email.
        """
        if not email:
            return None
        return self.collection.find_one({"email": email.strip().lower()})

    def get_by_id(self, user_id):
        """
        Find user by ObjectId.
        """
        oid = parse_object_id(user_id)
        if not oid:
            return None
        return self.collection.find_one({"_id": oid})

    def verify_password(self, user_doc, password):
        """
        Verify plain password against stored password hash.
        """
        if not user_doc or "password_hash" not in user_doc:
            return False
        return check_password_hash(user_doc["password_hash"], password)

    def update_profile(self, user_id, name, department, year, bio, profile_image=None):
        """
        Update user profile information.
        """
        oid = parse_object_id(user_id)
        if not oid:
            return False, "Invalid user ID"

        update_fields = {
            "name": name.strip(),
            "department": department.strip(),
            "year": year.strip(),
            "bio": bio.strip(),
            "updated_at": datetime.now(timezone.utc)
        }

        if profile_image and profile_image.strip():
            update_fields["profile_image"] = profile_image.strip()

        result = self.collection.update_one({"_id": oid}, {"$set": update_fields})
        return result.modified_count >= 0, None

    def increment_skills_offered(self, user_id, delta=1):
        """
        Update skills offered count for user.
        """
        oid = parse_object_id(user_id)
        if oid:
            self.collection.update_one({"_id": oid}, {"$inc": {"skills_offered": delta}})

    def increment_skills_learned(self, user_id, delta=1):
        """
        Update skills learned count for user.
        """
        oid = parse_object_id(user_id)
        if oid:
            self.collection.update_one({"_id": oid}, {"$inc": {"skills_learned": delta}})
