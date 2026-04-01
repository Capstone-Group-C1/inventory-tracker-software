import pytest
import sqlite3
import os
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aim_central.logic import DatabaseOperations


@pytest.fixture
def test_db(tmp_path):
    """
    Fixture that creates a fresh database using database_init().
    """
    db_path = str(tmp_path / "test_inventory.db")
    with patch.object(DatabaseOperations, 'DB_PATH', db_path):
        DatabaseOperations.database_init()
    yield db_path


@pytest.fixture
def sample_data(test_db):
    """
    Fixture that seeds the database with 3 items across 3 containers.

    Schema:
      items:      item_id, item_name, item_weight, needed_stock, current_stock
      containers: container_id
      item_list:  container_id, item_id

    Container 1 → Resistor  (item_id=1), needed=100, current=50
    Container 2 → Capacitor (item_id=2), needed=50,  current=60
    Container 3 → LED       (item_id=3), needed=100, current=0
    """
    with patch.object(DatabaseOperations, 'DB_PATH', test_db):
        with sqlite3.connect(test_db) as conn:
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("Resistor", 0.001, 100, 50)
            )
            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("Capacitor", 0.002, 50, 60)
            )
            cur.execute(
                "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                ("LED", 0.003, 100, 0)
            )

            cur.execute("INSERT INTO containers (container_id) VALUES (?)", (1,))
            cur.execute("INSERT INTO containers (container_id) VALUES (?)", (2,))
            cur.execute("INSERT INTO containers (container_id) VALUES (?)", (3,))

            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 1))
            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (2, 2))
            cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (3, 3))

            conn.commit()

    yield test_db


# ============================================================================
# Tests for database_init()
# ============================================================================

