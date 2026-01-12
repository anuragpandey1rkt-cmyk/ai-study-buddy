from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://study_buddy_db_gpua_user:SlDUsn8jgdbnUbGYAMkvqAB6IeV9U9ts@dpg-d5ia0kv5r7bs73btc0tg-a/study_buddy_db_gpua"


engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
