import pyrebase
import json
import os
from dotenv import load_dotenv
load_dotenv()

FIREBASE_CONFIG=os.getenv("FIREBASE_CONFIG")

firebase_config = json.loads(FIREBASE_CONFIG)

pb=pyrebase.initialize_app(config=firebase_config)

db=pb.database()