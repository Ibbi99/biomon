# scripts/reset_database.py
#
# Utility script to completely wipe the Firebase Realtime Database.
# USE WITH CAUTION — this deletes all patient data, history, and processed results.
#
# Run from the project root:
#   python scripts/reset_database.py

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_client import FirebaseClient
from firebase_admin import db


def main():
    FirebaseClient()
    db.reference("/").delete()
    print("Firebase database cleared.")


if __name__ == "__main__":
    main()