import psycopg2
import datetime

with open('basepass.txt', 'r') as file:
    password_db = file.readline().strip()
    name_db = file.readline().strip()

DSN = f"database='netology_db', user='postgres', password='123456'"

def create_db(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS search (
            id_vk INT UNIQUE NOT NULL,
            date_search DATE);
        """)
        conn.commit()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS black_list (
                id_vk INT UNIQUE NOT NULL);
        """)
        conn.commit()

def show_data(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_vk FROM search s;
        """)
        result = cur.fetchall()
        # print(result)
        result_list = []
        for i in result:
            result_list.append(i[0])
        return result_list

def add_data(conn, new_id):
    date_is = datetime.date.today()
    with conn.cursor() as cur:
        param = """
            INSERT INTO search
            VALUES(%s, %s);
        """
        data = (new_id, date_is)
        cur.execute(param, data)
        conn.commit()

def drop_tbs(conn):
    with conn.cursor() as cur:
        cur.execute("""
            DROP TABLE search CASCADE;
        """)
        conn.commit()

def clean_tbs(conn):
    with conn.cursor() as cur:
        cur.execute("""
            TRUNCATE TABLE search;
        """)
        conn.commit()

