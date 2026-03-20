from dotenv import load_dotenv
import os
import json
import firebase_admin
from firebase_admin import credentials, auth

# Load environment variables
load_dotenv()

def init_firebase():
    firebase_json = os.getenv("FIREBASE_CREDENTIALS")

    if not firebase_json:
        raise ValueError("❌ FIREBASE_CREDENTIALS not set in environment")

    try:
        # Handle case where quotes are accidentally added twice
        if firebase_json.startswith("'") or firebase_json.startswith('"'):
            firebase_json = firebase_json.strip("'\"")

        cred_dict = json.loads(firebase_json)

        # Fix private key formatting
        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

        # Initialize only once
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)

    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Invalid FIREBASE_CREDENTIALS JSON: {str(e)}")

    except Exception as e:
        raise ValueError(f"❌ Firebase initialization failed: {str(e)}")


# Initialize at import
init_firebase()


def verify_token(token: str):
    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
        }
    except Exception as e:
        raise ValueError(f"❌ Invalid Firebase token: {str(e)}")