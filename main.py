from database import SessionLocal, engine
from fastapi import Depends, FastAPI, HTTPException
import models
from sqlalchemy.orm import Session

# إنشاء الجداول في قاعدة البيانات تلقائياً
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DataPulse TON API")


# دالة الاتصال بقاعدة البيانات لكل طلب
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# الصفحة الرئيسية للتأكد أن الخادم يعمل
@app.get("/")
def read_root():
  return {"message": "Welcome to DataPulse TON Backend API is running successfully!"}


# مسار لتسجيل المستخدم أو التحقق من حسابه عبر تليجرام
@app.post("/users/")
def create_user(telegram_id: int, db: Session = Depends(get_db)):
  db_user = (
      db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
  )
  if db_user:
    return {"message": "User already exists", "user": db_user}
  new_user = models.User(telegram_id=telegram_id, balance=0.0)
  db.add(new_user)
  db.commit()
  db.refresh(new_user)
  return {"message": "User created successfully", "user": new_user}


# مسار لإضافة مهمة جديدة (للشركات أو الإدارة)
@app.post("/tasks/")
def create_task(
    title: str, description: str, reward: float, db: Session = Depends(get_db)
):
  new_task = models.Task(title=title, description=description, reward=reward)
  db.add(new_task)
  db.commit()
  db.refresh(new_task)
  return {"message": "Task created successfully", "task": new_task}


# مسار لعرض جميع المهام المتاحة للمستخدمين
@app.get("/tasks/")
def get_tasks(db: Session = Depends(get_db)):
  tasks = db.query(models.Task).filter(models.Task.is_active == 1).all()
  return {"available_tasks": tasks}

