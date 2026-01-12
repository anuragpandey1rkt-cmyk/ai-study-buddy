from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models, schemas, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Study Buddy Backend")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "Backend running"}

@app.post("/users")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

@app.post("/progress")
def add_progress(progress: schemas.ProgressCreate, db: Session = Depends(get_db)):
    return crud.add_progress(db, progress)
