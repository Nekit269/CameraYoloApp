import os
import psycopg2

from configparser import ConfigParser

script_dir = os.path.dirname(os.path.abspath(__file__))
db_ini_path = os.path.join(script_dir, 'database.ini')

def load_config(filename='database.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)

    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return config

def connect_to_db():
    config = load_config(db_ini_path)
    try:
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)

if __name__ == '__main__':
    filename = db_ini_path
    config = load_config(filename)
    print(config)