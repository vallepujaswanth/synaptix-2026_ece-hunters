# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for hackathon (easy to setup)
SQLALCHEMY_DATABASE_URL = "sqlite:///./vita_bot.db"
# For production, use PostgreSQL:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/vita_bot"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()