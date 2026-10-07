from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_PATH = "sqlite:////data/starlite.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # plaintext on purpose - this is a vuln lab
    balance = Column(Float, default=5.0)
    is_admin = Column(Boolean, default=False)
    email = Column(String, default="")


class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    genre = Column(String)
    year = Column(Integer)
    rental_price = Column(Float, default=2.0)
    stock = Column(Integer, default=3)


class Snack(Base):
    __tablename__ = "snacks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=100)


class Rental(Base):
    __tablename__ = "rentals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, ForeignKey("movies.id"))
    qty = Column(Integer, default=1)


def init_db():
    import os
    os.makedirs("/data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
