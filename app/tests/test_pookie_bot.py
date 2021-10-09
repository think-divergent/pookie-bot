from unittest.mock import patch
from unittest import TestCase
from discord_client import group_participants, group_members_by_timeslot


class TestPookie(TestCase):
    @patch("random.shuffle")
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
        self.assertEqual(res, [[1, 2, 3], [4, 5, 6], [7, 8]])
        # 9 people group of 3, 3 and 3
        res = group_participants([1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(res, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        # 13 people group of 4, 4, 3 and 2
        res = group_participants(range(1, 14))
        self.assertEqual(res, [[1, 2, 3, 4], [5, 6, 7], [9, 10, 11], [8, 12, 13]])

    @patch("random.shuffle")
    def test_group_members_by_timeslot(self, shuffle):
        groups_to_member_ids = {
            0: {"AD", "CU", "SE", "MA"},
            1: {"RM", "CU", "SE", "MAL"},
            2: {"FE"},
            3: {"SE", "MY"},
            4: {"SE", "CU"},
            5: {"RO", "FE", "CU"},
        }
        all_members = {m for members in groups_to_member_ids.values() for m in members}
        all_members.update(["AA", "BB", "CC", "DD", "EE", "FF", "GG", "HH", "II"])
        groups = group_members_by_timeslot(
            all_members, groups_to_member_ids, lambda x: x
        )
        self.assertEqual(
            groups,
            {
                -1: ["HH", "II"],
                0: ["AD", "CU", "DD", "MA"],
                1: ["AA", "EE", "MAL", "RM"],
                3: ["BB", "FF", "MY", "SE"],
                5: ["CC", "FE", "GG", "RO"],
            },
        )
        return
        all_members.update(["JJ"])
        groups = group_members_by_timeslot(
            all_members, groups_to_member_ids, lambda x: x
        )
        self.assertEqual(
            groups,
            {
                -1: ["HH", "II", "JJ"],
                0: ["AD", "CU", "DD", "MA"],
                1: ["AA", "EE", "MAL", "RM"],
                3: ["BB", "FF", "MY", "SE"],
                5: ["CC", "FE", "GG", "RO"],
            },
        )
        all_members.update(["KK"])
        groups = group_members_by_timeslot(
            all_members, groups_to_member_ids, lambda x: x
        )
        self.assertEqual(
            groups,
            {
                -2: ["JJ", "KK"],
                -1: ["HH", "II"],
                0: ["AD", "CU", "DD", "MA"],
                1: ["AA", "EE", "MAL", "RM"],
                3: ["BB", "FF", "MY", "SE"],
                5: ["CC", "FE", "GG", "RO"],
            },
        )
        all_members.update(["LL"])
        groups = group_members_by_timeslot(
            all_members, groups_to_member_ids, lambda x: x
        )
        self.assertEqual(
            groups,
            {
                -2: ["JJ", "KK", "LL"],
                -1: ["HH", "II"],
                0: ["AD", "CU", "DD", "MA"],
                1: ["AA", "EE", "MAL", "RM"],
                3: ["BB", "FF", "MY", "SE"],
                5: ["CC", "FE", "GG", "RO"],
            },
        )
