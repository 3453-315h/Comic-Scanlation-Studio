"""
Firestore Module - Comic Translation Studio

Manages Firestore operations for project sync and cloud backup.
"""

import logging
from typing import Any

from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreManager:
    """Manages Firestore operations for project sync"""

    def __init__(self):
        self.db = firestore.Client()
        logger.info("Firestore client initialized")

    def save_project(self, user_id: str, project_data: dict[str, Any]) -> bool:
        """Save project to Firestore"""
        try:
            doc_ref = self.db.collection("users").document(user_id).collection("projects").document(project_data["id"])
            doc_ref.set({
                "name": project_data["name"],
                "created_at": project_data["created_at"],
                "settings": project_data["settings"],
                "page_count": len(project_data.get("pages", {})),
                "synced_at": firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Saved project {project_data['id']} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project to Firestore: {e}")
            return False

    def save_page(self, user_id: str, project_id: str, page_id: str, page_data: dict) -> bool:
        """Save page data to Firestore"""
        try:
            doc_ref = self.db.collection("users").document(user_id).collection("projects").document(project_id).collection("pages").document(page_id)
            doc_ref.set(page_data)
            logger.debug(f"Saved page {page_id} for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save page to Firestore: {e}")
            return False

    def get_projects(self, user_id: str) -> list[dict]:
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

    def sync_project(self, user_id: str, project_data: dict) -> bool:
        """Full project sync (including pages)"""
        try:
            batch = self.db.batch()
            ops_count = 0

            # Save project metadata
            project_ref = self.db.collection("users").document(user_id).collection("projects").document(project_data["id"])
            batch.set(project_ref, {
                "name": project_data["name"],
                "created_at": project_data["created_at"],
                "settings": project_data["settings"],
                "page_count": len(project_data.get("pages", {})),
                "synced_at": firestore.SERVER_TIMESTAMP
            })
            ops_count += 1

            # Save each page
            pages_ref = project_ref.collection("pages")
            for page_id, page_data in project_data.get("pages", {}).items():
                if ops_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    ops_count = 0

                page_ref = pages_ref.document(page_id)
                batch.set(page_ref, page_data)
                ops_count += 1

            if ops_count > 0:
                batch.commit()

            logger.info(f"Full sync completed for project {project_data['id']}")
            return True
        except Exception as e:
            logger.error(f"Project sync failed: {e}")
            return False
