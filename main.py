import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, Boolean, select, update
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
def home(request: Request):
    data = session_data(request)
    if not data or data.get("role") != "customer":
        return RedirectResponse("/login", status_code=303)
    return FileResponse(BASE_DIR / "index.html")

@app.get("/login")
def login_page(request: Request):
    data = session_data(request)
    if data and data.get("role") == "customer":
        return RedirectResponse("/", status_code=303)
    return FileResponse(BASE_DIR / "login.html")

@app.get("/admin")
def admin_page():
    return FileResponse(BASE_DIR / "admin.html")

@app.get("/style.css")
def stylesheet():
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")

@app.get("/script.js")
def frontend_script():
    return FileResponse(BASE_DIR / "script.js", media_type="application/javascript")

@app.get("/login.js")
def login_script():
    return FileResponse(BASE_DIR / "login.js", media_type="application/javascript")

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
    db.flush()
    db.add(Wallet(customer_id=user.id, balance=0))
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
def list_services(user: Customer = Depends(current_user), db: Session = Depends(get_db)):
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
    if total < 1:
        raise HTTPException(400, "قيمة الطلب غير صحيحة")
    mapping = db.scalar(select(ProviderServiceMap).where(
        ProviderServiceMap.local_service_id == service.id))
    if mapping and not os.getenv("PANELFOLLOWS_API_KEY", "").strip():
        raise HTTPException(503, "خدمة المورد غير مفعّلة حاليًا. تواصل مع الإدارة.")
    wallet_for(db, user.id)
    # Atomic conditional debit prevents concurrent requests from spending the same balance.
    debit = db.execute(
        update(Wallet)
        .where(Wallet.customer_id == user.id, Wallet.balance >= total)
        .values(balance=Wallet.balance - total)
    )
    if debit.rowcount != 1:
        db.rollback()
        raise HTTPException(400, "رصيدك غير كافٍ. اشحن محفظتك أولاً.")
    wallet = db.scalar(select(Wallet).where(Wallet.customer_id == user.id))
    order = Order(customer_id=user.id, service_id=service.id, service_title=service.title,
                  target_link=body.target_link.strip(), quantity=body.quantity,
                  total_price=total, status="paid")
    db.add(order)
    db.flush()
    db.add(WalletTransaction(customer_id=user.id, amount=-total, balance_after=wallet.balance,
                             kind="order", reference=f"order:{order.id}",
                             note=f"خصم قيمة الطلب #{order.id}"))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    db.refresh(wallet)

    # If this service is mapped to PanelFollows, submit it server-side.
    if mapping:
        api_key = os.getenv("PANELFOLLOWS_API_KEY", "").strip()
        from provider_client import PanelFollowsClient
        try:
            provider_result = PanelFollowsClient(api_key).add_order(
                mapping.provider_service_id, body.target_link.strip(), body.quantity)
            provider_order_id = str(provider_result["order"])
            db.add(ProviderOrderMap(local_order_id=order.id,
                                    provider_order_id=provider_order_id,
                                    provider_status="Pending"))
            order.status = "processing"
            db.commit()
            db.refresh(order)
        except Exception as exc:
            db.rollback()
            # Provider submission failed: refund the already-debited customer wallet.
            wallet = db.scalar(select(Wallet).where(
                Wallet.customer_id == user.id).with_for_update())
            refund_ref = f"refund:provider-submit:{order.id}"
            exists = db.scalar(select(WalletTransaction).where(
                WalletTransaction.reference == refund_ref))
            if wallet and not exists:
                wallet.balance += total
                db.add(WalletTransaction(customer_id=user.id, amount=total,
                    balance_after=wallet.balance, kind="refund", reference=refund_ref,
                    note=f"استرداد تعذر تنفيذ الطلب #{order.id}"))
            order = db.get(Order, order.id)
            if order:
                order.status = "rejected"
                order.admin_note = "تعذر إرسال الطلب للمورد؛ تم رد المبلغ للمحفظة."
            db.commit()
            raise HTTPException(502, "المورد لم يقبل الطلب. تم رد المبلغ إلى محفظتك.") from exc

    return {"ok": True, "order": order_json(order), "wallet_balance": wallet.balance}

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
    transitions = {
        "pending_payment": {"paid", "rejected", "cancelled"},
        "paid": {"processing", "rejected", "cancelled"},
        "processing": {"completed"},
        "completed": set(),
        "rejected": set(),
        "cancelled": set(),
    }
    if body.status not in transitions:
        raise HTTPException(400, "حالة الطلب غير صحيحة")
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order:
        raise HTTPException(404, "الطلب غير موجود")
    if body.status != order.status and body.status not in transitions.get(order.status, set()):
        raise HTTPException(409, "لا يمكن تغيير حالة الطلب من الحالة الحالية.")
    if body.status in {"rejected", "cancelled"} and order.status in {"pending_payment", "paid"}:
        charged = db.scalar(select(WalletTransaction).where(
            WalletTransaction.reference == f"order:{order.id}"))
        wallet = db.scalar(select(Wallet).where(
            Wallet.customer_id == order.customer_id).with_for_update())
        if charged and wallet and order.total_price > 0:
            reference = f"refund:order:{order.id}"
            exists = db.scalar(select(WalletTransaction).where(
                WalletTransaction.reference == reference))
            if not exists:
                wallet.balance += order.total_price
                db.add(WalletTransaction(customer_id=order.customer_id, amount=order.total_price,
                    balance_after=wallet.balance, kind="refund", reference=reference,
                    note=f"استرداد قيمة الطلب #{order.id}"))
    order.status = body.status
    order.admin_note = body.admin_note.strip()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
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


