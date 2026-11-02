import unittest
from unittest.mock import patch

from src.retrieval.search import HybridHRPolicyRetriever


class MultiQuerySearchTests(unittest.TestCase):
    def test_searches_original_and_unique_variants_then_fuses(self) -> None:
        retriever = object.__new__(HybridHRPolicyRetriever)
        first_results = [
            {"chunk_id": "a", "text": "first"},
            {"chunk_id": "b", "text": "second"},
        ]
        second_results = [
            {"chunk_id": "b", "text": "second"},
            {"chunk_id": "c", "text": "third"},
        ]

        with patch.object(
            retriever,
            "search",
            side_effect=[first_results, second_results],
        ) as search:
            results = retriever.search_multi_query(
                "Original question",
                ["Alternate wording", "original question", "Alternate wording"],
                top_k=2,
                role="employee",
            )

        self.assertEqual(search.call_count, 2)
        self.assertEqual(search.call_args_list[0].args[0], "Original question")
        self.assertEqual(search.call_args_list[1].args[0], "Alternate wording")
        self.assertEqual(
            [result["chunk_id"] for result in results],
            ["b", "a"],
        )


if __name__ == "__main__":
    unittest.main()
