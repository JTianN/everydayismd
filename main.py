from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_admin import credentials, firestore, initialize_app
from passlib.context import CryptContext
#ใหม่
from typing import Optional, List, Dict
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from typing import Optional, List, Dict, Any
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

# # --- ตั้งค่า Firebase ---Local Dev
# cred = credentials.Certificate("key23Apr.json")  # ใส่ path ให้ถูกต้อง
# initialize_app(cred)
# print("✅ Firebase connected successfully")

# --- ตั้งค่า Firebase ---server Dev    <----- เวลาใช้ให้ปรับส่วนนี้
# โหลด JSON จาก Environment Variable
firebase_cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIAL_JSON"))
# สร้าง credential จาก dict (ไม่ใช้ไฟล์)
cred = credentials.Certificate(firebase_cred_dict)
initialize_app(cred)
print("✅ Firebase connected successfully")


# ตั้งค่า DB & collection
db = firestore.client()
users_ref = db.collection("users")
profile_users_ref = db.collection("profile_users")  # เพิ่มมาใหม่


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
    return {"message": "Welcome to EveryDay in Monday ver4!"}

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

##################################################

# เพิ่มมาใหม่ --- ดึงข้อมูล profile_users ล่าสุด 10 คน ---
@app.get("/profile_users/latest")
def get_latest_profile_users():
    try:
        docs = profile_users_ref.order_by("name").limit(10).stream()  # เพิ่มมาใหม่
        profile_users = [doc.to_dict() for doc in docs]
        return {"profile_users": profile_users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# เพิ่มมาใหม่ --- ดึงข้อมูล profile_user ตามชื่อ ---
@app.get("/profile_users/{name}")
def get_profile_user_by_name(name: str):
    try:
        docs = profile_users_ref.where("name", "==", name).stream()  # เพิ่มมาใหม่
        doc = next(docs, None)
        if not doc:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูล profile_user")
        return {"profile_user": doc.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# เพิ่มมาใหม่ --- อัปเดตข้อมูล profile_user โดยใช้ ID ---
@app.put("/profile_users/name/{name}")
async def update_profile_user_by_name(name: str, profile_user: CreateProfileUser):
    try:
        docs = profile_users_ref.where("name", "==", name).stream()
        doc = next(docs, None)
        if not doc or not doc.exists:
            raise HTTPException(status_code=404, detail="ไม่พบ profile_user ที่มีชื่อนี้")

        doc.reference.set(profile_user.dict())  # แทนที่ document ทั้งหมด
        return {"message": "อัปเดต profile_user สำเร็จ"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# เพิ่มมาใหม่ --- อัปเดตแค่บาง attributes ของ profile_user โดยใช้ ID ---
@app.put("/profile_users/name/{name}/attributes")
async def update_attributes_by_name(name: str, updates: Dict[str, Any]):
    try:
        docs = profile_users_ref.where("name", "==", name).stream()
        doc = next(docs, None)
        if not doc or not doc.exists:
            raise HTTPException(status_code=404, detail="ไม่พบ profile_user ที่มีชื่อนี้")

        doc.reference.update(updates)  # อัปเดตเฉพาะฟิลด์ที่ส่งมา
        return {"message": "อัปเดต attributes ของ profile_user สำเร็จ"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# เพิ่ม API สำหรับสร้าง profile_user
@app.post("/profile_users")
async def create_profile_user(profile_user: CreateProfileUser):
    try:
        new_data = profile_user.dict()
        profile_users_ref.add(new_data)
        return {"message": "สร้าง profile_user สำเร็จ", "data": new_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

