from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL Database URL (you’ll modify this later)
DATABASE_URL = "postgresql://postgres:root@localhost/teamsync_db"

# Engine - connects SQLAlchemy to your actual database
engine = create_engine(DATABASE_URL)

# Session - used to talk to the database in each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for creating models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
