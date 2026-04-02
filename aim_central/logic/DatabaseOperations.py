import sqlite3
import os
import smtplib
import ssl
import pandas as pd
from email.message import EmailMessage
from config.config import AIMConfig

# Path for the database file to be created in the same directory
DB_PATH = os.path.join(os.path.dirname(__file__), AIMConfig.DB_PATH)

def database_init():
    """Initializes the database with tables."""
    sql_statements = [
        # AUTOINCREMENT to generate unique item IDs
        # UNIQUE makes sure that the names are unique
        # DEFAULT 0.0 sets the default weight to 0.0 when not provided
        """CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL UNIQUE,
            item_weight REAL NOT NULL DEFAULT 0.0,
            needed_stock INTEGER NOT NULL DEFAULT 0,
            current_stock INTEGER NOT NULL DEFAULT 0
        );""",

        # Manually set container ID, with a foreign key reference to items table for item_id
        '''CREATE TABLE IF NOT EXISTS containers (
            container_id INTEGER PRIMARY KEY,
            container_weight REAL NOT NULL DEFAULT 0.0
        );
        ''',

        # FOREIGN KEY constraint so that the container_id in item_list must exist in containers and item_id must exist in items
        '''CREATE TABLE IF NOT EXISTS item_list (
            container_id TEXT NOT NULL REFERENCES containers(container_id),
            item_id INTEGER NOT NULL REFERENCES items(item_id),
            PRIMARY KEY (container_id, item_id)
        );''',

        # Time-series history for troubleshooting and analytics.
        """CREATE TABLE IF NOT EXISTS sensor_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id INTEGER NOT NULL,
            raw_weight_g REAL NOT NULL,
            net_weight_g REAL,
            computed_stock INTEGER,
            sensor_status TEXT NOT NULL,
            decision TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (container_id) REFERENCES containers(container_id)
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


def get_item_ids(container_id):
    """
    Get the item ID(s) for a container
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('SELECT item_id FROM item_list WHERE container_id = ?', (container_id,))
            row = cur.fetchall()
            return [item_id for item_id, in row]  # Return a list of item IDs (empty list if none)
    except sqlite3.OperationalError as e:
        print(e)
        return []


def get_item_weight(item_id):
    """
    Get the configured item weight for an item.

    Returns None when the container is not found.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT i.item_weight
                FROM items i
                WHERE i.item_id = ?""",
                (item_id,),
            )
            row = cur.fetchone()
            if row:
                return float(row[0])
            return None
    except sqlite3.OperationalError as e:
        print(e)
        return None

def find_container(container_id):
    """
    Find a container in the database by its ID. Returns a dictionary with item and container details or None if not found.

    @throws sqlite3.OperationalError if the database operation fails.
    @return a dictionary with container details or None if not found.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # access columns by name
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    c.container_id,
                    i.item_id,
                    i.item_name,
                    i.needed_stock,
                    i.current_stock
                FROM containers c
                JOIN item_list il ON c.container_id = il.container_id
                JOIN items i      ON il.item_id = i.item_id
                WHERE c.container_id = ?;
            """, (container_id,))

            rows = cur.fetchall()

            result = {
                "container_id": container_id,
                "items": [
                    {
                        "item_id":       r["item_id"],
                        "item_name":     r["item_name"],
                        "needed_stock":  r["needed_stock"],
                        "current_stock": r["current_stock"],
                    }
                    for r in rows
                ]
            }

            print("Database query result for container {}: {}".format(container_id, result))
            # adding stock level to each item in the container details for use in the UI
            for item in result["items"]:
                item["stock_level"] = get_stock_level(item["item_id"])

            if result["items"]:  # Only return if we found at least one item for the container
                return result
            return None
    except sqlite3.OperationalError as e:
        print(e)
        return None
    