# --- HAMO STORE wallet and manual top-ups ---
class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), unique=True, index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DepositRequest(Base):
    __tablename__ = "deposit_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(30))
    sender_reference: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    admin_note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class DepositBody(BaseModel):
    amount: int = Field(ge=10, le=100000)
    method: str = Field(min_length=3, max_length=30)
    sender_reference: str = Field(default="", max_length=120)

class DepositReviewBody(BaseModel):
    status: str
    admin_note: str = Field(default="", max_length=300)

def wallet_for(db: Session, customer_id: int):
    wallet = db.scalar(select(Wallet).where(Wallet.customer_id == customer_id).with_for_update())
    if not wallet:
        wallet = Wallet(customer_id=customer_id, balance=0)
        db.add(wallet)
        db.flush()
    return wallet

def transaction_json(item):
    return {"id": item.id, "amount": item.amount, "balance_after": item.balance_after,
            "kind": item.kind, "reference": item.reference, "note": item.note,
            "created_at": item.created_at.isoformat()}

def deposit_json(item, db: Session):
    customer = item.customer_id
    owner = db.get(Customer, customer)
    return {"id": item.id, "customer_id": customer,
            "customer_name": owner.name if owner else "", "customer_email": owner.email if owner else "",
            "customer_phone": owner.phone if owner else "", "amount": item.amount,
            "method": item.method, "sender_reference": item.sender_reference,
            "status": item.status, "admin_note": item.admin_note,
            "created_at": item.created_at.isoformat()}

@app.get("/wallet")
def wallet_page(request: Request):
    data = session_data(request)
    if not data or data.get("role") != "customer":
        return RedirectResponse("/login", status_code=303)
    return FileResponse(BASE_DIR / "wallet.html")

@app.get("/wallet.js")
def wallet_script():
    return FileResponse(BASE_DIR / "wallet.js", media_type="application/javascript")

@app.get("/wallet.css")
def wallet_stylesheet():
    return FileResponse(BASE_DIR / "wallet.css", media_type="text/css")

@app.get("/api/wallet")
def wallet_summary(user: Customer = Depends(current_user), db: Session = Depends(get_db)):
    wallet = wallet_for(db, user.id)
    db.commit()
    txs = db.scalars(select(WalletTransaction).where(
        WalletTransaction.customer_id == user.id).order_by(WalletTransaction.id.desc()).limit(50)).all()
    deposits = db.scalars(select(DepositRequest).where(
        DepositRequest.customer_id == user.id).order_by(DepositRequest.id.desc()).limit(20)).all()
    return {"balance": wallet.balance, "transactions": [transaction_json(x) for x in txs],
            "deposits": [deposit_json(x, db) for x in deposits]}

@app.post("/api/deposits")
def request_deposit(body: DepositBody, user: Customer = Depends(current_user), db: Session = Depends(get_db)):
    allowed_methods = {"vodafone_cash", "instapay", "bank_transfer"}
    if body.method not in allowed_methods:
        raise HTTPException(400, "طريقة الشحن غير متاحة")
    item = DepositRequest(customer_id=user.id, amount=body.amount, method=body.method,
                          sender_reference=body.sender_reference.strip())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "deposit": deposit_json(item, db),
            "message": "تم تسجيل طلب الشحن، وسيُضاف الرصيد بعد مراجعة الإدارة."}

