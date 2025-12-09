import pymysql
from pymysql.err import OperationalError

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "123456"
DB_NAME = "gym_manager"
DB_PORT = 3306

def create_database():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            print(f"Database '{DB_NAME}' created or already exists.")
        
        connection.close()
        return True
        
    except OperationalError as e:
        print(f"Error connecting to MySQL: {e}")
        print("\nPlease check:")
        print("1. MySQL server is running")
        print("2. Username and password are correct")
        print("3. Port 3306 is accessible")
        return False

if __name__ == "__main__":
    create_database()