def find_item(item_id):
    """
    Find an item in the database by its ID. Returns a dictionary with item details or None if not found.

    @throws sqlite3.OperationalError if the database operation fails.
    @return a dictionary with item details or None if not found.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # access columns by name
            cur = conn.cursor()
            cur.execute("""
                SELECT item_id, item_name, item_weight, needed_stock, current_stock
                FROM items
                WHERE item_id = ?
            """, (item_id,))

            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except sqlite3.OperationalError as e:
        print(e)
        return None

def get_all_container_ids():
    """
    Returns a list of all container IDs in the database.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT container_id FROM containers")
            return [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError as e:
        print(e)
        return []


def get_num_containers():
    """
    Get the total number of containers in the database.

    @throws sqlite3.OperationalError if the database operation fails.
    @return the total count of containers as an integer.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM containers")
            count = cur.fetchone()[0] # fetchone returns a tuple like (count,)
            return count
    except sqlite3.OperationalError as e:
        print(e)
        return 0

def get_stock(item_id):
    """
    Returns the current stock of the item or -1 if we can't find the item.
    """
    item = find_item(item_id)
    if item:
        return item["current_stock"]
    return -1


def get_stock_level(item_id):
    """
    Returns 0 if out of stock, 1 if low stock, and 2 if in stock.
    Changed to allow iteration over multiple items in a container, and use the lowest stock level to drive the button colour.
    """
    item = find_item(item_id)
    if item:
        if item["current_stock"] == 0:
            return 0
        elif item["current_stock"] <= item["needed_stock"] * 0.5:
            return 1
    return 2


def get_container_stock_level(container_id):
    """
    Returns the lowest stock level for all items in a container.
    """
    item_ids = get_item_ids(container_id)
    print("Item IDs for container {}: {}".format(container_id, item_ids))
    lowest_stock_level = 2
    for item in item_ids:
        stock_level = get_stock_level(item)
        if stock_level is not None and stock_level < lowest_stock_level:
            lowest_stock_level = stock_level
    return lowest_stock_level


def set_stock(item_id, new_stock):
    """
    Sets the current_stock of an item to an absolute value.
    """
    if new_stock < 0:
        print("Error: Attempting to set stock below zero.")
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE items SET current_stock = ? WHERE item_id = ?",
                (new_stock, item_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False


def change_stock(item_id, change_amount):
    """
    Adjusts stock of an item by change_amount (positive or negative).
    """
    item = find_item(item_id)
    if item is None:
        print(f"Error: Item with ID {item_id} not found.")
        return False

    new_stock = item["current_stock"] + change_amount
    if new_stock < 0:
        print("Error: Attempting to set stock below zero.")
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('UPDATE items SET current_stock = ? WHERE item_id = ?', (new_stock, item_id))
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False


def export_to_email(receiver_email):
    email_sender = 'AmbulanceInventoryManagement@gmail.com'
    email_password = os.getenv('AIM_EMAIL_PASSWORD', '')

    subject = 'Ambulance Inventory File Attached'
    body = 'Please find the attached database file containing the ambulance inventory details.'

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = receiver_email
    em['Subject'] = subject
    em.set_content(body)

    df = pd.DataFrame() # create empty dataframe to hold query results

    try:
        with sqlite3.connect(DB_PATH) as conn:

            query = """
                SELECT i.item_id, il.container_id, i.item_name, i.needed_stock, i.current_stock
                FROM items i
                JOIN item_list il ON i.item_id = il.item_id
                ORDER BY il.container_id, i.item_id
            """

            df = pd.read_sql_query(query, conn)
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False

    df.to_csv('inventory_export.csv', index=False) # export to CSV

    # Attach the database file
    with open('inventory_export.csv', 'rb') as csv_file:
        em.add_attachment(csv_file.read(),
                        maintype='application',
                        subtype='octet-stream', # generic type for a data file
                        filename=os.path.basename('inventory_export.csv'))

    # add SSL (layer of security)
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.send_message(em)
        return "Email sent successfully!"
    except smtplib.SMTPException as e:
        return (f"Error: Unable to send email. {e}")


def import_from_csv(csv_file_path):
    """
    Imports inventory data from a CSV file and updates the database.
    The CSV file should have columns: item_id, container_id, item_name, needed_stock, current_stock
    """
    try:
        df = pd.read_csv(csv_file_path)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            # Clear existing data before reimporting
            cur.execute("DELETE FROM item_list")
            cur.execute("DELETE FROM items")
            cur.execute("DELETE FROM containers")

            for _, row in df.iterrows():
                # Insert or ignore the container
                cur.execute("""
                    INSERT OR IGNORE INTO containers (container_id)
                    VALUES (?)
                """, (row['container_id'],))

                # Insert or update the item (upsert)
                cur.execute("""
                    INSERT INTO items (item_name, needed_stock, current_stock)
                    VALUES (?, ?, ?)
                    ON CONFLICT(item_name) DO UPDATE SET
                        needed_stock = excluded.needed_stock,
                        current_stock = excluded.current_stock
                """, (row['item_name'], row['needed_stock'], row['current_stock']))

                # Get the item_id (whether it was just inserted or already existed)
                cur.execute("SELECT item_id FROM items WHERE item_name = ?", (row['item_name'],))
                item_id = cur.fetchone()[0]

                # Link item to container in item_list
                cur.execute("""
                    INSERT OR IGNORE INTO item_list (container_id, item_id)
                    VALUES (?, ?)
                """, (row['container_id'], item_id))
            conn.commit()
        return "Import successful!"
    except Exception as e:
        return "Unable to import data."


def record_sensor_event(
    container_id,
    raw_weight_g,
    sensor_status,
    decision,
    net_weight_g=None,
    computed_stock=None,
    note=None,
):
    """
    Record a sensor processing event for observability.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO sensor_events (
                    container_id,
                    raw_weight_g,
                    net_weight_g,
                    computed_stock,
                    sensor_status,
                    decision,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    container_id,
                    float(raw_weight_g),
                    None if net_weight_g is None else float(net_weight_g),
                    computed_stock,
                    sensor_status,
                    decision,
                    note,
                ),
            )
            conn.commit()
            return True
    except sqlite3.OperationalError:
        # Keep compatibility with databases created before sensor_events table existed.
        return False


# Main Function to initialize database
# if __name__ == "__main__":
#     database_init()