@app.get("/api/admin/deposits")
def admin_deposits(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(DepositRequest).order_by(DepositRequest.id.desc()).limit(200)).all()
    return [deposit_json(x, db) for x in rows]

@app.patch("/api/admin/deposits/{deposit_id}")
def review_deposit(deposit_id: int, body: DepositReviewBody,
                   _=Depends(admin_only), db: Session = Depends(get_db)):
    if body.status not in {"approved", "rejected"}:
        raise HTTPException(400, "حالة طلب الشحن غير صحيحة")
    item = db.scalar(select(DepositRequest).where(DepositRequest.id == deposit_id).with_for_update())
    if not item:
        raise HTTPException(404, "طلب الشحن غير موجود")
    # Claim the pending request atomically; only one concurrent admin action can win.
    claimed = db.execute(
        update(DepositRequest)
        .where(DepositRequest.id == item.id, DepositRequest.status == "pending")
        .values(status=body.status, admin_note=body.admin_note.strip())
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "تمت مراجعة طلب الشحن بالفعل")
    if body.status == "approved":
        wallet = wallet_for(db, item.customer_id)
        db.execute(
            update(Wallet)
            .where(Wallet.customer_id == item.customer_id)
            .values(balance=Wallet.balance + item.amount)
        )
        db.flush()
        db.refresh(wallet)
        db.add(WalletTransaction(customer_id=item.customer_id, amount=item.amount,
            balance_after=wallet.balance, kind="deposit", reference=f"deposit:{item.id}",
            note=f"شحن رصيد عبر {item.method} — طلب #{item.id}"))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(item)
    return {"ok": True, "deposit": deposit_json(item, db)}

@app.get("/api/admin/customers")
def admin_customers(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(Customer).order_by(Customer.id.desc()).limit(500)).all()
    result = []
    for customer in rows:
        wallet = db.scalar(select(Wallet).where(Wallet.customer_id == customer.id))
        result.append({"id": customer.id, "name": customer.name, "email": customer.email,
                       "phone": customer.phone, "balance": wallet.balance if wallet else 0})
    return result

app.mount("/assets", StaticFiles(directory=BASE_DIR), name="assets")


# --- PanelFollows provider integration ---
class ProviderServiceMap(Base):
    __tablename__ = "provider_service_maps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    local_service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), unique=True, index=True)
    provider_service_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    provider_rate_usd: Mapped[str] = mapped_column(String(30), default="0")
    provider_min: Mapped[int] = mapped_column(Integer, default=1)
    provider_max: Mapped[int] = mapped_column(Integer, default=100000)

class ProviderOrderMap(Base):
    __tablename__ = "provider_order_maps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    local_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    provider_order_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    provider_status: Mapped[str] = mapped_column(String(40), default="Pending")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class ProviderImportBody(BaseModel):
    provider_service_id: str = Field(min_length=1, max_length=40)
    selling_price_egp: int = Field(ge=1)
    active: bool = False

def panel_follows_client():
    from provider_client import PanelFollowsClient
    key = os.getenv("PANELFOLLOWS_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "مفتاح PanelFollows غير مضبوط في إعدادات الاستضافة")
    return PanelFollowsClient(key)

@app.get("/api/admin/provider/status")
def provider_status(_=Depends(admin_only)):
    try:
        data = panel_follows_client().balance()
        return {"connected": True, "balance": data.get("balance"), "currency": data.get("currency", "USD")}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "تعذر الاتصال بـ PanelFollows؛ راجع المفتاح والرصيد.")

@app.get("/api/admin/provider/services")
def provider_services(_=Depends(admin_only)):
    try:
        items = panel_follows_client().services()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "تعذر تحميل قائمة خدمات المورد.")
    result = []
    for item in items:
        category = str(item.get("category", ""))
        name = str(item.get("name", ""))
        if "tiktok" not in (category + " " + name).lower():
            continue
        result.append({
            "provider_service_id": str(item.get("service", "")),
            "name": name, "category": category, "rate_usd": str(item.get("rate", "0")),
            "min": int(item.get("min", 1)), "max": int(item.get("max", 100000)),
            "refill": bool(item.get("refill", False)), "cancel": bool(item.get("cancel", False)),
            "type": str(item.get("type", "")),
        })
    return result

