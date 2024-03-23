from fastapi import Body, FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, Session, create_engine, Field, select, delete
from fastapi_neon.password_validation import password_check
from fastapi_neon import settings
from typing import Optional, Annotated, List
from fastapi.responses import JSONResponse
router = APIRouter()
# Define the Todo modela
class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field()
    uid:int=Field(default=None, foreign_key="users.uid")

class Users(SQLModel, table=True):
    uid: Optional[int] = Field(default=None, primary_key=True)
    uname: str = Field(index=True)
    password: str = Field()

# Database URL adjustment
connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")

# Create the database engine
engine = create_engine(connection_string, connect_args={"sslmode": "require"}, pool_recycle=300)

# Function to create database and tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Lifespan function for table creation
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables...")
    create_db_and_tables()
    yield

# FastAPI app initialization with CORS middleware
app = FastAPI(lifespan=lifespan, title="Todo API", version="1.0.0",
              servers=[
                  {"url": "https://related-frog-charmed.ngrok-free.app/", "description": "Development Server"}
              ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # This now explicitly includes PATCH and DELETE
    allow_headers=["*"],
)

# Session dependency
def get_session():
    with Session(engine) as session:
        yield session

# Root endpoint
@app.get("/")
def read_root():
    return {"Todo Multiuser App!"}

# # Create Todo
@app.post("/todos/", response_model=Todo)
def create_todo(todo: Todo, session: Annotated[Session, Depends(get_session)]):
    existing_uid = session.exec(select(Users).where(Users.uid == todo.uid)).first()
    if not existing_uid:
        raise HTTPException(status_code=404,detail="User Not Found!")
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

# # Read Todos
@app.get("/todos/{uid}", response_model=List[Todo])
def read_todos(uid: int, session: Annotated[Session, Depends(get_session)]):
    todos = session.exec(select(Todo).where(Todo.uid == uid)).all()
    return todos

# # Update Todo
@app.patch("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo: Todo, session: Annotated[Session, Depends(get_session)]):
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo_data = todo.dict(exclude_unset=True)
    for key, value in todo_data.items():
        setattr(db_todo, key, value)
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo
@app.patch("/users/{user_id}/", response_model=dict)
def update_user_password(user_id: int, session: Annotated[Session, Depends(get_session)],new_password: str = Body(..., embed=True)):
    # Check if the user exists
    db_user = session.get(Users, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the new password is the same as the current one
    if db_user.password == new_password:
        raise HTTPException(status_code=400, detail="Password cannot be updated to your current password")

    # Validate the new password
    try:
        password_check(new_password)
    except ValueError as e:  # Assuming password_check raises ValueError for invalid passwords
        raise HTTPException(status_code=400, detail=str(e))

    # Update the password
    db_user.password = new_password
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return {"message": "Password updated successfully"}
# # Delete Todo
@app.delete("/todos/{todo_id}", response_model=Todo)
def delete_todo(todo_id: int, session: Annotated[Session, Depends(get_session)]):
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    session.delete(db_todo)
    session.commit()
    return db_todo

# Add User
@app.post("/users/", response_model=Users)
def create_user(user: Users, session: Annotated[Session, Depends(get_session)]):
    # Check if the username already exists
    existing_user = session.exec(select(Users).where(Users.uname == user.uname)).first()
    user_pass= user.password
    if existing_user:
        raise HTTPException(status_code=400, detail="This username Already exists!")
    password_check(user_pass)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
@router.post("/login/")
def login(session: Annotated[Session, Depends(get_session)],uname: str = Body(...), password: str = Body(...)):
    # Check if the username exists
    user = session.exec(select(Users).where(Users.uname == uname)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Username not found")

    # Verify the password
    if user.password != password:
        raise HTTPException(status_code=401, detail="Incorrect password")

    # On successful login, return the uid and a message indicating where to redirect
    return JSONResponse(status_code=200, content={"message": "Login successful", "uid": user.uid, "username":"Bilawal"})

# Include the router in the application
app.include_router(router)
# # Read Users
@app.get("/users/", response_model=List[Users])
def read_users(session: Annotated[Session, Depends(get_session)]):
    users = session.exec(select(Users)).all()
    return users

# Delete Users
@app.delete("/users/{user_id}", response_model=dict)
def delete_user(user_id: int, session: Annotated[Session, Depends(get_session)]):
    # First, check if the user exists
    db_user = session.get(Users, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete todos associated with the user
    session.execute(delete(Todo).where(Todo.uid == user_id))
    session.commit()  # Commit the deletion of the todos

    # Now delete the user
    session.delete(db_user)
    session.commit()  # Commit the deletion of the user
    
    return {"message": "User and associated todos deleted successfully"}