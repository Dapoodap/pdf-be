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
    is_premium = Column(Boolean, default=False)

    transactions = relationship("Transaction", back_populates="user")
    file_histories = relationship("FileHistory", back_populates="user")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    pricings = relationship("Pricing", back_populates="service")
    file_histories = relationship("FileHistory", back_populates="service")

class Pricing(Base):
    __tablename__ = "pricings"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    price = Column(Float, default=0.0)

    service = relationship("Service", back_populates="pricings")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")

class FileHistory(Base):
    __tablename__ = "file_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String)
    file_name = Column(String)
    file_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="file_histories")
    service = relationship("Service", back_populates="file_histories")