@app.post("/api/admin/provider/import")
def import_provider_service(body: ProviderImportBody, _=Depends(admin_only),
                            db: Session = Depends(get_db)):
    try:
        items = panel_follows_client().services()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "تعذر تحميل قائمة خدمات المورد.")
    remote = next((x for x in items if str(x.get("service")) == body.provider_service_id), None)
    if not remote:
        raise HTTPException(404, "خدمة المورد غير موجودة أو غير متاحة.")
    category = str(remote.get("category", ""))
    title = str(remote.get("name", ""))
    if "tiktok" not in (category + " " + title).lower():
        raise HTTPException(400, "يمكن استيراد خدمات TikTok فقط من هذا المسار.")
    if db.scalar(select(ProviderServiceMap).where(
        ProviderServiceMap.provider_service_id == body.provider_service_id)):
        raise HTTPException(409, "الخدمة مستوردة بالفعل.")
    minimum = max(1, int(remote.get("min", 1)))
    maximum = max(minimum, int(remote.get("max", 100000)))
    service = Service(platform="tiktok", title=title[:140],
        description="خدمة موردة عبر PanelFollows؛ السعر بالجنيه المصري لكل 1000.",
        price=body.selling_price_egp, min_quantity=minimum,
        max_quantity=maximum, active=body.active)
    db.add(service)
    db.flush()
    db.add(ProviderServiceMap(local_service_id=service.id,
        provider_service_id=body.provider_service_id,
        provider_rate_usd=str(remote.get("rate", "0")),
        provider_min=minimum, provider_max=maximum))
    db.commit()
    db.refresh(service)
    return {"ok": True, "service": service_json(service)}

@app.get("/api/admin/provider/orders")
def provider_orders(_=Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(ProviderOrderMap).order_by(ProviderOrderMap.id.desc()).limit(100)).all()
    return [{"local_order_id": x.local_order_id, "provider_order_id": x.provider_order_id,
             "provider_status": x.provider_status} for x in rows]

@app.post("/api/admin/provider/orders/{local_order_id}/sync")
def sync_provider_order(local_order_id: int, _=Depends(admin_only), db: Session = Depends(get_db)):
    mapping = db.scalar(select(ProviderOrderMap).where(
        ProviderOrderMap.local_order_id == local_order_id))
    order = db.get(Order, local_order_id)
    if not mapping or not order:
        raise HTTPException(404, "طلب المورد غير موجود.")
    try:
        data = panel_follows_client().status(mapping.provider_order_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "تعذر جلب حالة الطلب من المورد.")
    remote_status = str(data.get("status", "Unknown"))
    mapping.provider_status = remote_status
    normalized = remote_status.lower()
    terminal_statuses = {"completed", "cancelled", "rejected"}
    if normalized == "completed" and order.status not in terminal_statuses:
        order.status = "completed"
    elif normalized in {"pending", "in progress"} and order.status not in terminal_statuses:
        order.status = "processing"
    elif normalized in {"canceled", "cancelled"}:
        if order.status not in {"cancelled", "rejected", "completed"}:
            wallet = db.scalar(select(Wallet).where(
                Wallet.customer_id == order.customer_id).with_for_update())
            refund_ref = f"refund:provider-cancel:{order.id}"
            if wallet and not db.scalar(select(WalletTransaction).where(
                    WalletTransaction.reference == refund_ref)):
                wallet.balance += order.total_price
                db.add(WalletTransaction(customer_id=order.customer_id,
                    amount=order.total_price, balance_after=wallet.balance,
                    kind="refund", reference=refund_ref,
                    note=f"استرداد إلغاء المورد للطلب #{order.id}"))
            order.status = "cancelled"
            order.admin_note = "ألغى المورد الطلب وتم رد المبلغ للمحفظة."
    elif normalized == "partial":
        order.admin_note = f"المورد أبلغ أن الطلب جزئي؛ المتبقي: {data.get('remains', 'غير معروف')}"
    db.commit()
    return {"ok": True, "order": order_json(order),
            "provider_status": remote_status, "provider_charge_usd": data.get("charge"),
            "provider_remains": data.get("remains")}
