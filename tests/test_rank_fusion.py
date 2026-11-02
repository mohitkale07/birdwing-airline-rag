import unittest

from src.retrieval.rank_fusion import reciprocal_rank_fusion


class ReciprocalRankFusionTests(unittest.TestCase):
    def test_fuses_rankings_and_removes_duplicate_chunks(self) -> None:
        first = [
            {"chunk_id": "a", "text": "first"},
            {"chunk_id": "b", "text": "second"},
        ]
        second = [
            {"chunk_id": "b", "text": "second"},
            {"chunk_id": "c", "text": "third"},
        ]

        results = reciprocal_rank_fusion(
            [first, second],
            top_k=2,
            rank_constant=1,
        )

        self.assertEqual([result["chunk_id"] for result in results], ["b", "a"])
        self.assertEqual(results[0]["rrf_score"], 1 / 2 + 1 / 3)
        self.assertEqual(results[1]["rrf_score"], 1 / 2)

    def test_uses_payload_identity_when_chunk_id_is_missing(self) -> None:
        candidate = {
            "document_name": "policy.pdf",
            "start_page": 2,
            "end_page": 3,
            "text": "Relevant policy",
        }

        results = reciprocal_rank_fusion([[candidate], [candidate]])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rrf_score"], 2 / 61)

    def test_rejects_non_positive_rank_constant(self) -> None:
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion([], rank_constant=0)


if __name__ == "__main__":
    unittest.main()
