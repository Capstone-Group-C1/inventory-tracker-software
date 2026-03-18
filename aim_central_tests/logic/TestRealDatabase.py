"""
Integration tests for the actual inventory.db database.

These tests verify that the DatabaseOperations module works correctly
with the real production database file, using a copy to avoid modifying
the actual data.
"""

import pytest
import sqlite3
import os
import shutil
from unittest.mock import patch
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aim_central.logic import DatabaseOperations


@pytest.fixture
def real_db_copy(tmp_path):
    """
    Fixture to create a copy of the real inventory.db for testing.
    
    If inventory.db exists, copy it to a temp location.
    If it doesn't exist, initialize a fresh one using database_init().
    
    This allows us to test against the actual database schema and data
    without risking modification of the real file.
    """
    # Determine the path to the real database
    real_db_path = os.path.join(os.path.dirname(__file__), '../../', 'inventory.db')
    test_db_path = str(tmp_path / "inventory_test.db")
    
    if os.path.exists(real_db_path):
        # If the real database exists, copy it
        print(f"Using copy of existing database: {real_db_path}")
        shutil.copy(real_db_path, test_db_path)
    else:
        # If it doesn't exist yet, initialize a fresh one
        print(f"Real database not found at {real_db_path}, creating fresh one for testing")
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            DatabaseOperations.database_init()
    
    yield test_db_path


# ============================================================================
# Tests for real database scenarios
# ============================================================================

class TestRealDatabase:
    """Integration tests using the actual database file."""
    
    def test_database_file_exists(self, real_db_copy):
        """Verify the test database file was created."""
        assert os.path.exists(real_db_copy), "Database file was not created"
    
    def test_database_has_correct_schema(self, real_db_copy):
        """Verify the database has the expected tables and schema."""
        with sqlite3.connect(real_db_copy) as conn:
            cursor = conn.cursor()
            
            # Check for items table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
            assert cursor.fetchone() is not None, "items table does not exist"
            
            # Check for containers table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='containers'")
            assert cursor.fetchone() is not None, "containers table does not exist"
            
            # Verify items columns
            cursor.execute("PRAGMA table_info(items)")
            items_columns = {row[1] for row in cursor.fetchall()}
            expected_items_columns = {"item_id", "item_name", "item_weight"}
            assert expected_items_columns.issubset(items_columns), \
                f"items table missing columns. Has: {items_columns}"
            
            # Verify containers columns
            cursor.execute("PRAGMA table_info(containers)")
            containers_columns = {row[1] for row in cursor.fetchall()}
            expected_containers_columns = {"container_id", "item_id", "needed_stock", "current_stock"}
            assert expected_containers_columns.issubset(containers_columns), \
                f"containers table missing columns. Has: {containers_columns}"
    
    def test_can_insert_and_query_items(self, real_db_copy):
        """Test inserting items and querying them from the real database."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # Insert test items
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("TestComponent1", 0.5))
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("TestComponent2", 0.75))
                conn.commit()
                
                # Query them back
                cursor.execute("SELECT COUNT(*) FROM items")
                count = cursor.fetchone()[0]
                assert count >= 2, "Items were not inserted correctly"
    
    def test_can_insert_and_query_containers(self, real_db_copy):
        """Test inserting containers and querying them."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # First insert an item (container needs a valid item_id)
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("TestItem", 0.4))
                conn.commit()
                
                # Get the item_id
                cursor.execute("SELECT item_id FROM items WHERE item_name = 'TestItem'")
                item_id = cursor.fetchone()[0]
                
                # Insert a container for this item
                cursor.execute(
                    "INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    (999, item_id, 100, 50)
                )
                conn.commit()
                
                # Query the container
                cursor.execute("SELECT * FROM containers WHERE container_id = 999")
                result = cursor.fetchone()
                assert result is not None, "Container was not inserted"
                assert result[2] == 100, "needed_stock was not set correctly"
                assert result[3] == 50, "current_stock was not set correctly"
    
    def test_database_operations_find_container_works(self, real_db_copy):
        """Test that find_container() works with the real database schema."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # Insert test data
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("RealTestItem", 0.3))
                conn.commit()
                
                cursor.execute("SELECT item_id FROM items WHERE item_name = 'RealTestItem'")
                item_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    (777, item_id, 150, 75)
                )
                conn.commit()
            
            # Now test the actual DatabaseOperations function
            container = DatabaseOperations.find_container(777)
            assert container is not None, "find_container returned None"
            assert container["item_name"] == "RealTestItem"
            assert container["needed_stock"] == 150
            assert container["current_stock"] == 75
    
    def test_database_operations_get_stock_works(self, real_db_copy):
        """Test that get_stock() works with the real database."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # Insert test data
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("StockTestItem", 0.2))
                conn.commit()
                
                cursor.execute("SELECT item_id FROM items WHERE item_name = 'StockTestItem'")
                item_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    (666, item_id, 200, 125)
                )
                conn.commit()
            
            # Test get_stock
            stock = DatabaseOperations.get_stock(666)
            assert stock == 125, f"Expected stock 125, got {stock}"
    
    def test_database_operations_change_stock_works(self, real_db_copy):
        """Test that change_stock() works with the real database."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # Insert test data
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("ChangeStockItem", 0.15))
                conn.commit()
                
                cursor.execute("SELECT item_id FROM items WHERE item_name = 'ChangeStockItem'")
                item_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    (555, item_id, 250, 100)
                )
                conn.commit()
            
            # Test change_stock
            initial_stock = DatabaseOperations.get_stock(555)
            assert initial_stock == 100
            
            result = DatabaseOperations.change_stock(555, 50)
            assert result is True, "change_stock returned False"
            
            updated_stock = DatabaseOperations.get_stock(555)
            assert updated_stock == 150, f"Expected stock 150, got {updated_stock}"


# ============================================================================
# Tests for data integrity
# ============================================================================

class TestDatabaseIntegrity:
    """Tests to verify database integrity and constraints."""
    
    def test_item_name_uniqueness_constraint(self, real_db_copy):
        """Verify that item names must be unique."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                
                # Insert first item
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                              ("UniqueItem", 0.5))
                conn.commit()
                
                # Try to insert duplicate - should fail
                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                                  ("UniqueItem", 0.6))
                    conn.commit()
    
    def test_foreign_key_constraint(self, real_db_copy):
        """Verify that containers must reference valid items."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                # Enable foreign key constraints (SQLite doesn't enforce by default)
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Try to insert container with non-existent item_id
                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute(
                        "INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                        (444, 99999, 100, 50)
                    )
                    conn.commit()
