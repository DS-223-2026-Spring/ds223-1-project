from SQLHandler import SQLHandler

inst = SQLHandler(host="127.0.0.1", dbname="reporting_db", 
                  user="postgres", password="MuhammadAli@25")

query = """
SELECT *
FROM dbo.sales
"""

inst.set_schema('dbo')
df = inst.select(query=query)
print(type(df))

data = inst.from_sql(query)
print(data)

##inst.commit()
inst.close()