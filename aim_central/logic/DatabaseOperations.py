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
        );""",

        # Per-container calibration parameters for converting raw sensor weight.
        """CREATE TABLE IF NOT EXISTS container_calibration (
            container_id INTEGER PRIMARY KEY,
            empty_bin_weight_g REAL NOT NULL DEFAULT 0.0,
            scale_factor REAL NOT NULL DEFAULT 1.0,
            min_detectable_weight_g REAL NOT NULL DEFAULT 0.0,
            rounding_mode TEXT NOT NULL DEFAULT 'round',
            FOREIGN KEY (container_id) REFERENCES containers(container_id)
        );""",

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


def get_item_weight(container_id):
    """
    Get the configured item weight for a container.

    Returns None when the container is not found.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT i.item_weight
                FROM containers c
                JOIN items i ON c.item_id = i.item_id
                WHERE c.container_id = ?""",
                (container_id,),
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
    Find a container in the database by its ID.

    @throws sqlite3.OperationalError if the database operation fails.
    @return a dictionary with container details or None if not found.
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


def set_stock(container_id, new_stock):
    """
    Sets the current_stock of a container to an absolute value.
    """
    if new_stock < 0:
        print("Error: Attempting to set stock below zero.")
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE containers SET current_stock = ? WHERE container_id = ?",
                (new_stock, container_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False


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

            query = """SELECT c.container_id, i.item_name, c.needed_stock, c.current_stock
                    FROM containers c
                    JOIN items i ON c.item_id = i.item_id"""

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
    The CSV file should have columns: container_id, item_name, needed_stock, current_stock
    """
    try:
        df = pd.read_csv(csv_file_path)
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            for _, row in df.iterrows():
                # Check if item exists, if not insert it
                cur.execute('SELECT item_id FROM items WHERE item_name = ?', (row['item_name'],))
                item = cur.fetchone()
                if item:
                    item_id = item[0]
                else:
                    cur.execute('INSERT INTO items (item_name) VALUES (?)', (row['item_name'],))
                    item_id = cur.lastrowid

                # Update or insert container
                cur.execute('SELECT container_id FROM containers WHERE container_id = ?', (row['container_id'],))
                container = cur.fetchone()
                if container:
                    cur.execute('''UPDATE containers
                                   SET item_id = ?, needed_stock = ?, current_stock = ?
                                   WHERE container_id = ?''',
                                (item_id, row['needed_stock'], row['current_stock'], row['container_id']))
                else:
                    cur.execute('''INSERT INTO containers (container_id, item_id, needed_stock, current_stock)
                                   VALUES (?, ?, ?, ?)''',
                                (row['container_id'], item_id, row['needed_stock'], row['current_stock']))
            conn.commit()
        return "Import successful!"
    except Exception as e:
        return "Unable to import data."


def get_container_calibration(container_id):
    """
    Get per-container calibration values.

    Returns defaults when no calibration row exists.
    """
    defaults = {
        "empty_bin_weight_g": 0.0,
        "scale_factor": 1.0,
        "min_detectable_weight_g": 0.0,
        "rounding_mode": "round",
    }

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """SELECT empty_bin_weight_g, scale_factor, min_detectable_weight_g, rounding_mode
                FROM container_calibration
                WHERE container_id = ?""",
                (container_id,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return defaults
    except sqlite3.OperationalError:
        # Keep compatibility with databases created before calibration table existed.
        return defaults


def upsert_container_calibration(
    container_id,
    empty_bin_weight_g=0.0,
    scale_factor=1.0,
    min_detectable_weight_g=0.0,
    rounding_mode="round",
):
    """
    Insert or update per-container calibration values.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO container_calibration (
                    container_id,
                    empty_bin_weight_g,
                    scale_factor,
                    min_detectable_weight_g,
                    rounding_mode
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(container_id) DO UPDATE SET
                    empty_bin_weight_g = excluded.empty_bin_weight_g,
                    scale_factor = excluded.scale_factor,
                    min_detectable_weight_g = excluded.min_detectable_weight_g,
                    rounding_mode = excluded.rounding_mode""",
                (
                    container_id,
                    float(empty_bin_weight_g),
                    float(scale_factor),
                    float(min_detectable_weight_g),
                    rounding_mode,
                ),
            )
            conn.commit()
            return True
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False


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


def update_stock_from_weight(container_id, measured_weight_g):
    """
    Converts measured weight (grams) into item count, then updates stock.

    Assumption: item_weight stored in DB is grams per unit.
    """
    if measured_weight_g < 0:
        print("Error: measured_weight_g cannot be negative.")
        return False

    item_weight_g = get_item_weight(container_id)
    if item_weight_g is None:
        print(f"Error: No item configured for container ID {container_id}.")
        return False

    if item_weight_g <= 0:
        print(f"Error: Invalid item weight ({item_weight_g}) for container ID {container_id}.")
        return False

    calibration = get_container_calibration(container_id)
    empty_bin_weight_g = float(calibration["empty_bin_weight_g"])
    scale_factor = float(calibration["scale_factor"])
    min_detectable_weight_g = float(calibration["min_detectable_weight_g"])
    rounding_mode = calibration["rounding_mode"]

    if scale_factor <= 0:
        print(f"Error: Invalid scale_factor ({scale_factor}) for container ID {container_id}.")
        return False

    net_weight_g = max(0.0, (measured_weight_g - empty_bin_weight_g) * scale_factor)
    if net_weight_g < min_detectable_weight_g:
        net_weight_g = 0.0

    ratio = net_weight_g / item_weight_g
    if rounding_mode == "floor":
        calculated_stock = int(ratio)
    elif rounding_mode == "ceil":
        calculated_stock = int(ratio) if ratio == int(ratio) else int(ratio) + 1
    else:
        calculated_stock = int(round(ratio))

    return set_stock(container_id, calculated_stock)

# Main Function to initialize database
# if __name__ == "__main__":
#     database_init()
