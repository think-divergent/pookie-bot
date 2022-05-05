from unittest.mock import patch
from unittest import TestCase
from clients.discord.groups import group_participants


class TestPookie(TestCase):
    @patch("clients.discord.groups._daily_random_shuffle")
    def test_group_participants(self, shuffle):
        # 1 person... one group.. can't do better
        res = group_participants([1])
        self.assertEqual(res, [[1]])
        # 2 people a single group of 2
        res = group_participants([1, 2])
        self.assertEqual(res, [[1, 2]])
        # 3 people, a single group of 3
        res = group_participants([1, 2, 3])
        self.assertEqual(res, [[1, 2, 3]])
        # 4 people, a single group of 3
        res = group_participants([1, 2, 3, 4])
        self.assertEqual(res, [[1, 2], [3, 4]])
        # 5 people group of 2 and 3
        res = group_participants([1, 2, 3, 4, 5])
        self.assertEqual(res, [[1, 2], [3, 4, 5]])
        # 7 people group of 3 and 4
        res = group_participants([1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(res, [[1, 2, 3], [4, 5, 6, 7]])
        # 8 people group of 3, 3 and 2
        res = group_participants([1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(res, [[1, 2, 3, 4], [5, 6, 7, 8]])
        # 9 people group of 3, 3 and 3
        res = group_participants([1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(res, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        # 13 people group of 4, 4, 3 and 3
        res = group_participants(range(1, 14))
        self.assertEqual(res, [[1, 2, 3, 4], [5, 6, 7], [9, 10, 11], [8, 12, 13]])
        # 11 people group of 3, 3, 3, and 2
        res = group_participants(range(1, 12))
        self.assertEqual(res, [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11]])
