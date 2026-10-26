import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from app.config import settings

logger = logging.getLogger("database")

LOCAL_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "local_db.json")

class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.is_cloud = False
        self.connected = False
        self.status_message = "Uninitialized"
        self._init_connection()

    def _init_connection(self):
        if settings.MONGODB_URI:
            try:
                # Mask credentials for safe logging
                safe_uri = settings.MONGODB_URI.split("@")[-1] if "@" in settings.MONGODB_URI else "custom_uri"
                logger.info(f"Attempting MongoDB connection to {safe_uri}...")
                self.client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
                # Verify connection
                self.client.admin.command('ping')
                self.db = self.client[settings.MONGODB_DATABASE]
                self.is_cloud = True
                self.connected = True
                self.status_message = f"Connected to MongoDB Atlas ({settings.MONGODB_DATABASE})"
                self._ensure_indexes()
                return
            except Exception as e:
                logger.warning(f"Failed to connect to MongoDB Atlas: {str(e)}. Falling back to local file persistence.")
                self.client = None
                self.db = None

        # Fallback to local storage
        self.is_cloud = False
        self.connected = True
        self.status_message = f"Local JSON persistence active ({os.path.basename(LOCAL_DB_FILE)})"
        self._ensure_local_db()

    def _ensure_local_db(self):
        os.makedirs(os.path.dirname(LOCAL_DB_FILE), exist_ok=True)
        if not os.path.exists(LOCAL_DB_FILE):
            initial_data = {
                "news_articles": [],
                "sentiment_results": [],
                "sentiment_history": [],
                "alerts": [],
                "users": [],
                "password_resets": []
            }
            with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def _read_local_db(self) -> Dict[str, List[Dict[str, Any]]]:
        self._ensure_local_db()
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading local db: {e}")
            return {
                "news_articles": [],
                "sentiment_results": [],
                "sentiment_history": [],
                "alerts": [],
                "users": [],
                "password_resets": []
            }

    def _write_local_db(self, data: Dict[str, List[Dict[str, Any]]]):
        try:
            with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error writing to local db: {e}")
            raise RuntimeError(f"Local storage write failure: {e}")

    def _ensure_indexes(self):
        if self.is_cloud and self.db is not None:
            try:
                self.db.news_articles.create_index("canonical_id", unique=True, sparse=True)
                self.db.news_articles.create_index("company")
                self.db.news_articles.create_index("published_at")
                self.db.sentiment_results.create_index("article_id")
                self.db.sentiment_history.create_index([("company", 1), ("timestamp", -1)])
                self.db.alerts.create_index("timestamp")
                # User and security indexes
                self.db.users.create_index("email", unique=True, sparse=True)
                self.db.password_resets.create_index("token_hash", unique=True, sparse=True)
                self.db.password_resets.create_index("expires_at")
            except Exception as e:
                logger.warning(f"Could not build indexes: {e}")

    def is_storage_available(self) -> bool:
        """Verifies that persistent storage (MongoDB Atlas or writable local filesystem) is operational."""
        if self.is_cloud:
            if self.client is None or self.db is None:
                return False
            try:
                self.client.admin.command('ping')
                return True
            except Exception:
                return False
        else:
            try:
                self._ensure_local_db()
                return os.path.exists(LOCAL_DB_FILE) and os.access(LOCAL_DB_FILE, os.W_OK)
            except Exception:
                return False

    def insert_user(self, user_doc: Dict[str, Any]) -> str:
        """
        Inserts a new user record into persistent storage with duplicate-email enforcement.
        Never silently uses an insecure in-memory structure or ignores storage failure.
        """
        if not self.is_storage_available():
            raise RuntimeError("Persistent database storage is unavailable. Registration aborted.")

        normalized_email = (user_doc.get("email") or "").strip().lower()
        if not normalized_email:
            raise ValueError("User email is required.")

        doc = dict(user_doc)
        doc["email"] = normalized_email
        doc_id = doc.get("id") or doc.get("_id")
        if not doc_id:
            import uuid
            doc_id = f"usr_{uuid.uuid4().hex[:16]}"
            doc["id"] = doc_id
        doc["_id"] = doc_id

        if self.is_cloud and self.db is not None:
            from pymongo.errors import DuplicateKeyError
            try:
                res = self.db.users.insert_one(doc)
                return str(res.inserted_id)
            except DuplicateKeyError:
                raise ValueError("An account with this email address already exists.")
            except Exception as e:
                logger.error(f"MongoDB user persistence failure: {e}")
                raise RuntimeError(f"Database error during user persistence: {e}")
        else:
            db_data = self._read_local_db()
            users = db_data.setdefault("users", [])
            for u in users:
                if (u.get("email") or "").strip().lower() == normalized_email:
                    raise ValueError("An account with this email address already exists.")
            users.append(doc)
            self._write_local_db(db_data)
            return doc_id

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        return self.find_one("users", {"email": normalized})

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        user = self.find_one("users", {"id": user_id})
        if not user:
            user = self.find_one("users", {"_id": user_id})
        return user

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        if not self.is_storage_available():
            raise RuntimeError("Persistent database storage is unavailable.")
        return self.update_one("users", {"id": user_id}, {"password_hash": new_password_hash, "updated_at": datetime.utcnow().isoformat() + "Z"})

    def get_status(self) -> Dict[str, Any]:
        return {
            "persistence_mode": "cloud" if self.is_cloud else "local",
            "connected": self.connected,
            "message": self.status_message,
            "database_name": settings.MONGODB_DATABASE if self.is_cloud else "local_json_db"
        }

    # Generic Collection Operations
    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> str:
        document_copy = dict(document)
        if "_id" not in document_copy and "id" in document_copy:
            document_copy["_id"] = document_copy["id"]
        
        if self.is_cloud and self.db is not None:
            try:
                cid = document_copy.get("canonical_id")
                doc_id = document_copy.get("_id") or document_copy.get("id")
                query = {}
                if cid:
                    query = {"canonical_id": cid}
                elif doc_id:
                    query = {"_id": doc_id}

                if query:
                    self.db[collection_name].replace_one(query, document_copy, upsert=True)
                    return str(doc_id or cid)
                else:
                    res = self.db[collection_name].insert_one(document_copy)
                    return str(res.inserted_id)
            except Exception as e:
                logger.warning(f"MongoDB write handled gracefully: {e}")
                return str(document_copy.get("_id", "unknown"))
        else:
            db_data = self._read_local_db()
            items = db_data.setdefault(collection_name, [])
            # check duplicate by id or canonical_id
            cid = document_copy.get("canonical_id")
            doc_id = document_copy.get("id") or document_copy.get("_id")
            for idx, item in enumerate(items):
                if (cid and item.get("canonical_id") == cid) or (doc_id and item.get("id") == doc_id):
                    items[idx] = document_copy
                    self._write_local_db(db_data)
                    return str(doc_id or cid)
            items.append(document_copy)
            self._write_local_db(db_data)
            return str(doc_id or cid or len(items))

    def bulk_upsert(self, collection_name: str, documents: List[Dict[str, Any]], key_field: str = "canonical_id") -> int:
        """High-speed bulk upsert across MongoDB Atlas and local JSON storage."""
        if not documents:
            return 0
        if self.is_cloud and self.db is not None:
            try:
                from pymongo import ReplaceOne
                operations = []
                for doc in documents:
                    doc_copy = dict(doc)
                    if "_id" not in doc_copy and "id" in doc_copy:
                        doc_copy["_id"] = doc_copy["id"]
                    val = doc_copy.get(key_field) or doc_copy.get("_id")
                    if val:
                        operations.append(ReplaceOne({key_field: val}, doc_copy, upsert=True))
                if operations:
                    res = self.db[collection_name].bulk_write(operations, ordered=False)
                    return (res.upserted_count or 0) + (res.modified_count or 0)
                return 0
            except Exception as e:
                logger.warning(f"MongoDB bulk write notice: {e}. Falling back to iterative insert.")
                count = 0
                for d in documents:
                    self.insert_one(collection_name, d)
                    count += 1
                return count
        else:
            db_data = self._read_local_db()
            items = db_data.setdefault(collection_name, [])
            index_by_key = {}
            for idx, it in enumerate(items):
                k = it.get(key_field) or it.get("id") or it.get("_id")
                if k:
                    index_by_key[k] = idx
            for doc in documents:
                doc_copy = dict(doc)
                k = doc_copy.get(key_field) or doc_copy.get("id") or doc_copy.get("_id")
                if k and k in index_by_key:
                    items[index_by_key[k]] = doc_copy
                else:
                    items.append(doc_copy)
                    if k:
                        index_by_key[k] = len(items) - 1
            self._write_local_db(db_data)
            return len(documents)

    def find(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 100, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        if self.is_cloud and self.db is not None:
            cursor = self.db[collection_name].find(filter_dict or {})
            if sort:
                cursor = cursor.sort(sort)
            cursor = cursor.limit(limit)
            results = []
            for doc in cursor:
                doc["_id"] = str(doc.get("_id"))
                results.append(doc)
            return results
        else:
            db_data = self._read_local_db()
            items = db_data.get(collection_name, [])
            if not filter_dict:
                filtered = list(items)
            else:
                filtered = []
                for item in items:
                    matches = True
                    for k, v in filter_dict.items():
                        if item.get(k) != v:
                            matches = False
                            break
                    if matches:
                        filtered.append(item)
            if sort:
                for key, direction in reversed(sort):
                    filtered = sorted(filtered, key=lambda x: str(x.get(key, "")), reverse=(direction == -1))
            return filtered[:limit]

    def delete_many(self, collection_name: str, filter_dict: Dict[str, Any]) -> int:
        """Deletes matching documents from collection."""
        if self.is_cloud and self.db is not None:
            res = self.db[collection_name].delete_many(filter_dict)
            return res.deleted_count
        else:
            db_data = self._read_local_db()
            items = db_data.get(collection_name, [])
            initial_count = len(items)
            db_data[collection_name] = [
                item for item in items
                if not all(item.get(k) == v for k, v in filter_dict.items())
            ]
            self._write_local_db(db_data)
            return initial_count - len(db_data[collection_name])

    def find_one(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        results = self.find(collection_name, filter_dict, limit=1)
        return results[0] if results else None

    def update_one(self, collection_name: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> bool:
        if self.is_cloud and self.db is not None:
            res = self.db[collection_name].update_one(filter_dict, {"$set": update_dict})
            return res.modified_count > 0
        else:
            db_data = self._read_local_db()
            items = db_data.get(collection_name, [])
            updated = False
            for item in items:
                matches = True
                for k, v in filter_dict.items():
                    if item.get(k) != v:
                        matches = False
                        break
                if matches:
                    item.update(update_dict)
                    updated = True
                    break
            if updated:
                self._write_local_db(db_data)
            return updated

    def count(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        if self.is_cloud and self.db is not None:
            return self.db[collection_name].count_documents(filter_dict or {})
        else:
            return len(self.find(collection_name, filter_dict, limit=100000))

db = DatabaseManager()
