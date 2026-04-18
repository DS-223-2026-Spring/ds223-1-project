"""SQLAlchemy models for database tables."""
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(Integer, primary_key=True)
    recency = Column(Float)
    frequency = Column(Float)
    monetary = Column(Float)
    basket_diversity = Column(Float)
    avg_order_size = Column(Float)
    purchase_regularity = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

class Action(Base):
    __tablename__ = "actions"
    action_id = Column(Integer, primary_key=True)
    action_name = Column(String(50))
    action_cost = Column(Float, default=0.0)
    description = Column(String)

class Interaction(Base):
    __tablename__ = "interactions"
    interaction_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"))
    action_id = Column(Integer, ForeignKey("actions.action_id"))
    reward = Column(Float)
    converted = Column(Boolean)
    revenue = Column(Float)
    cost = Column(Float)
    simulation_id = Column(String(50))
    round_number = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
