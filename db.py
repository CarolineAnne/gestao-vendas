import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Se tiver senha no MySQL, coloque aqui
            database="controle_vendas"
        )
        return conn
    except Error as e:
        print("Erro ao conectar ao MySQL:", e)
        return None
