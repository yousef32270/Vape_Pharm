# import psycopg2

# DB_HOST = "localhost"
# DB_NAME = "my_flask_db"
# DB_USER = "postgres"
# DB_PASS = "124"
# DB_PORT = 5432

# def get_db_connection():
#     return psycopg2.connect(
#         host=DB_HOST,
#         database=DB_NAME,
#         user=DB_USER,
#         password=DB_PASS,
#         port=DB_PORT,
    

# CREATE TABLE users (
#     id SERIAL PRIMARY KEY,
#     username VARCHAR(50) UNIQUE NOT NULL,
#     password VARCHAR(255) NOT NULL
# );
#     )

import psycopg2

# DB config
DB_HOST = "localhost"
DB_NAME = "Vape_Pharm"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_PORT = 5432

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

def create_vape_table():
    conn = get_db_connection()
    cur = conn.cursor()



    cur.execute("""
        CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

# Run the function
create_vape_table()
