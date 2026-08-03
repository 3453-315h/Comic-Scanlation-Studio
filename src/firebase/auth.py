"""
Firebase Authentication Module - Comic Translation Studio

Handles Firebase Authentication for user management and cloud sync.
"""

import logging

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


class FirebaseAuthManager:
    """Handles Firebase Authentication"""

    def __init__(self, service_account_path: str | None = None):
        """
        Initialize Firebase Auth
        Args:
            service_account_path: Path to service account JSON file
        """
        if not firebase_admin._apps:
            if service_account_path:
                cred = credentials.Certificate(service_account_path)
            else:
                # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
                cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized")

        self.auth_client = auth

    def verify_token(self, id_token: str) -> dict | None:
        """
        Verify a Firebase ID token from client
        Returns user info if valid, None otherwise
        """
        try:
            decoded_token = self.auth_client.verify_id_token(id_token)
            logger.info(f"Token verified for user: {decoded_token.get('uid')}")
            return decoded_token
        except FirebaseError as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    def create_user(self, email: str, password: str, display_name: str) -> dict | None:
        """Create a new Firebase user"""
        try:
            user = self.auth_client.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            logger.info(f"Created user: {user.uid}")
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name
            }
        except FirebaseError as e:
            logger.error(f"User creation failed: {e}")
            return None

    def get_user(self, uid: str) -> dict | None:
        """Get user data by UID"""
        try:
            user = self.auth_client.get_user(uid)
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "photo_url": user.photo_url
            }
        except FirebaseError as e:
            logger.error(f"Failed to get user {uid}: {e}")
            return None
