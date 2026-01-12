from sqlalchemy.orm import Session
import models, schemas

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def add_progress(db: Session, progress: schemas.ProgressCreate):
    db_progress = models.Progress(**progress.dict())
    db.add(db_progress)
    db.commit()
    return db_progress
