import mysql.connector


def setup():
    connect = mysql.connector.connect(user='root', password='LoveSosa1337', host='127.0.0.1', database='smallbro')
    return connect
