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
    real_db_path = os.path.join(os.path.dirname(__file__), '../../', 'inventory.db')
    test_db_path = str(tmp_path / "inventory_test.db")

    if os.path.exists(real_db_path):
        print(f"Using copy of existing database: {real_db_path}")
        shutil.copy(real_db_path, test_db_path)
    else:
        print(f"Real database not found at {real_db_path}, creating fresh one for testing")
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            DatabaseOperations.database_init()

    yield test_db_path


@pytest.fixture
def seeded_db(tmp_path):
    """
    Fixture that provides a fresh database pre-seeded with test data.

    Schema:
      items:      item_id, item_name, item_weight, needed_stock, current_stock
      containers: container_id
      item_list:  container_id, item_id
    """
    test_db_path = str(tmp_path / "seeded_test.db")

    with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
        DatabaseOperations.database_init()

        with sqlite3.connect(test_db_path) as conn:
            cur = conn.cursor()

            # Insert items
            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("Adult Gloves", 50.0, 10, 10)
            )
            adult_glove_id = cur.lastrowid

            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("Child Gloves", 30.0, 5, 5)
            )
            child_glove_id = cur.lastrowid

            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("Saline Bag", 500.0, 4, 4)
            )
            saline_id = cur.lastrowid

            # Insert containers
            cur.execute("INSERT INTO containers (container_id) VALUES (?)", (1,))
            cur.execute("INSERT INTO containers (container_id) VALUES (?)", (2,))

            # Container 1 has both glove types, container 2 has saline bags
            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, adult_glove_id))
            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, child_glove_id))
            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (2, saline_id))

            conn.commit()

    yield test_db_path, {
        "adult_glove_id": adult_glove_id,
        "child_glove_id": child_glove_id,
        "saline_id": saline_id,
    }


# ============================================================================
# Tests for real database scenarios
# ============================================================================

class TestRealDatabase:
    """Integration tests using the actual database file."""

    def test_database_file_exists(self, real_db_copy):
        """Verify the test database file was created."""
        assert os.path.exists(real_db_copy), "Database file was not created"

    def test_database_has_correct_schema(self, real_db_copy):
        """Verify the database has the expected tables and columns."""
        with sqlite3.connect(real_db_copy) as conn:
            cursor = conn.cursor()

            # Check all expected tables exist
            for table in ("items", "containers", "item_list"):
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                )
                assert cursor.fetchone() is not None, f"{table} table does not exist"

            # Verify items columns include stock fields (moved from containers)
            cursor.execute("PRAGMA table_info(items)")
            items_columns = {row[1] for row in cursor.fetchall()}
            assert {"item_id", "item_name", "item_weight", "needed_stock", "current_stock"}.issubset(items_columns), \
                f"items table missing columns. Has: {items_columns}"

            # Verify containers is now just an ID
            cursor.execute("PRAGMA table_info(containers)")
            containers_columns = {row[1] for row in cursor.fetchall()}
            assert "container_id" in containers_columns, "containers table missing container_id"
            assert "item_id" not in containers_columns, \
                "containers table should not have item_id (moved to item_list)"

            # Verify item_list junction table
            cursor.execute("PRAGMA table_info(item_list)")
            item_list_columns = {row[1] for row in cursor.fetchall()}
            assert {"container_id", "item_id"}.issubset(item_list_columns), \
                f"item_list table missing columns. Has: {item_list_columns}"

    def test_can_insert_and_query_items(self, real_db_copy):
        """Test inserting items and querying them."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("TestComponent1", 50.0, 10, 10)
                )
                cursor.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("TestComponent2", 75.0, 5, 5)
                )
                conn.commit()

                cursor.execute("SELECT COUNT(*) FROM items")
                count = cursor.fetchone()[0]
                assert count >= 2, "Items were not inserted correctly"

    def test_can_insert_and_query_containers(self, real_db_copy):
        """Test inserting containers and linking items via item_list."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("TestItem", 40.0, 10, 10)
                )
                item_id = cursor.lastrowid

                cursor.execute("INSERT INTO containers (container_id) VALUES (?)", (999,))
                cursor.execute(
                    "INSERT INTO item_list (container_id, item_id) VALUES (?, ?)",
                    (999, item_id)
                )
                conn.commit()

                cursor.execute("SELECT container_id FROM containers WHERE container_id = 999")
                assert cursor.fetchone() is not None, "Container was not inserted"

                cursor.execute(
                    "SELECT item_id FROM item_list WHERE container_id = 999"
                )
                assert cursor.fetchone()[0] == item_id, "item_list entry was not inserted correctly"


# ============================================================================
# Tests for DatabaseOperations functions
# ============================================================================

