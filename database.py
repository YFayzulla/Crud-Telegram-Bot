from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text  
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

DB_USER = "root"
DB_PASSWORD = ""
DB_HOST = "localhost"  
DB_NAME = "tgbot"

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE();"))
            database = result.fetchone()[0]
            print(f"Connected to the database: {database}")
    except Exception as e:
        print(f"Error connecting to the database: {e}")

if __name__ == "__main__":
    test_connection()



# Questionnaire table
class Questionnaire(Base):
    __tablename__ = "questionnaires"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    owner_id = Column(Integer, nullable=False)  # Admin ID

    options = relationship("Option", back_populates="questionnaire")

# Options for each questionnaire
class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"))
    votes = Column(Integer, default=0)

    questionnaire = relationship("Questionnaire", back_populates="options")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)