from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

DB_USER = "root"  # Default XAMPP user
DB_PASSWORD = ""  # Default XAMPP password for root (empty by default)
DB_HOST = "localhost"
DB_NAME = "tgbot"

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
# Create engine to interact with MySQL
engine = create_engine(DATABASE_URL)

# SessionLocal is used to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("Connected to the database successfully!")
except Exception as e:
    print(f"Error: {e}")
