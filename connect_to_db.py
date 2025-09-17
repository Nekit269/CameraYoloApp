import os
import psycopg2

from dotenv import load_dotenv

load_dotenv()

db_host = os.getenv("HOST")
db_name = os.getenv("DATABASE")
db_user = os.getenv("USER")
db_password = os.getenv("PASSWORD")

def connect_to_db():
    try:
        with psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            print('Connected to the PostgreSQL server.')
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)

if __name__ == '__main__':
    connect_to_db()