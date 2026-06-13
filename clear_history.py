import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app"
    },
)

db.reference("/patients/Patient_01").delete()
db.reference("/patients/Patient_02").delete()
print("Done!")
