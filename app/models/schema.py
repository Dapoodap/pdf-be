from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    membership_status = Column(String, default="basic")

    transactions = relationship("Transaction", back_populates="user")
    file_histories = relationship("FileHistory", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    file_histories = relationship("FileHistory", back_populates="service")

class Pricing(Base):
    __tablename__ = "pricings"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, default=0.0)
    description = Column(String)
    plan_type = Column(String)
    duration_days = Column(Integer)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    amount = Column(Float)
    status = Column(String)
    
    order_id = Column(String, unique=True, index=True, nullable=True)
    midtrans_transaction_id = Column(String, nullable=True)
    payment_type = Column(String, nullable=True)
    snap_token = Column(String, nullable=True)
    snap_redirect_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pricing_id = Column(Integer, ForeignKey("pricings.id", ondelete="SET NULL"), nullable=True)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="subscriptions")

class FileHistory(Base):
    __tablename__ = "file_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String)
    file_name = Column(String)
    file_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="file_histories")
    service = relationship("Service", back_populates="file_histories")
