import unittest

from app import compare, parse_reference, save_comparison_graph, save_frame_sweep, simulate, working_set


class PagingTests(unittest.TestCase):
    def test_classic_trace_fault_totals(self):
        results = {s.algorithm: s.page_faults for s in compare("7,0,1,2,0,3,0,4,2,3", 3)}
        self.assertEqual(results, {"FIFO": 9, "LRU": 8, "OPTIMAL": 6})

    def test_hit_does_not_create_fault(self):
        result = simulate("1,1", 1, "LRU")
        self.assertEqual((result.page_faults, result.hits), (1, 1))
        self.assertEqual(result.steps[-1].frames, [1])

    def test_fifo_eviction_order(self):
        result = simulate("1,2,1,3", 2, "FIFO")
        self.assertEqual(result.steps[-1].evicted, 1)

    def test_optimal_eviction(self):
        result = simulate("1,2,3,1,2,4", 3, "OPTIMAL")
        # At the final reference, page 1 is never used again; 2 is used next.
        self.assertEqual(result.steps[-1].evicted, 1)

    def test_single_frame_and_rate(self):
        result = simulate("3,4,3", 1, "FIFO")
        self.assertEqual(result.page_faults, 3)
        self.assertAlmostEqual(result.fault_rate, 1.0)

    def test_validation(self):
        for value in ("", "1,x", "1,-2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_reference(value)
        for count in (0, 65, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                simulate("1", count, "FIFO")
        with self.assertRaises(ValueError):
            simulate("1", 1, "random")

    def test_working_set_window(self):
        sizes = [row["working_set_size"] for row in working_set("1,2,1,3", 3)]
        self.assertEqual(sizes, [1, 2, 2, 3])
        with self.assertRaises(ValueError):
            working_set("1,2", 3)

    def test_visualization_files(self):
        sims = compare("7,0,1,2,0,3,0,4,2,3", 3)
        self.assertIn("Page replacement comparison", save_comparison_graph(sims).read_text(encoding="utf-8"))
        self.assertIn("Frame count vs page faults", save_frame_sweep("7,0,1,2,0,3,0,4,2,3", 4).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
