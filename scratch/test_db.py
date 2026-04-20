import pymysql
try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='tpsg_db'
    )
    print("Connection successful")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
