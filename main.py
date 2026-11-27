import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, Boolean, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hamo_smm.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(String(300), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, default=100)
    max_quantity: Mapped[int] = mapped_column(Integer, default=100000)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    service_title: Mapped[str] = mapped_column(String(140))
    target_link: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    admin_note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="HAMO STORE SMM API")
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY", "change-this-secret-before-production"))
COOKIE_NAME = "hamo_smm_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def session_data(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return serializer.loads(token, max_age=60 * 60 * 24 * 14)
    except (BadSignature, SignatureExpired):
        return None

def current_user(request: Request, db: Session = Depends(get_db)):
    data = session_data(request)
    if not data or data.get("role") != "customer":
        raise HTTPException(401, "سجل الدخول أولاً")
    user = db.get(Customer, data.get("id"))
    if not user:
        raise HTTPException(401, "الحساب غير موجود")
    return user

def admin_only(request: Request):
    data = session_data(request)
    if not data or data.get("role") != "admin":
        raise HTTPException(403, "غير مسموح")
    return data

def set_session(response: Response, payload: dict):
    token = serializer.dumps(payload)
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE,
                        samesite="lax", max_age=60 * 60 * 24 * 14, path="/")

class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    password: str = Field(min_length=8, max_length=128)

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class AdminLoginBody(BaseModel):
    username: str
    password: str

class ServiceBody(BaseModel):
    platform: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=300)
    price: int = Field(ge=0)
    min_quantity: int = Field(default=100, ge=1)
    max_quantity: int = Field(default=100000, ge=1)
    active: bool = True

class OrderBody(BaseModel):
    service_id: int
    target_link: str = Field(min_length=5, max_length=1000)
    quantity: int = Field(ge=1)

class StatusBody(BaseModel):
    status: str
    admin_note: str = Field(default="", max_length=500)

def service_json(item):
    return {"id": item.id, "platform": item.platform, "title": item.title,
            "description": item.description, "price": item.price,
            "min_quantity": item.min_quantity, "max_quantity": item.max_quantity,
            "active": item.active}

def order_json(item):
    return {"id": item.id, "customer_id": item.customer_id, "service_id": item.service_id,
            "service_title": item.service_title, "target_link": item.target_link,
            "quantity": item.quantity, "total_price": item.total_price,
            "status": item.status, "admin_note": item.admin_note,
            "created_at": item.created_at.isoformat()}

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/admin")
def admin_page():
    return FileResponse(BASE_DIR / "admin.html")

@app.get("/style.css")
def stylesheet():
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")

@app.get("/script.js")
def frontend_script():
    return FileResponse(BASE_DIR / "script.js", media_type="application/javascript")

@app.get("/admin.js")
def admin_script():
    return FileResponse(BASE_DIR / "admin.js", media_type="application/javascript")

@app.get("/admin.css")
def admin_stylesheet():
    return FileResponse(BASE_DIR / "admin.css", media_type="text/css")

@app.get("/api/health")
def health():
    return {"ok": True, "service": "HAMO STORE SMM"}

