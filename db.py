import psycopg2
from psycopg2 import sql

def connect_db():
    try:
        conn = psycopg2.connect(
            dbname="scraper",
            user="Mark",
            password="Makfam123",
            host="localhost",  
            port="5432"       
        )
        return conn
    except Exception as e:
        return f"An error occurred while connecting to the database: {e}"

def insert_table_data(conn, table_data):
    try:
        with conn.cursor() as cur:
            for idx, table in enumerate(table_data):
                cur.execute(sql.SQL(
                    "INSERT INTO your_table_name (table_idx, table_html) VALUES (%s, %s)"
                ), [idx + 1, table])
            conn.commit()
    except Exception as e:
        return f"An error occurred while inserting data into the database: {e}"
