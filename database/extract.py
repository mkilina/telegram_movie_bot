import mysql.connector, os
from mysql.connector import Error
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import Date, Time

db_config = {
    'host': os.getenv('DB_HOST'), 
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

DB_TABLE = os.getenv('DB_TABLE')

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Database connection successful")
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None
    

def get_db_engine():
    try:
        engine = create_engine(f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}")
        return engine
    except Error as e:
        print(f"Error: {e}")
        return None
    

def fetch_data(query, params=None):
    connection = get_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor(dictionary=True)  # Use dictionary=True for results as dictionaries
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def insert_data(filename='timetable.csv', table_name=DB_TABLE):
    engine = get_db_engine()
    df = pd.read_csv(filename)
    df.to_sql(table_name, con=engine, if_exists='replace', index=False, dtype={'date': Date, 'time': Time})
    return True

if __name__ == '__main__':
    insert_data()