@app.post("/api/register")
def register(body: RegisterBody, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(Customer).where(Customer.email == email)):
        raise HTTPException(409, "البريد الإلكتروني مسجل بالفعل")
    user = Customer(name=body.name.strip(), email=email, phone=body.phone.strip(),
                    password_hash=pwd_context.hash(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session(response, {"role": "customer", "id": user.id})
    return {"ok": True, "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.post("/api/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(Customer).where(Customer.email == body.email.lower()))
    if not user or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(401, "بيانات الدخول غير صحيحة")
    set_session(response, {"role": "customer", "id": user.id})
    return {"ok": True, "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.post("/api/admin/login")
def admin_login(body: AdminLoginBody, response: Response):
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        raise HTTPException(503, "اضبط ADMIN_USERNAME و ADMIN_PASSWORD في إعدادات الاستضافة")
    if not secrets.compare_digest(body.username, username) or not secrets.compare_digest(body.password, password):
        raise HTTPException(401, "بيانات الإدارة غير صحيحة")
    set_session(response, {"role": "admin", "id": 0})
    return {"ok": True}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

@app.get("/api/me")
def me(user: Customer = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone}

@app.get("/api/services")
def list_services(db: Session = Depends(get_db)):
    items = db.scalars(select(Service).where(Service.active == True).order_by(Service.platform, Service.id)).all()
    return [service_json(item) for item in items]

@app.post("/api/orders")
def create_order(body: OrderBody, user: Customer = Depends(current_user), db: Session = Depends(get_db)):
    service = db.get(Service, body.service_id)
    if not service or not service.active:
        raise HTTPException(404, "الخدمة غير متاحة")
    if body.quantity < service.min_quantity or body.quantity > service.max_quantity:
        raise HTTPException(400, f"الكمية يجب أن تكون بين {service.min_quantity} و{service.max_quantity}")
    total = (service.price * body.quantity + 999) // 1000
    order = Order(customer_id=user.id, service_id=service.id, service_title=service.title,
                  target_link=body.target_link.strip(), quantity=body.quantity,
                  total_price=total, status="pending_payment")
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"ok": True, "order": order_json(order)}

@app.get("/api/orders")
def my_orders(user: Customer = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Order).where(Order.customer_id == user.id).order_by(Order.id.desc())).all()
    return [order_json(item) for item in items]

@app.get("/api/admin/summary")
def admin_summary(_=Depends(admin_only), db: Session = Depends(get_db)):
    return {"customers": db.query(Customer).count(), "orders": db.query(Order).count(),
            "pending": db.query(Order).filter(Order.status == "pending_payment").count(),
            "revenue": sum(row[0] for row in db.query(Order.total_price).filter(Order.status == "completed").all())}

@app.get("/api/admin/orders")
def admin_orders(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(Order).order_by(Order.id.desc())).all()
    return [order_json(row) for row in rows]

@app.patch("/api/admin/orders/{order_id}")
def update_order(order_id: int, body: StatusBody, _=Depends(admin_only), db: Session = Depends(get_db)):
    allowed = {"pending_payment", "paid", "processing", "completed", "rejected", "cancelled"}
    if body.status not in allowed:
        raise HTTPException(400, "حالة الطلب غير صحيحة")
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "الطلب غير موجود")
    order.status = body.status
    order.admin_note = body.admin_note
    db.commit()
    return {"ok": True, "order": order_json(order)}

@app.get("/api/admin/services")
def admin_services(_=Depends(admin_only), db: Session = Depends(get_db)):
    items = db.scalars(select(Service).order_by(Service.platform, Service.id)).all()
    return [service_json(item) for item in items]

@app.post("/api/admin/services")
def add_service(body: ServiceBody, _=Depends(admin_only), db: Session = Depends(get_db)):
    if body.max_quantity < body.min_quantity:
        raise HTTPException(400, "الحد الأقصى أقل من الحد الأدنى")
    item = Service(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return service_json(item)

@app.put("/api/admin/services/{service_id}")
def edit_service(service_id: int, body: ServiceBody, _=Depends(admin_only), db: Session = Depends(get_db)):
    item = db.get(Service, service_id)
    if not item:
        raise HTTPException(404, "الخدمة غير موجودة")
    if body.max_quantity < body.min_quantity:
        raise HTTPException(400, "الحد الأقصى أقل من الحد الأدنى")
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return service_json(item)

@app.delete("/api/admin/services/{service_id}")
def remove_service(service_id: int, _=Depends(admin_only), db: Session = Depends(get_db)):
    item = db.get(Service, service_id)
    if not item:
        raise HTTPException(404, "الخدمة غير موجودة")
    linked_orders = db.query(Order).filter(Order.service_id == service_id).count()
    if linked_orders:
        item.active = False
        db.commit()
        return {"ok": True, "removed": False, "archived": True,
                "message": "تمت إزالة الخدمة من المتجر مع الاحتفاظ بها لسجل الطلبات السابقة"}
    db.delete(item)
    db.commit()
    return {"ok": True, "removed": True, "archived": False,
            "message": "تمت إزالة الخدمة نهائياً"}

app.mount("/assets", StaticFiles(directory=BASE_DIR), name="assets")
