import sqlite3

def get_item_id(container_id):
    try:
        with sqlite3.connect('inventory.db') as conn:
            cur = conn.cursor()
            cur.execute('SELECT item_id FROM containers WHERE container_id =?', (container_id,))
            row = cur.fetchone()
            if row:
                print(row)
                return row
    except sqlite3.OperationalError as e:
        print(e)