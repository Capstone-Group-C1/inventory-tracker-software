import sqlite3

sql_statements = [ 
    """CREATE TABLE IF NOT EXISTS containers (
            container_id INTEGER PRIMARY KEY, 
            item_id INTEGER, 
            needed_stock INTEGER, 
            current_stock INTEGER
        );""",

    """CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY, 
            item_name text NOT NULL, 
            item_weight REAL NOT NULL
        );"""
]

# create a database connection
try:
    with sqlite3.connect('inventory.db') as conn:
        # create a cursor
        cursor = conn.cursor()

        # execute statements
        for statement in sql_statements:
            cursor.execute(statement)

        # commit the changes
        conn.commit()

        print("Tables created successfully.")
except sqlite3.OperationalError as e:
    print("Failed to create tables:", e)
