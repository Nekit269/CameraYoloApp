import os
import databases

from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
db = databases.Database(database_url)