from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from connection import Base  # Import Base and sessionmaker from connection.py

# Questionnaire table
class Questionnaire(Base):
    __tablename__ = "questionnaires"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    owner_id = Column(Integer, nullable=False)  # Admin ID

    options = relationship("Option", back_populates="questionnaire")

# Option table for each questionnaire
class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"))
    votes = Column(Integer, default=0)

    questionnaire = relationship("Questionnaire", back_populates="options")
