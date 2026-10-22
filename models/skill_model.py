from datetime import datetime, timezone
import re
from utils.helpers import parse_object_id

class SkillModel:
    def __init__(self, db):
        self.collection = db.skills

    def create_skill(self, title, description, category, level, owner_id, owner_name):
        """
        Create a new skill document.
        """
        oid = parse_object_id(owner_id)
        if not oid:
            return None, "Invalid owner ID"

        skill_doc = {
            "title": title.strip(),
            "description": description.strip(),
            "category": category.strip(),
            "level": level.strip(),
            "owner_id": oid,
            "owner_name": owner_name.strip(),
            "created_at": datetime.now(timezone.utc)
        }

        result = self.collection.insert_one(skill_doc)
        skill_doc["_id"] = result.inserted_id
        return skill_doc, None

    def get_by_id(self, skill_id):
        """
        Find skill by ObjectId.
        """
        oid = parse_object_id(skill_id)
        if not oid:
            return None
        return self.collection.find_one({"_id": oid})

    def get_all_skills(self, search=None, category=None, level=None, limit=100):
        """
        Search and filter skills with case-insensitive matching.
        """
        query = {}

        if category and category.strip() and category != "All":
            query["category"] = category.strip()

        if level and level.strip() and level != "All":
            query["level"] = level.strip()

        if search and search.strip():
            search_regex = re.compile(re.escape(search.strip()), re.IGNORECASE)
            query["$or"] = [
                {"title": {"$regex": search_regex}},
                {"description": {"$regex": search_regex}},
                {"owner_name": {"$regex": search_regex}},
                {"category": {"$regex": search_regex}}
            ]

        cursor = self.collection.find(query).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def get_by_owner_id(self, owner_id):
        """
        Get all skills posted by a specific user.
        """
        oid = parse_object_id(owner_id)
        if not oid:
            return []
        return list(self.collection.find({"owner_id": oid}).sort("created_at", -1))

    def count_by_owner(self, owner_id):
        """
        Count skills posted by a specific user.
        """
        oid = parse_object_id(owner_id)
        if not oid:
            return 0
        return self.collection.count_documents({"owner_id": oid})

    def get_recent_skills(self, limit=6):
        """
        Get the most recently posted skills.
        """
        return list(self.collection.find().sort("created_at", -1).limit(limit))

    def update_skill(self, skill_id, owner_id, title, description, category, level):
        """
        Update skill document ensuring owner authorization.
        """
        s_oid = parse_object_id(skill_id)
        o_oid = parse_object_id(owner_id)

        if not s_oid or not o_oid:
            return False, "Invalid IDs"

        # Check ownership
        skill = self.collection.find_one({"_id": s_oid})
        if not skill:
            return False, "Skill not found"
        if skill.get("owner_id") != o_oid:
            return False, "Unauthorized: You can only edit your own skills"

        update_fields = {
            "title": title.strip(),
            "description": description.strip(),
            "category": category.strip(),
            "level": level.strip(),
            "updated_at": datetime.now(timezone.utc)
        }

        self.collection.update_one({"_id": s_oid}, {"$set": update_fields})
        return True, None

    def delete_skill(self, skill_id, owner_id):
        """
        Delete a skill document with ownership check.
        """
        s_oid = parse_object_id(skill_id)
        o_oid = parse_object_id(owner_id)

        if not s_oid or not o_oid:
            return False, "Invalid IDs"

        skill = self.collection.find_one({"_id": s_oid})
        if not skill:
            return False, "Skill not found"
        if skill.get("owner_id") != o_oid:
            return False, "Unauthorized: You can only delete your own skills"

        self.collection.delete_one({"_id": s_oid})
        return True, None
