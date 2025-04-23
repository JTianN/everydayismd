from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_admin import credentials, firestore, initialize_app
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# --- โหลดค่า Environment Variables ---
#load_dotenv() #####

# --- ตั้งค่า Firebase ---
# cred = credentials.Certificate(os.getenv("FIREBASE_KEY_PATH"))
# initialize_app(cred)
# db = firestore.client()
# users_ref = db.collection("users")

cred = credentials.Certificate("MyKey.json")  # <<< ใส่ path ที่ถูกต้องตรงนี้
initialize_app(cred)
db = firestore.client()
users_ref = db.collection("users")


# --- FastAPI App ---
app = FastAPI()

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Models สำหรับ Request ---
class User(BaseModel):
    email: str
    password: str


# --- welcome server ---
@app.get("/")
def home():
    return {"message": "Welcome to EveryDay in Monday!"}

# --- Register User ---
@app.post("/register")
async def register(user: User):
    # เช็คว่า email นี้ถูกใช้แล้วหรือยัง
    existing = users_ref.where("email", "==", user.email).stream()
    if any(existing):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash Password แล้วเก็บใน Firestore
    hashed_password = pwd_context.hash(user.password)
    users_ref.add({"email": user.email, "password": hashed_password})

    return {"message": "Registration successful"}

# --- Login User ---
@app.post("/login")
async def login(user: User):
    # หา email ที่ตรงกันใน Firestore
    docs = users_ref.where("email", "==", user.email).stream()
    doc = next(docs, None)
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    user_data = doc.to_dict()

    # ตรวจสอบ Password
    if not pwd_context.verify(user.password, user_data["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {"message": "Login successful", "email": user.email}

@app.delete("/delete")
async def delete_account(user: User):
    # ค้นหา email
    docs = users_ref.where("email", "==", user.email).stream()
    doc = next(docs, None)
    if not doc:
        raise HTTPException(status_code=400, detail="Account not found")

    user_data = doc.to_dict()

    # ตรวจสอบ password
    if not pwd_context.verify(user.password, user_data["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # ลบ document
    users_ref.document(doc.id).delete()

    return {"message": "Account deleted successfully"}


