from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime


engine = create_engine("sqlite:///shop.db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String, nullable=True)
    total = Column(Integer)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_name = Column(String)
    price = Column(Integer)
    order = relationship("Order", back_populates="items")

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()