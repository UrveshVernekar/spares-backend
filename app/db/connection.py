import psycopg2
from sqlalchemy import create_engine
from app.config import settings


def get_connection():
    return psycopg2.connect(settings.DATABASE_URL)

# SQLAlchemy engine for pandas and ORM use
engine = create_engine(settings.DATABASE_URL)