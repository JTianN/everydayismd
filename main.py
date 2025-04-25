from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_admin import credentials, firestore, initialize_app
from passlib.context import CryptContext
import os
import json
from fastapi.middleware.cors import CORSMiddleware


# --- FastAPI App ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # หรือ ["http://localhost:3000"] ถ้าอยากจำกัดแค่ frontend ที่ใช้
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#แก้ code 24-04-2025 change path key 2025

# โหลด JSON จาก Environment Variable
firebase_cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIAL_JSON"))
# สร้าง credential จาก dict (ไม่ใช้ไฟล์)
cred = credentials.Certificate(firebase_cred_dict)
initialize_app(cred)
print("✅ Firebase connected successfully")
# ใช้งาน Firestore ได้ตามปกติ
db = firestore.client()
users_ref = db.collection("users")




# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Models ---
class User(BaseModel):
    email: str
    password: str

class ProfileUser(BaseModel):  # เพิ่มมาใหม่
    name: str
    status: str
    comments: List[str]
    enduBTN: str

class UpdateProfileUser(BaseModel):  # เพิ่มมาใหม่
    name: Optional[str] = None
    status: Optional[str] = None
    comments: Optional[List[str]] = None
    enduBTN: Optional[str] = None

class CreateProfileUser(BaseModel):  # เพิ่มมาใหม่
    name: str
    status: Optional[str] = ""
    comments: Optional[List[str]] = []
    enduBTN: Optional[str] = ""

# --- Welcome Route ---
@app.get("/")
def home():
    return {"message": "Welcome to EveryDay in Monday!"}

# --- Register ---
@app.post("/register")
async def register(user: User):
    user.email = user.email.strip().lower()

    # ใช้ .where แบบ positional arguments แก้เป็น .filter
    existing = users_ref.where("email", "==", user.email).stream()
    if any(existing):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    users_ref.add({"email": user.email, "password": hashed_password})

    return {"message": "Registration successful"}

# --- Login ---
@app.post("/login")
async def login(user: User):
    user.email = user.email.strip().lower()

    # เปลี่ยนจาก .where เป็น .filter
    docs = users_ref.where("email", "==", user.email).stream()  # ใช้ where ได้ แต่คำเตือนจะหายไป
    doc = next(docs, None)
    if not doc or not doc.exists:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_data = doc.to_dict()
    if not pwd_context.verify(user.password, user_data["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"message": "Login successful", "email": user.email}

# --- Delete Account ---
@app.post("/delete")
async def delete_account(user: User):
    user.email = user.email.strip().lower()

    # เปลี่ยนจาก .where เป็น .filter
    docs = users_ref.where("email", "==", user.email).stream()  # ใช้ where ได้ แต่คำเตือนจะหายไป
    doc = next(docs, None)
    if not doc or not doc.exists:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_data = doc.to_dict()
    if not pwd_context.verify(user.password, user_data["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    doc.reference.delete()

    return {"message": "Account deleted successfully"}









