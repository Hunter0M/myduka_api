from sqlalchemy import create_engine # This function is used to create a new SQLAlchemy engine instance.
from sqlalchemy.ext.declarative import declarative_base # This function is used to create a base class,It allows you to define your database models as classes.
from sqlalchemy.orm import sessionmaker # This is a factory for creating new Session objects. A session is used to interact with the database, allowing you to add, delete, and query objects.


SQLALCHEMY_DATABASE_URL ="postgresql://postgres:0777@localhost/myduka_api"

engine=create_engine(SQLALCHEMY_DATABASE_URL) # This line creates an SQLAlchemy engine using the provided database URL.

sessionLocal=sessionmaker(bind=engine) # This line creates a session factory (sessionLocal) that is bound to the engine. When you call sessionLocal(), it will return a new session object that you can use to interact with the database.

Base = declarative_base() # This line creates a base class (Base) for declarative class definitions.

# This function is a generator that provides a database session.
def get_db():
    db=sessionLocal() # When called, it creates a new session (db = sessionLocal()).
    try:
        yield db #The yield statement returns the session to the caller, allowing them to perform database operations.
    finally:
        db.close()


# This to Create the tables
Base.metadata.create_all(bind=engine)




