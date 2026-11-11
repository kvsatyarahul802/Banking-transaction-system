from db import connect

try:
    mydb = connect()

    if mydb.is_connected():
        print("Successfully connected to Aiven!")

    mydb.close()

except Exception as e:
    print("Connection failed:", e)