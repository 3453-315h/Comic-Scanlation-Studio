"""
Firestore Module - Comic Translation Studio

Manages Firestore operations for project sync and cloud backup.
"""

from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentSnapshot
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


class FirestoreManager:
    """Manages Firestore operations for project sync"""
    
    def __init__(self):
        self.db = firestore.Client()
        logger.info("Firestore client initialized")
    
    def save_project(self, user_id: str, project_data: Dict[str, Any], batch: Optional[Any] = None) -> bool:
        """Save project to Firestore"""
        try:
            doc_ref = self.db.collection("users").document(user_id).collection("projects").document(project_data["id"])
            data = {
                "name": project_data["name"],
                "created_at": project_data["created_at"],
                "settings": project_data["settings"],
                "page_count": len(project_data.get("pages", {})),
                "synced_at": firestore.SERVER_TIMESTAMP
            }
            if batch:
                batch.set(doc_ref, data)
            else:
                doc_ref.set(data)
            logger.info(f"Saved project {project_data['id']} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project to Firestore: {e}")
            return False
    
    def save_page(self, user_id: str, project_id: str, page_id: str, page_data: Dict, batch: Optional[Any] = None) -> bool:
        """Save page data to Firestore"""
        try:
            doc_ref = self.db.collection("users").document(user_id).collection("projects").document(project_id).collection("pages").document(page_id)
            if batch:
                batch.set(doc_ref, page_data)
            else:
                doc_ref.set(page_data)
            logger.debug(f"Saved page {page_id} for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save page to Firestore: {e}")
            return False
    
    def get_projects(self, user_id: str) -> List[Dict]:
        """Get all projects for a user"""
        try:
            projects_ref = self.db.collection("users").document(user_id).collection("projects")
            docs = projects_ref.stream()
            projects = [doc.to_dict() for doc in docs]
            logger.info(f"Retrieved {len(projects)} projects for user {user_id}")
            return projects
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            return []
    
    def sync_project(self, user_id: str, project_data: Dict) -> bool:
        """Full project sync (including pages)"""
        try:
            op_count = 0
            batch = self.db.batch()

            # Save project metadata
            self.save_project(user_id, project_data, batch=batch)
            op_count += 1
            
            # Save each page
            for page_id, page_data in project_data.get("pages", {}).items():
                self.save_page(user_id, project_data["id"], page_id, page_data, batch=batch)
                op_count += 1

                # Firestore batch limit is 500 operations
                if op_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    op_count = 0
            
            # Commit any remaining operations
            if op_count > 0:
                batch.commit()

            logger.info(f"Full sync completed for project {project_data['id']}")
            return True
        except Exception as e:
            logger.error(f"Project sync failed: {e}")
            return False