import sqlite3
connection = sqlite3.connect("budget.db")
with open("schema.sql") as file:
    schema = file.read()

connection.executescript(schema)

connection.close()

print("Base initialized!")