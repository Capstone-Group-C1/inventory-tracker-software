import sqlite3
import os

# Path for the database file to be created in the same directory
DB_PATH = os.path.join(os.path.dirname(__file__), 'inventory.db')

def database_init():
    """Initializes the database with tables."""
    sql_statements = [
        # AUTOINCREMENT to generate unique item IDs
        # UNIQUE makes sure that the names are unique
        # DEFAULT 0.0 sets the default weight to 0.0 when not provided
        """CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL UNIQUE,
            item_weight REAL NOT NULL DEFAULT 0.0
        );""",

        # Manually set container ID
        # needed_stock is defaulted to 0 unless specified
        # current_stock is defaulted to 0 unless specified
        # FOREIGN KEY constraint so that the item_id in containers must exist in items
        """CREATE TABLE IF NOT EXISTS containers (
            container_id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            needed_stock INTEGER NOT NULL DEFAULT 0,
            current_stock INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        );"""
    ]

    # create a database connection
    try:
        with sqlite3.connect(DB_PATH) as conn:
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


def get_item_id(container_id):
    """
    Get the item ID for a container
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('SELECT item_id FROM containers WHERE container_id =?', (container_id,))
            row = cur.fetchone()
            if row:
                return row[0] # row ID not the touple
            return None
    except sqlite3.OperationalError as e:
        print(e)

def find_container(container_id):
    """
    Find a container in the database by its ID.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # access columns by name
            cur = conn.cursor()
            # JOIN connects two tables based on a common column to get item name from items table and container details
            cur.execute(
                """SELECT c.container_id, i.item_name, c.needed_stock, c.current_stock 
                FROM containers c
                JOIN items i ON c.item_id = i.item_id
                WHERE c.container_id = ?""", (container_id,))
            row = cur.fetchone() # returns a single row or None
            if row:
                return dict(row) # convert to dictionary
            return None
    except sqlite3.OperationalError as e:
        print(e)
        return None

def get_stock_level(container_id):
    """
    Returns Red, Yellow, or Green based on stock levels.
    """
    container = find_container(container_id)
    if container:
        if container["current_stock"] == 0:
            return "Red"
        elif container["current_stock"] <= container["needed_stock"] * 0.5:
            return "Yellow"
    return "Green"

def get_stock(container_id):
    """
    Returns the current stock of the container or -1 if we can't find the container.
    """
    container = find_container(container_id)
    if container:
        return container["current_stock"]
    return -1

def change_stock(container_id, change_amount):
    """
    Adjusts stock of a container by change_amount.
    """
    container = find_container(container_id)
    if container is None:
        print(f"Error: Container with ID {container_id} not found.")
        return False
    
    new_stock = container["current_stock"] + change_amount
    if new_stock < 0:
        print("Error: Attempting to set stock below zero.")
        return False
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # Update the current_stock for the specified container_id
            cur.execute('UPDATE containers SET current_stock = ? WHERE container_id = ?', (new_stock, container_id))
            conn.commit()
            print(f"Stock updated successfully for container ID {container_id}. New stock: {new_stock}")
            return True
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False

# Main Function to initialize database
if __name__ == "__main__":
    database_init()