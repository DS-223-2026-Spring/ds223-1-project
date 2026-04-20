<<<<<<< HEAD
"""DS service entrypoint."""

try:
    from .synthetic.cli import main
except ImportError:  # pragma: no cover - supports running inside the ds container
    from synthetic.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
=======
# from SQLHandler import SQLHandler
# import os
# from dotenv import load_dotenv

# load_dotenv()

# DB_NAME = os.getenv("POSTGRES_DB")
# DB_USER = os.getenv("POSTGRES_USER")
# DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# inst = SQLHandler(
#     host="db", 
#     dbname=DB_NAME,  
#     user=DB_USER, 
#     password=DB_PASSWORD)

# query = """
# SELECT *
# FROM dbo.sales
# """

# inst.set_schema('dbo')
# df = inst.select(query=query)
# print(type(df))

# data = inst.from_sql(query)
# print(data)

# ##inst.commit()
# inst.close()

from SQLHandler import SQLHandler
import os
from dotenv import load_dotenv
import db.db_interactions as dbi
from loguru import logger

load_dotenv()

db = SQLHandler(
    host="db",
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)

print(os.getenv("POSTGRES_PASSWORD"))
logger.error(os.getenv("POSTGRES_PASSWORD"))

# use CRUD with injected handler
customers = dbi.get_all_customers(db)
print(customers.shape)

sim_id = dbi.create_simulation(db, "test", 10, 100, 0.5)
print(sim_id)

db.close()
>>>>>>> main
