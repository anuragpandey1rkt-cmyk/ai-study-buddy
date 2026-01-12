import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("postgresql://study_buddy_db_gpua_user:SlDUsn8jgdbnUbGYAMkvqAB6IeV9U9ts@dpg-d5ia0kv5r7bs73btc0tg-a/study_buddy_db_gpua")

# Detect database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Render)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
