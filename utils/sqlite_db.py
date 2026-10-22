import sqlite3
import json
import re
import os
from datetime import datetime
from bson import ObjectId, json_util

class Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=1):
        def sort_key(d):
            val = d.get(key)
            if val is None:
                return (0, "")
            if isinstance(val, datetime):
                return (1, val.isoformat())
            return (2, str(val))
        self.docs.sort(key=sort_key, reverse=(direction == -1))
        return self

    def limit(self, n):
        if n:
            self.docs = self.docs[:n]
        return self

    def __iter__(self):
        return iter(self.docs)

    def __len__(self):
        return len(self.docs)

    def __getitem__(self, index):
        return self.docs[index]


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class InsertManyResult:
    def __init__(self, inserted_ids):
        self.inserted_ids = inserted_ids

class UpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count

class DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _matches(doc, query):
    if not query:
        return True
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, sub_q) for sub_q in expected):
                return False
            continue
        
        actual = doc.get(key)
        if isinstance(expected, dict):
            if "$regex" in expected:
                pattern = expected["$regex"]
                if isinstance(pattern, str):
                    if not re.search(pattern, str(actual or ""), re.IGNORECASE):
                        return False
                elif hasattr(pattern, "search"):
                    if not pattern.search(str(actual or "")):
                        return False
            if "$in" in expected:
                if actual not in expected["$in"]:
                    return False
        elif hasattr(expected, "search"):
            if not expected.search(str(actual or "")):
                return False
        else:
            if str(actual) != str(expected):
                return False
    return True


def _apply_update(doc, update):
    for op, fields in update.items():
        if op == "$set":
            for k, v in fields.items():
                doc[k] = v
        elif op == "$inc":
            for k, v in fields.items():
                doc[k] = doc.get(k, 0) + v
        elif op == "$addToSet":
            for k, v in fields.items():
                if k not in doc or not isinstance(doc[k], list):
                    doc[k] = []
                if v not in doc[k]:
                    doc[k].append(v)
        elif op == "$pull":
            for k, v in fields.items():
                if k in doc and isinstance(doc[k], list):
                    doc[k] = [x for x in doc[k] if x != v]
    return doc


class SQLiteCollection:
    def __init__(self, db_conn, table_name):
        self.conn = db_conn
        self.table_name = table_name

    def _get_all(self):
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT data FROM {self.table_name}")
        rows = cursor.fetchall()
        docs = []
        for (raw,) in rows:
            doc = json_util.loads(raw)
            docs.append(doc)
        return docs

    def _save_doc(self, doc):
        doc_id = str(doc["_id"])
        raw = json_util.dumps(doc)
        cursor = self.conn.cursor()
        cursor.execute(f"INSERT OR REPLACE INTO {self.table_name} (_id, data) VALUES (?, ?)", (doc_id, raw))
        self.conn.commit()

    def _delete_by_id(self, doc_id):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {self.table_name} WHERE _id = ?", (str(doc_id),))
        self.conn.commit()

    def insert_one(self, doc):
        if "_id" not in doc or not doc["_id"]:
            doc["_id"] = ObjectId()
        self._save_doc(doc)
        return InsertOneResult(doc["_id"])

    def insert_many(self, docs):
        ids = []
        for d in docs:
            if "_id" not in d or not d["_id"]:
                d["_id"] = ObjectId()
            self._save_doc(d)
            ids.append(d["_id"])
        return InsertManyResult(ids)

    def find_one(self, query=None):
        query = query or {}
        if len(query) == 1 and "_id" in query:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT data FROM {self.table_name} WHERE _id = ?", (str(query["_id"]),))
            row = cursor.fetchone()
            if row:
                return json_util.loads(row[0])
            return None

        for doc in self._get_all():
            if _matches(doc, query):
                return doc
        return None

    def find(self, query=None):
        query = query or {}
        all_docs = self._get_all()
        matched = [d for d in all_docs if _matches(d, query)]
        return Cursor(matched)

    def count_documents(self, query=None):
        query = query or {}
        if not query:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]
        return len([d for d in self._get_all() if _matches(d, query)])

    def update_one(self, filter_q, update_q):
        all_docs = self._get_all()
        for doc in all_docs:
            if _matches(doc, filter_q):
                updated_doc = _apply_update(doc, update_q)
                self._save_doc(updated_doc)
                return UpdateResult(1)
        return UpdateResult(0)

    def delete_one(self, filter_q):
        all_docs = self._get_all()
        for doc in all_docs:
            if _matches(doc, filter_q):
                self._delete_by_id(doc["_id"])
                return DeleteResult(1)
        return DeleteResult(0)

    def create_index(self, keys, **kwargs):
        return "idx_ok"


class SQLiteDB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.collections = {}
        for tbl in ['users', 'skills', 'requests', 'reviews', 'materials']:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {tbl} (_id TEXT PRIMARY KEY, data TEXT)")
        self.conn.commit()

        self.users = SQLiteCollection(self.conn, 'users')
        self.skills = SQLiteCollection(self.conn, 'skills')
        self.requests = SQLiteCollection(self.conn, 'requests')
        self.reviews = SQLiteCollection(self.conn, 'reviews')
        self.materials = SQLiteCollection(self.conn, 'materials')

    def __getitem__(self, item):
        if item in ('users', 'skills', 'requests', 'reviews', 'materials'):
            return getattr(self, item)
        if item not in self.collections:
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS {item} (_id TEXT PRIMARY KEY, data TEXT)")
            self.conn.commit()
            self.collections[item] = SQLiteCollection(self.conn, item)
        return self.collections[item]


def get_sqlite_fallback_db(db_path=None):
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'skill_exchange.db')
    db = SQLiteDB(db_path)
    
    # Auto-seed if empty
    if db.users.count_documents({}) == 0:
        seed_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed_data.json')
        if os.path.exists(seed_json_path):
            try:
                with open(seed_json_path, 'r', encoding='utf-8') as f:
                    seed_data = json_util.loads(f.read())
                for col_name, docs in seed_data.items():
                    if docs:
                        db[col_name].insert_many(docs)
                print(f"[OK] Seeded local SQLite database from seed_data.json")
            except Exception as e:
                print(f"[WARNING] Could not seed from seed_data.json: {e}")
    return db
