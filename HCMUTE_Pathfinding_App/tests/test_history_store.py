import os
import tempfile
import unittest

from core.history_store import HistoryStore


class TestHistoryStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "history.sqlite3")
        self.store = HistoryStore(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_and_list_route(self):
        record_id = self.store.add_route(
            algorithm="A*",
            start_node_id="N01",
            start_node_name="Cong chinh",
            goal_node_id="N05",
            goal_node_name="Thu vien",
            distance_m=123.45,
            path_node_ids=["N01", "N02", "N05"],
            path_names=["Cong chinh", "Nga ba", "Thu vien"],
            visited_count=8,
            elapsed_ms=12.3,
        )

        records = self.store.list_routes()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, record_id)
        self.assertEqual(records[0].algorithm, "A*")
        self.assertAlmostEqual(records[0].distance_m, 123.45)
        self.assertEqual(records[0].path_node_ids, ["N01", "N02", "N05"])
        self.assertIn("Thu vien", records[0].route_text)

    def test_delete_and_clear(self):
        first_id = self.store.add_route("BFS", "A", "A", "B", "B", 10, ["A", "B"], ["A", "B"], 2, 1)
        self.store.add_route("DFS", "B", "B", "C", "C", 20, ["B", "C"], ["B", "C"], 3, 2)

        self.store.delete_route(first_id)
        self.assertEqual(len(self.store.list_routes()), 1)

        self.store.clear()
        self.assertEqual(self.store.list_routes(), [])


if __name__ == "__main__":
    unittest.main()
