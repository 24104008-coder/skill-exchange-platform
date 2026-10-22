from datetime import datetime, timezone
from utils.helpers import parse_object_id

class RequestModel:
    def __init__(self, db):
        self.collection = db.requests

    def create_request(self, skill_id, skill_title, sender_id, sender_name, receiver_id, receiver_name, message):
        """
        Create a new skill learning request.
        """
        s_oid = parse_object_id(skill_id)
        sender_oid = parse_object_id(sender_id)
        receiver_oid = parse_object_id(receiver_id)

        if not s_oid or not sender_oid or not receiver_oid:
            return None, "Invalid ID format"

        if sender_oid == receiver_oid:
            return None, "You cannot request to learn your own skill."

        # Check for existing pending request
        if self.has_pending_request(s_oid, sender_oid):
            return None, "You already have a pending request for this skill."

        req_doc = {
            "skill_id": s_oid,
            "skill_title": skill_title.strip(),
            "sender_id": sender_oid,
            "sender_name": sender_name.strip(),
            "receiver_id": receiver_oid,
            "receiver_name": receiver_name.strip(),
            "message": message.strip() if message else "Hi! I would like to connect and learn this skill.",
            "status": "Pending",
            "reviewed": False,
            "created_at": datetime.now(timezone.utc)
        }

        result = self.collection.insert_one(req_doc)
        req_doc["_id"] = result.inserted_id
        return req_doc, None

    def get_by_id(self, request_id):
        """
        Get request document by ObjectId.
        """
        oid = parse_object_id(request_id)
        if not oid:
            return None
        return self.collection.find_one({"_id": oid})

    def has_pending_request(self, skill_id, sender_id):
        """
        Check if user has an active pending request for this skill.
        """
        s_oid = parse_object_id(skill_id)
        u_oid = parse_object_id(sender_id)
        if not s_oid or not u_oid:
            return False

        return self.collection.find_one({
            "skill_id": s_oid,
            "sender_id": u_oid,
            "status": "Pending"
        }) is not None

    def get_sent_requests(self, user_id):
        """
        Get all requests sent by this user.
        """
        oid = parse_object_id(user_id)
        if not oid:
            return []
        return list(self.collection.find({"sender_id": oid}).sort("created_at", -1))

    def get_received_requests(self, user_id):
        """
        Get all requests received by this user.
        """
        oid = parse_object_id(user_id)
        if not oid:
            return []
        return list(self.collection.find({"receiver_id": oid}).sort("created_at", -1))

    def update_status(self, request_id, new_status, user_id):
        """
        Update request status with strict authorization checks.
        - Accept/Reject: Must be receiver (skill owner)
        - Complete: Can be receiver or sender when in Accepted status
        """
        r_oid = parse_object_id(request_id)
        u_oid = parse_object_id(user_id)

        if not r_oid or not u_oid:
            return False, "Invalid IDs"

        req = self.collection.find_one({"_id": r_oid})
        if not req:
            return False, "Request not found"

        if new_status in ["Accepted", "Rejected"]:
            if req.get("receiver_id") != u_oid:
                return False, "Unauthorized: Only the skill owner can accept or reject this request."
            if req.get("status") != "Pending":
                return False, f"Request cannot be modified as it is currently '{req.get('status')}'."

        elif new_status == "Completed":
            if req.get("receiver_id") != u_oid and req.get("sender_id") != u_oid:
                return False, "Unauthorized: You are not a participant of this request."
            if req.get("status") != "Accepted":
                return False, "Only accepted sessions can be marked as completed."

        update_fields = {"status": new_status, "updated_at": datetime.now(timezone.utc)}
        if new_status == "Completed":
            update_fields["completed_at"] = datetime.now(timezone.utc)

        self.collection.update_one({"_id": r_oid}, {"$set": update_fields})
        return True, None

    def mark_reviewed(self, request_id):
        """
        Mark a completed request as reviewed.
        """
        oid = parse_object_id(request_id)
        if oid:
            self.collection.update_one({"_id": oid}, {"$set": {"reviewed": True}})

    def get_user_stats(self, user_id):
        """
        Retrieve count statistics for user dashboard.
        """
        oid = parse_object_id(user_id)
        if not oid:
            return {"total_learning_requests": 0, "pending_requests": 0, "completed_sessions": 0}

        total_sent = self.collection.count_documents({"sender_id": oid})
        pending_received = self.collection.count_documents({"receiver_id": oid, "status": "Pending"})
        pending_sent = self.collection.count_documents({"sender_id": oid, "status": "Pending"})
        
        # Completed sessions as learner or teacher
        completed_sessions = self.collection.count_documents({
            "$or": [{"sender_id": oid}, {"receiver_id": oid}],
            "status": "Completed"
        })

        return {
            "total_learning_requests": total_sent,
            "pending_received": pending_received,
            "pending_sent": pending_sent,
            "total_pending": pending_received + pending_sent,
            "completed_sessions": completed_sessions
        }
