from datetime import datetime, timezone
from utils.helpers import parse_object_id

class ReviewModel:
    def __init__(self, db):
        self.collection = db.reviews

    def create_review(self, skill_id, request_id, reviewer_id, reviewer_name, rating, comment):
        """
        Create a new review for a completed skill sharing request.
        """
        s_oid = parse_object_id(skill_id)
        r_oid = parse_object_id(request_id)
        u_oid = parse_object_id(reviewer_id)

        if not s_oid or not r_oid or not u_oid:
            return None, "Invalid IDs provided"

        # Prevent duplicate review on the same completed request
        if self.has_reviewed_request(r_oid):
            return None, "You have already reviewed this learning session."

        try:
            rating_int = int(rating)
            if rating_int < 1 or rating_int > 5:
                return None, "Rating must be between 1 and 5 stars."
        except (ValueError, TypeError):
            return None, "Invalid rating value."

        review_doc = {
            "skill_id": s_oid,
            "request_id": r_oid,
            "reviewer_id": u_oid,
            "reviewer_name": reviewer_name.strip(),
            "rating": rating_int,
            "comment": comment.strip() if comment else "",
            "created_at": datetime.now(timezone.utc)
        }

        result = self.collection.insert_one(review_doc)
        review_doc["_id"] = result.inserted_id
        return review_doc, None

    def get_by_skill_id(self, skill_id):
        """
        Fetch all reviews for a specific skill.
        """
        oid = parse_object_id(skill_id)
        if not oid:
            return []
        return list(self.collection.find({"skill_id": oid}).sort("created_at", -1))

    def get_by_request_id(self, request_id):
        """
        Fetch review for a specific request.
        """
        oid = parse_object_id(request_id)
        if not oid:
            return None
        return self.collection.find_one({"request_id": oid})

    def has_reviewed_request(self, request_id):
        """
        Check if a request was already reviewed.
        """
        oid = parse_object_id(request_id)
        if not oid:
            return False
        return self.collection.find_one({"request_id": oid}) is not None

    def get_skill_stats(self, skill_id):
        """
        Calculate average rating and total reviews for a skill.
        """
        oid = parse_object_id(skill_id)
        if not oid:
            return {"average_rating": 0.0, "total_reviews": 0}

        reviews = list(self.collection.find({"skill_id": oid}))
        if not reviews:
            return {"average_rating": 0.0, "total_reviews": 0}

        total = len(reviews)
        avg = sum(r["rating"] for r in reviews) / total
        return {
            "average_rating": round(avg, 1),
            "total_reviews": total
        }