class TestDatabaseInit:

    def test_database_init_creates_tables(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()

                for table in ("items", "containers", "item_list", "sensor_events"):
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    )
                    assert cursor.fetchone() is not None, f"{table} table was not created"

    def test_items_table_schema(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(items)")
                columns = {row[1] for row in cursor.fetchall()}
                assert {"item_id", "item_name", "item_weight", "needed_stock", "current_stock"}.issubset(columns)

    def test_containers_table_schema(self, test_db):
        """containers table should only have container_id — stock moved to items."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(containers)")
                columns = {row[1] for row in cursor.fetchall()}
                assert "container_id" in columns
                assert "item_id" not in columns, "item_id should not be on containers — use item_list"
                assert "needed_stock" not in columns, "needed_stock moved to items"
                assert "current_stock" not in columns, "current_stock moved to items"

    def test_item_list_table_schema(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(item_list)")
                columns = {row[1] for row in cursor.fetchall()}
                assert {"container_id", "item_id"}.issubset(columns)


# ============================================================================
# Tests for get_item_ids()
# ============================================================================

class TestGetItemIds:

    def test_returns_correct_ids_for_single_item_container(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_item_ids(1) == [1]
            assert DatabaseOperations.get_item_ids(2) == [2]

    def test_returns_multiple_ids_for_multi_item_container(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", ("Adult Gloves", 50.0))
                cur.execute("INSERT INTO items (item_name, item_weight) VALUES (?, ?)", ("Child Gloves", 30.0))
                cur.execute("INSERT INTO containers (container_id) VALUES (?)", (1,))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 1))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 2))
                conn.commit()

            result = DatabaseOperations.get_item_ids(1)
            assert sorted(result) == [1, 2]

    def test_returns_empty_list_for_nonexistent_container(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_item_ids(999) == []


# ============================================================================
# Tests for get_item_weight()
# ============================================================================

class TestGetItemWeight:

    def test_returns_correct_weight(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_item_weight(1) == 0.001
            assert DatabaseOperations.get_item_weight(2) == 0.002

    def test_returns_none_for_nonexistent_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_item_weight(999) is None


# ============================================================================
# Tests for find_container()
# ============================================================================

class TestFindContainer:

    def test_returns_items_list(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.find_container(1)
            assert result is not None
            assert "items" in result
            assert len(result["items"]) == 1
            assert result["items"][0]["item_name"] == "Resistor"

    def test_returns_correct_stock_fields_on_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            result = DatabaseOperations.find_container(1)
            item = result["items"][0]
            assert item["needed_stock"] == 100
            assert item["current_stock"] == 50

    def test_returns_none_for_nonexistent_container(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.find_container(999) is None

    def test_returns_multiple_items_for_multi_item_container(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("Adult Gloves", 50.0, 10, 10)
                )
                cur.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("Child Gloves", 30.0, 5, 5)
                )
                cur.execute("INSERT INTO containers (container_id) VALUES (?)", (1,))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 1))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 2))
                conn.commit()

            result = DatabaseOperations.find_container(1)
            assert len(result["items"]) == 2
            names = {item["item_name"] for item in result["items"]}
            assert names == {"Adult Gloves", "Child Gloves"}


# ============================================================================
# Tests for find_item()
# ============================================================================

class TestFindItem:

    def test_returns_correct_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            item = DatabaseOperations.find_item(1)
            assert item is not None
            assert item["item_name"] == "Resistor"
            assert item["item_weight"] == 0.001
            assert item["needed_stock"] == 100
            assert item["current_stock"] == 50

    def test_returns_none_for_nonexistent(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.find_item(999) is None


# ============================================================================
# Tests for get_stock_level()
# ============================================================================

class TestGetStockLevel:

    def test_red_when_stock_is_zero(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # item_id=3 (LED) has current_stock=0
            assert DatabaseOperations.get_stock_level(3) == "Red"

    def test_yellow_when_stock_at_50_percent(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # item_id=1 (Resistor): needed=100, current=50 → exactly 50%
            assert DatabaseOperations.get_stock_level(1) == "Yellow"

    def test_green_when_stock_above_50_percent(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            # item_id=2 (Capacitor): needed=50, current=60 → 120%
            assert DatabaseOperations.get_stock_level(2) == "Green"

    def test_green_for_nonexistent_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_stock_level(999) == "Green"


# ============================================================================
# Tests for get_stock()
# ============================================================================

class TestGetStock:

    def test_returns_correct_stock(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_stock(1) == 50
            assert DatabaseOperations.get_stock(2) == 60
            assert DatabaseOperations.get_stock(3) == 0

    def test_returns_minus_one_for_nonexistent(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_stock(999) == -1


# ============================================================================
# Tests for set_stock()
# ============================================================================

class TestSetStock:

    def test_sets_to_absolute_value(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.set_stock(1, 75) is True
            assert DatabaseOperations.get_stock(1) == 75

    def test_set_to_zero(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.set_stock(1, 0) is True
            assert DatabaseOperations.get_stock(1) == 0

    def test_rejects_negative(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.set_stock(1, -5) is False
            assert DatabaseOperations.get_stock(1) == 50  # unchanged

    def test_returns_false_for_nonexistent_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.set_stock(999, 10) is False


# ============================================================================
# Tests for change_stock()
# ============================================================================

class TestChangeStock:

    def test_increment(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.change_stock(1, 20) is True
            assert DatabaseOperations.get_stock(1) == 70

    def test_decrement(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.change_stock(1, -10) is True
            assert DatabaseOperations.get_stock(1) == 40

    def test_prevents_below_zero(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.change_stock(1, -100) is False
            assert DatabaseOperations.get_stock(1) == 50  # unchanged

    def test_returns_false_for_nonexistent_item(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.change_stock(999, 10) is False

    def test_multiple_updates_accumulate(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            DatabaseOperations.change_stock(1, 10)
            DatabaseOperations.change_stock(1, 15)
            DatabaseOperations.change_stock(1, -5)
            assert DatabaseOperations.get_stock(1) == 70  # 50 + 10 + 15 - 5


# ============================================================================
# Tests for get_num_containers() and get_all_container_ids()
# ============================================================================

class TestContainerQueries:

    def test_get_num_containers(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert DatabaseOperations.get_num_containers() == 3

    def test_get_num_containers_empty(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            assert DatabaseOperations.get_num_containers() == 0

    def test_get_all_container_ids(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            assert sorted(DatabaseOperations.get_all_container_ids()) == [1, 2, 3]

    def test_get_all_container_ids_empty(self, test_db):
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            assert DatabaseOperations.get_all_container_ids() == []


# ============================================================================
# Tests for sensor events
# ============================================================================

class TestSensorEvents:

    def test_record_sensor_event(self, sample_data):
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            ok = DatabaseOperations.record_sensor_event(
                container_id=1,
                raw_weight_g=4.0,
                net_weight_g=3.8,
                computed_stock=4,
                sensor_status="ok",
                decision="accepted",
                note="unit test",
            )
            assert ok is True

            with sqlite3.connect(sample_data) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT decision, computed_stock FROM sensor_events WHERE container_id = ?", (1,)
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == "accepted"
                assert row[1] == 4


# ============================================================================
# Integration tests
# ============================================================================

class TestDatabaseIntegration:

    def test_full_item_workflow(self, sample_data):
        """Find container, check stock level, change stock, verify new level."""
        with patch.object(DatabaseOperations, 'DB_PATH', sample_data):
            container = DatabaseOperations.find_container(1)
            assert container is not None

            # item_id=1: needed=100, current=50 → Yellow
            assert DatabaseOperations.get_stock_level(1) == "Yellow"

            DatabaseOperations.change_stock(1, 10)
            assert DatabaseOperations.get_stock_level(1) == "Green"
            assert DatabaseOperations.get_stock(1) == 60

    def test_multi_item_container_independent_stock(self, test_db):
        """Two items in the same container track stock independently."""
        with patch.object(DatabaseOperations, 'DB_PATH', test_db):
            with sqlite3.connect(test_db) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("Adult Gloves", 50.0, 10, 10)
                )
                cur.execute(
                    "INSERT INTO items (item_name, item_weight, needed_stock, current_stock) VALUES (?, ?, ?, ?)",
                    ("Child Gloves", 30.0, 5, 5)
                )
                cur.execute("INSERT INTO containers (container_id) VALUES (?)", (1,))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 1))
                cur.execute("INSERT INTO item_list (container_id, item_id) VALUES (?, ?)", (1, 2))
                conn.commit()

            DatabaseOperations.change_stock(1, -1)  # remove one adult glove
            assert DatabaseOperations.get_stock(1) == 9
            assert DatabaseOperations.get_stock(2) == 5  # child gloves unchanged