class TestDatabaseOperations:
    """Tests for DatabaseOperations functions against the new schema."""

    def test_find_container_returns_items_list(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            result = DatabaseOperations.find_container(1)
            assert result is not None, "find_container returned None"
            assert "items" in result, "find_container should return dict with 'items' key"
            assert len(result["items"]) == 2, "Container 1 should have 2 items"
            item_names = {item["item_name"] for item in result["items"]}
            assert item_names == {"Adult Gloves", "Child Gloves"}

    def test_find_container_returns_none_for_missing(self, seeded_db):
        test_db_path, _ = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.find_container(9999) is None

    def test_find_item_returns_correct_item(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            item = DatabaseOperations.find_item(ids["saline_id"])
            assert item is not None
            assert item["item_name"] == "Saline Bag"
            assert item["item_weight"] == 500.0

    def test_get_item_ids_returns_list(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            item_ids = DatabaseOperations.get_item_ids(1)
            assert isinstance(item_ids, list)
            assert len(item_ids) == 2
            assert ids["adult_glove_id"] in item_ids
            assert ids["child_glove_id"] in item_ids

    def test_get_item_ids_returns_empty_list_for_missing(self, seeded_db):
        test_db_path, _ = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            result = DatabaseOperations.get_item_ids(9999)
            assert result == []

    def test_get_stock_returns_current_stock(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.get_stock(ids["adult_glove_id"]) == 10
            assert DatabaseOperations.get_stock(ids["saline_id"]) == 4

    def test_get_stock_returns_minus_one_for_missing(self, seeded_db):
        test_db_path, _ = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.get_stock(9999) == -1

    def test_set_stock(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.set_stock(ids["adult_glove_id"], 7) is True
            assert DatabaseOperations.get_stock(ids["adult_glove_id"]) == 7

    def test_set_stock_rejects_negative(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.set_stock(ids["adult_glove_id"], -1) is False

    def test_change_stock_increment(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.change_stock(ids["child_glove_id"], 3) is True
            assert DatabaseOperations.get_stock(ids["child_glove_id"]) == 8

    def test_change_stock_decrement(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.change_stock(ids["saline_id"], -2) is True
            assert DatabaseOperations.get_stock(ids["saline_id"]) == 2

    def test_change_stock_rejects_below_zero(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.change_stock(ids["saline_id"], -999) is False
            assert DatabaseOperations.get_stock(ids["saline_id"]) == 4

    def test_get_stock_level_red(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            DatabaseOperations.set_stock(ids["adult_glove_id"], 0)
            assert DatabaseOperations.get_stock_level(ids["adult_glove_id"]) == "Red"

    def test_get_stock_level_yellow(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            # needed_stock is 10, so yellow is <= 5
            DatabaseOperations.set_stock(ids["adult_glove_id"], 4)
            assert DatabaseOperations.get_stock_level(ids["adult_glove_id"]) == "Yellow"

    def test_get_stock_level_green(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.get_stock_level(ids["adult_glove_id"]) == "Green"

    def test_get_num_containers(self, seeded_db):
        test_db_path, _ = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.get_num_containers() == 2

    def test_get_all_container_ids(self, seeded_db):
        test_db_path, _ = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            ids = DatabaseOperations.get_all_container_ids()
            assert sorted(ids) == [1, 2]

    def test_get_item_weight(self, seeded_db):
        test_db_path, ids = seeded_db
        with patch.object(DatabaseOperations, 'DB_PATH', test_db_path):
            assert DatabaseOperations.get_item_weight(ids["adult_glove_id"]) == 50.0
            assert DatabaseOperations.get_item_weight(ids["child_glove_id"]) == 30.0
            assert DatabaseOperations.get_item_weight(9999) is None


# ============================================================================
# Tests for data integrity
# ============================================================================

class TestDatabaseIntegrity:
    """Tests to verify database constraints."""

    def test_item_name_uniqueness_constraint(self, real_db_copy):
        """Verify that item names must be unique."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                    ("UniqueItem", 50.0)
                )
                conn.commit()

                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute(
                        "INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                        ("UniqueItem", 60.0)
                    )
                    conn.commit()

    def test_item_list_foreign_key_constraint(self, real_db_copy):
        """Verify item_list rejects references to non-existent containers or items."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")

                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute(
                        "INSERT INTO item_list (container_id, item_id) VALUES (?, ?)",
                        (9999, 9999)
                    )
                    conn.commit()

    def test_item_list_composite_primary_key(self, real_db_copy):
        """Verify that duplicate (container_id, item_id) pairs are rejected."""
        with patch.object(DatabaseOperations, 'DB_PATH', real_db_copy):
            with sqlite3.connect(real_db_copy) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO items (item_name, item_weight) VALUES (?, ?)",
                    ("DupTestItem", 50.0)
                )
                item_id = cursor.lastrowid
                cursor.execute("INSERT INTO containers (container_id) VALUES (?)", (888,))
                cursor.execute(
                    "INSERT INTO item_list (container_id, item_id) VALUES (?, ?)",
                    (888, item_id)
                )
                conn.commit()

                with pytest.raises(sqlite3.IntegrityError):
                    cursor.execute(
                        "INSERT INTO item_list (container_id, item_id) VALUES (?, ?)",
                        (888, item_id)
                    )
                    conn.commit()
