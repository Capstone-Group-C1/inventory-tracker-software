import sqlite3
import os
import smtplib
import ssl
from email.message import EmailMessage
from aim_central.config.config import AIMConfig

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
    # --- 2. Email Configuration ---
    # Set up your email credentials and recipient details
    # It is highly recommended to use an App Password for Gmail/similar services
    # You can generate one in your Google account settings:
    # https://support.google.com
    email_sender = 'your_email@gmail.com'
    email_password = 'your_app_password' # Use an App Password here, not your main password

    subject = 'Ambulance Inventory File Attached'
    body = 'Please find the attached database file containing the ambulance inventory details.'

    # --- 3. Create the Email Message and Attach the File ---
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = receiver_email
    em['Subject'] = subject
    em.set_content(body)

    # Attach the database file
    with open(DB_PATH, 'rb') as db_file:
        em.add_attachment(db_file.read(),
                        maintype='application',
                        subtype='octet-stream', # Generic type for a data file
                        filename=os.path.basename(DB_PATH))

    # --- 4. Send the Email via SMTP ---
    # Add SSL (layer of security)
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.send_message(em)
        print("Email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"Error: Unable to send email. {e}")



# Main Function to initialize database
# if __name__ == "__main__":
#     database_init()