"""
Firebase integration for cloud sync, authentication, and storage.
All firebase features are optional - the app works offline.
"""

from .auth import FirebaseAuthManager
from .firestore import FirestoreManager
from .storage import CloudStorageManager

__all__ = [
    "FirebaseAuthManager",
    "FirestoreManager",
    "CloudStorageManager"
]
