from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt

class Settings(BaseSettings):
    SECRET_KEY: str = "mysecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

settings = Settings()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


fake_users_db: Dict[str, Dict[str, Any]] = {}
fake_groups_db: Dict[str, Any] = {}

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or not verify_password(password, user["password"]):
        return False
    return user

def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(required_roles: List[str]):
    def dependency(payload: dict = Depends(get_token_payload)):
        roles = payload.get("roles", [])
        if not any(r in roles for r in required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: insufficient role")
        return payload
    return dependency


class RegisterResponse(BaseModel):
    msg: str
    username: str
    roles: List[str]
    groups: List[str]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@app.post("/register", response_model=RegisterResponse)
def register(username: str = Form(...), password: str = Form(...), role: str = Form("user"), groups: Optional[str] = Form("")):
    if username in fake_users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    groups_list = [g.strip() for g in groups.split(",") if g.strip()]
    fake_users_db[username] = {
        "username": username,
        "password": hash_password(password),
        "roles": [role],
        "groups": groups_list
    }
    for g in groups_list:
        fake_groups_db.setdefault(g, {"members": []})["members"].append(username)
    return {"msg": "User registered successfully", "username": username, "roles": [role], "groups": groups_list}

@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    payload = {"sub": user["username"], "roles": user["roles"], "groups": user["groups"]}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/refresh")
def refresh_token(payload: dict = Depends(get_token_payload)):
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    new_access = create_access_token({"sub": payload["sub"], "roles": payload.get("roles", []), "groups": payload.get("groups", [])})
    return {"access_token": new_access, "token_type": "bearer"}

@app.get("/protected")
def protected(payload: dict = Depends(get_token_payload)):
    return {"msg": f"Hello {payload.get('sub')}", "roles": payload.get("roles")}

@app.get("/admin/users")
def list_users(payload: dict = Depends(require_role(["admin"]))):
    users = {u: {"roles": info["roles"], "groups": info["groups"]} for u, info in fake_users_db.items()}
    return {"users": users}


@app.post("/groups/create")
def create_group(
    group_name: str = Form(...),
    budget: float = Form(...),
    add_creator: bool = Form(True),
    payload: dict = Depends(get_token_payload)
):
    if group_name in fake_groups_db:
        raise HTTPException(status_code=400, detail="Group already exists")
    creator = payload["sub"]
    fake_groups_db[group_name] = {
        "admin": creator,
        "budget": budget,
        "members": [],
        "split_amount": 0,
        "payments": {}
    }
    if add_creator:
        fake_groups_db[group_name]["members"].append(creator)
    fake_groups_db[group_name]["split_amount"] = budget / len(fake_groups_db[group_name]["members"])
    for member in fake_groups_db[group_name]["members"]:
        fake_groups_db[group_name]["payments"][member] = {"paid_amount": 0, "status": "unpaid"}
    return {"msg": f"Group '{group_name}' created", "details": fake_groups_db[group_name]}

@app.post("/groups/add-user")
def add_user_to_group(username: str = Form(...), group_name: str = Form(...)):
    if username not in fake_users_db:
        raise HTTPException(status_code=404, detail="User not found")
    group = fake_groups_db.get(group_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if username not in group["members"]:
        group["members"].append(username)
        fake_users_db[username]["groups"].append(group_name)
    # Recalculate split
    total_members = len(group["members"])
    group["split_amount"] = round(group["budget"] / total_members, 2)
    for m in group["members"]:
        group["payments"].setdefault(m, {"paid_amount": 0, "status": "unpaid"})
    return {"msg": f"User '{username}' added", "split_per_member": group["split_amount"]}

@app.post("/groups/{group_name}/pay")
def pay_share(group_name: str, amount: float = Form(...), payload: dict = Depends(get_token_payload)):
    username = payload["sub"]
    group = fake_groups_db.get(group_name)
    if not group or username not in group["members"]:
        raise HTTPException(status_code=403, detail="Not part of this group")
    split = group["split_amount"]
    payment = group["payments"][username]
    if amount > split:
        raise HTTPException(status_code=400, detail="Exceeds threshold amount")
    payment["paid_amount"] = amount
    payment["status"] = "pending_approval"
    return {"msg": "Payment submitted, pending approval", "your_status": payment}

@app.post("/groups/{group_name}/approve")
def approve_payment(group_name: str, username: str = Form(...), action: str = Form(...), payload: dict = Depends(get_token_payload)):
    group = fake_groups_db.get(group_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload["sub"] != group["admin"]:
        raise HTTPException(status_code=403, detail="Only admin can approve payments")
    if username not in group["payments"]:
        raise HTTPException(status_code=404, detail="User not in this group")
    payment = group["payments"][username]
    split = group["split_amount"]
    if action == "approve" and payment["paid_amount"] == split:
        payment["status"] = "approved"
    elif action == "deny":
        payment["status"] = "denied"
    else:
        payment["status"] = "pending"
    return {"msg": f"{username}'s payment {payment['status']}", "details": payment}

@app.get("/groups/{group_name}/status")
def group_status(group_name: str, payload: dict = Depends(get_token_payload)):
    group = fake_groups_db.get(group_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload["sub"] not in group["members"]:
        raise HTTPException(status_code=403, detail="You are not part of this group")
    return {"group": group_name, "details": group}

@app.get("/groups")
def list_groups():
    return {"groups": fake_groups_db}

# # import uvicorn

# if __name__ == '__main__':
#     uvicorn.run(app, port=8080, host='0.0.0.0')