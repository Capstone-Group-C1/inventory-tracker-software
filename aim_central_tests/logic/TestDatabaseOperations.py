import pytest
import sqlite3
import os
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) # Add import path for aim_central

from aim_central.logic import DatabaseOperations


@pytest.fixture
def test_db(tmp_path):
    """
    Fixture to create a temporary test database.
    This allows us to test without affecting the actual database.
    """
    # Create a temporary database file
    db_path = str(tmp_path / "test_inventory.db")
    
    # Initialize the database with tables
    sql_statements = [
        """CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL UNIQUE,
            item_weight REAL NOT NULL DEFAULT 0.0
        );""",
        """CREATE TABLE IF NOT EXISTS containers (
            container_id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            needed_stock INTEGER NOT NULL DEFAULT 0,
            current_stock INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        );"""
    ]
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            for statement in sql_statements:
                cursor.execute(statement)
            conn.commit()
    except sqlite3.OperationalError as e:
        print("Failed to create test tables:", e)
    
    yield db_path


@pytest.fixture
def sample_data(test_db):
    """
    Fixture to populate the test database with sample data.
    """
    with patch.object(DatabaseOperations, 'DB_PATH', test_db):
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            
            # Insert sample items
            cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", 
                          ("Resistor", 0.001))
            cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", 
                          ("Capacitor", 0.002))
            cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", 
                          ("LED", 0.003))
            
            # Insert sample containers
            cursor.execute("INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                          (1, 1, 100, 50))  # Container 1: Resistor, needed 100, have 50
            cursor.execute("INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                          (2, 2, 50, 60))   # Container 2: Capacitor, needed 50, have 60
            cursor.execute("INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                          (3, 3, 100, 0))   # Container 3: LED, needed 100, have 0
            
            conn.commit()
        
        yield test_db


# ============================================================================
# Tests for database_init()
# ============================================================================

class TestDatabaseInit:
    """Test suite for database_init function."""
    
    def test_database_init_creates_tables(self, test_db):
        """Test that database_init creates the required tables."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            DatabaseOperations.database_init()
            
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                
                # Check if items table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
                assert cursor.fetchone() is not None, "items table was not created"
                
                # Check if containers table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='containers'")
                assert cursor.fetchone() is not None, "containers table was not created"
    
    def test_items_table_schema(self, test_db):
        """Test that items table has the correct schema."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            DatabaseOperations.database_init()
            
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(items)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
                
                assert "item_id" in columns
                assert "item_name" in columns
                assert "item_weight" in columns
    
    def test_containers_table_schema(self, test_db):
        """Test that containers table has the correct schema."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            DatabaseOperations.database_init()
            
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(containers)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
                
                assert "container_id" in columns
                assert "item_id" in columns
                assert "needed_stock" in columns
                assert "current_stock" in columns


# ============================================================================
# Tests for get_item_id()
# ============================================================================

class TestGetItemId:
    """Test suite for get_item_id function."""
    
    def test_get_item_id_returns_correct_id(self, sample_data):
        """Test that get_item_id returns the correct item ID for a container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            item_id = DatabaseOperations.get_item_id(1)
            assert item_id == 1
            
            item_id = DatabaseOperations.get_item_id(2)
            assert item_id == 2
    
    def test_get_item_id_returns_none_for_nonexistent_container(self, sample_data):
        """Test that get_item_id returns None for non-existent container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            item_id = DatabaseOperations.get_item_id(999)
            assert item_id is None


class TestGetItemWeight:
    """Test suite for get_item_weight function."""

    def test_get_item_weight_returns_value(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Resistor row in fixture has weight 0.001
            item_weight = DatabaseOperations.get_item_weight(1)
            assert item_weight == 0.001

    def test_get_item_weight_returns_none_for_nonexistent_container(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            item_weight = DatabaseOperations.get_item_weight(999)
            assert item_weight is None


# ============================================================================
# Tests for find_container()
# ============================================================================

class TestFindContainer:
    """Test suite for find_container function."""
    
    def test_find_container_returns_correct_data(self, sample_data):
        """Test that find_container returns correct container data."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            container = DatabaseOperations.find_container(1)
            
            assert container is not None
            assert container["container_id"] == 1
            assert container["item_name"] == "Resistor"
            assert container["needed_stock"] == 100
            assert container["current_stock"] == 50
    
    def test_find_container_returns_none_for_nonexistent(self, sample_data):
        """Test that find_container returns None for non-existent container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            container = DatabaseOperations.find_container(999)
            assert container is None
    
    def test_find_container_returns_dictionary(self, sample_data):
        """Test that find_container returns a dictionary."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            container = DatabaseOperations.find_container(1)
            assert isinstance(container, dict)


# ============================================================================
# Tests for get_stock_level()
# ============================================================================

class TestGetStockLevel:
    """Test suite for get_stock_level function."""
    
    def test_get_stock_level_red(self, sample_data):
        """Test that get_stock_level returns Red when stock is 0."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Container 3 has current_stock = 0
            stock_level = DatabaseOperations.get_stock_level(3)
            assert stock_level == "Red"
    
    def test_get_stock_level_yellow(self, sample_data):
        """Test that get_stock_level returns Yellow when stock <= 50% of needed."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Container 1: needed=100, current=50 (exactly 50%)
            stock_level = DatabaseOperations.get_stock_level(1)
            assert stock_level == "Yellow"
    
    def test_get_stock_level_green(self, sample_data):
        """Test that get_stock_level returns Green when stock > 50% of needed."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Container 2: needed=50, current=60 (120%)
            stock_level = DatabaseOperations.get_stock_level(2)
            assert stock_level == "Green"
    
    def test_get_stock_level_nonexistent_container(self, sample_data):
        """Test that get_stock_level returns Green for non-existent container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Non-existent container should return Green (default)
            stock_level = DatabaseOperations.get_stock_level(999)
            assert stock_level == "Green"


# ============================================================================
# Tests for get_stock()
# ============================================================================

class TestGetStock:
    """Test suite for get_stock function."""
    
    def test_get_stock_returns_correct_value(self, sample_data):
        """Test that get_stock returns the correct stock value."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            stock = DatabaseOperations.get_stock(1)
            assert stock == 50
            
            stock = DatabaseOperations.get_stock(2)
            assert stock == 60
            
            stock = DatabaseOperations.get_stock(3)
            assert stock == 0
    
    def test_get_stock_returns_negative_one_for_nonexistent(self, sample_data):
        """Test that get_stock returns -1 for non-existent container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            stock = DatabaseOperations.get_stock(999)
            assert stock == -1


# ============================================================================
# Tests for change_stock()
# ============================================================================

class TestChangeStock:
    """Test suite for change_stock function."""
    
    def test_change_stock_increase(self, sample_data):
        """Test that change_stock correctly increases stock."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.change_stock(1, 20)
            assert result is True
            
            updated_stock = DatabaseOperations.get_stock(1)
            assert updated_stock == 70
    
    def test_change_stock_decrease(self, sample_data):
        """Test that change_stock correctly decreases stock."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.change_stock(1, -10)
            assert result is True
            
            updated_stock = DatabaseOperations.get_stock(1)
            assert updated_stock == 40
    
    def test_change_stock_prevents_negative(self, sample_data):
        """Test that change_stock prevents stock from going below zero."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Try to decrease by more than current stock
            result = DatabaseOperations.change_stock(1, -100)
            assert result is False
            
            # Stock should remain unchanged
            updated_stock = DatabaseOperations.get_stock(1)
            assert updated_stock == 50
    
    def test_change_stock_nonexistent_container(self, sample_data):
        """Test that change_stock returns False for non-existent container."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.change_stock(999, 10)
            assert result is False
    
    def test_change_stock_multiple_updates(self, sample_data):
        """Test that multiple stock changes accumulate correctly."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            DatabaseOperations.change_stock(1, 10)
            DatabaseOperations.change_stock(1, 15)
            DatabaseOperations.change_stock(1, -5)
            
            updated_stock = DatabaseOperations.get_stock(1)
            assert updated_stock == 70  # 50 + 10 + 15 - 5


class TestWeightBasedUpdates:
    """Test suite for absolute stock updates from measured weight."""

    def test_set_stock_updates_absolute_value(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.set_stock(1, 77)
            assert result is True
            assert DatabaseOperations.get_stock(1) == 77

    def test_update_stock_from_weight(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # item_weight for container 1 is 0.001, so 0.05 g -> 50 units
            result = DatabaseOperations.update_stock_from_weight(1, 0.05)
            assert result is True
            assert DatabaseOperations.get_stock(1) == 50

    def test_update_stock_from_weight_rejects_negative_weight(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.update_stock_from_weight(1, -1)
            assert result is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestDatabaseIntegration:
    """Integration tests combining multiple database operations."""
    
    def test_full_container_workflow(self, sample_data):
        """Test a complete workflow: find container, check stock level, change stock."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # Find container
            container = DatabaseOperations.find_container(1)
            assert container is not None
            
            # Check initial stock level
            stock_level = DatabaseOperations.get_stock_level(1)
            assert stock_level == "Yellow"
            
            # Increase stock to above 50% threshold
            DatabaseOperations.change_stock(1, 10)
            
            # Check new stock level
            stock_level = DatabaseOperations.get_stock_level(1)
            assert stock_level == "Green"
            
            # Verify final stock
            final_stock = DatabaseOperations.get_stock(1)
            assert final_stock == 60
    
    def test_create_and_query_new_item_and_container(self, test_db):
        """Test creating and querying a new item and container."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            # Initialize database
            DatabaseOperations.database_init()
            
            # Add a new item
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", 
                              ("Switch", 0.005))
                cursor.execute("INSERT INTO containers (container_id, item_id, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                              (10, 1, 200, 100))
                conn.commit()
            
            # Verify we can find and query the new container
            container = DatabaseOperations.find_container(10)
            assert container is not None
            assert container["item_name"] == "Switch"
            assert container["needed_stock"] == 200
            
            stock = DatabaseOperations.get_stock(10)
            assert stock == 100
