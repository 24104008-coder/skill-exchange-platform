from datetime import datetime, timezone
from utils.helpers import parse_object_id

class MaterialModel:
    def __init__(self, db):
        self.collection = db.materials

    def create_material(self, skill_id, uploader_id, uploader_name, uploader_role,
                        title, description, material_type, file_path=None, file_name=None,
                        file_size=None, file_ext=None, external_url=None, embed_url=None, tag="Lecture Notes"):
        """
        Create a new course learning material document (PDF, Video, Document, Link).
        """
        s_oid = parse_object_id(skill_id)
        u_oid = parse_object_id(uploader_id)

        if not s_oid or not u_oid:
            return None, "Invalid Skill or User ID"

        material_doc = {
            "skill_id": s_oid,
            "uploader_id": u_oid,
            "uploader_name": uploader_name.strip(),
            "uploader_role": uploader_role,  # 'mentor' or 'student'
            "title": title.strip(),
            "description": (description or "").strip(),
            "material_type": material_type.lower().strip(),  # 'pdf', 'video', 'document', 'link'
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "file_ext": (file_ext or "").lower().strip(),
            "external_url": (external_url or "").strip() or None,
            "embed_url": (embed_url or "").strip() or None,
            "tag": tag.strip() if tag else "General Resource",
            "likes": [],
            "downloads_count": 0,
            "views_count": 0,
            "created_at": datetime.now(timezone.utc)
        }

        result = self.collection.insert_one(material_doc)
        material_doc["_id"] = result.inserted_id
        return material_doc, None

    def get_by_id(self, material_id):
        """
        Retrieve a single material by ObjectId.
        """
        oid = parse_object_id(material_id)
        if not oid:
            return None
        return self.collection.find_one({"_id": oid})

    def get_by_skill_id(self, skill_id, material_type=None):
        """
        Retrieve all materials shared within a specific skill/course.
        """
        oid = parse_object_id(skill_id)
        if not oid:
            return []

        query = {"skill_id": oid}
        if material_type and material_type.lower() != 'all':
            query["material_type"] = material_type.lower()

        return list(self.collection.find(query).sort("created_at", -1))

    def count_by_skill(self, skill_id):
        """
        Count total materials uploaded to a skill.
        """
        oid = parse_object_id(skill_id)
        if not oid:
            return 0
        return self.collection.count_documents({"skill_id": oid})

    def get_by_uploader(self, uploader_id, limit=20):
        """
        Retrieve all materials uploaded by a specific user across courses.
        """
        oid = parse_object_id(uploader_id)
        if not oid:
            return []
        cursor = self.collection.find({"uploader_id": oid}).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def count_by_uploader(self, uploader_id):
        """
        Count total materials shared by a student.
        """
        oid = parse_object_id(uploader_id)
        if not oid:
            return 0
        return self.collection.count_documents({"uploader_id": oid})

    def toggle_like(self, material_id, user_id):
        """
        Toggle helpful/upvote reaction for a material by a student.
        """
        m_oid = parse_object_id(material_id)
        u_str = str(user_id)

        if not m_oid or not u_str:
            return False, 0, "Invalid ID"

        material = self.collection.find_one({"_id": m_oid})
        if not material:
            return False, 0, "Material not found"

        likes = material.get("likes", [])
        if u_str in likes:
            self.collection.update_one({"_id": m_oid}, {"$pull": {"likes": u_str}})
            new_count = len(likes) - 1
            return True, new_count, False  # unliked
        else:
            self.collection.update_one({"_id": m_oid}, {"$addToSet": {"likes": u_str}})
            new_count = len(likes) + 1
            return True, new_count, True  # liked

    def increment_downloads(self, material_id):
        """
        Increment the download counter when a student downloads a document.
        """
        m_oid = parse_object_id(material_id)
        if m_oid:
            self.collection.update_one({"_id": m_oid}, {"$inc": {"downloads_count": 1}})

    def increment_views(self, material_id):
        """
        Increment the view/preview counter when a student previews or watches media.
        """
        m_oid = parse_object_id(material_id)
        if m_oid:
            self.collection.update_one({"_id": m_oid}, {"$inc": {"views_count": 1}})

    def delete_material(self, material_id, user_id, is_skill_owner=False):
        """
        Delete a material if the requester is the uploader or the skill owner (mentor).
        Returns (success, deleted_material_doc, error_message)
        """
        m_oid = parse_object_id(material_id)
        u_oid = parse_object_id(user_id)

        if not m_oid or not u_oid:
            return False, None, "Invalid ID"

        material = self.collection.find_one({"_id": m_oid})
        if not material:
            return False, None, "Material not found"

        # Permission check: must be either the original uploader or the course owner
        if str(material.get("uploader_id")) != str(u_oid) and not is_skill_owner:
            return False, None, "Unauthorized: Only the uploader or course mentor can delete this material"

        self.collection.delete_one({"_id": m_oid})
        return True, material, None
