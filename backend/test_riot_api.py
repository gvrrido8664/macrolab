import unittest
from riot_api import PlaybookEngine

class CompositionTest(unittest.TestCase):
    def test_coordinates_are_clamped(self):
        self.assertEqual(PlaybookEngine.normalize_coordinates(-1, 20_000), {"x": 0, "y": 0})


    def test_each_analysis_model_can_win(self):
        cases = {
            "PROTECT_CARRY": [("Ornn", "TOP"), ("Sejuani", "JUNGLE"), ("Orianna", "MIDDLE"), ("Jinx", "BOTTOM"), ("Lulu", "UTILITY")],
            "SPLIT_PUSH_131": [("Fiora", "TOP"), ("Kindred", "JUNGLE"), ("Syndra", "MIDDLE"), ("Ezreal", "BOTTOM"), ("Bard", "UTILITY")],
            "POKE": [("Jayce", "TOP"), ("Nidalee", "JUNGLE"), ("Xerath", "MIDDLE"), ("Jhin", "BOTTOM"), ("Bard", "UTILITY")],
            "ENGAGE": [("Malphite", "TOP"), ("Amumu", "JUNGLE"), ("Orianna", "MIDDLE"), ("MissFortune", "BOTTOM"), ("Leona", "UTILITY")],
            "PICK": [("Camille", "TOP"), ("Elise", "JUNGLE"), ("Ahri", "MIDDLE"), ("Jhin", "BOTTOM"), ("Thresh", "UTILITY")],
            "DIVE": [("Ambessa", "TOP"), ("Nocturne", "JUNGLE"), ("Akali", "MIDDLE"), ("Samira", "BOTTOM"), ("Rakan", "UTILITY")],
            "COUNTER_ENGAGE": [("Poppy", "TOP"), ("Ivern", "JUNGLE"), ("Anivia", "MIDDLE"), ("Xayah", "BOTTOM"), ("Janna", "UTILITY")],
            "FRONT_TO_BACK": [("Ornn", "TOP"), ("Graves", "JUNGLE"), ("Viktor", "MIDDLE"), ("Caitlyn", "BOTTOM"), ("Braum", "UTILITY")],
        }
        for expected, picks in cases.items():
            with self.subTest(expected=expected):
                composition = [{"champion_name": champion, "role": role} for champion, role in picks]
                selected, reason, evaluations = PlaybookEngine.select_archetype(composition)
                self.assertEqual(selected, expected)
                self.assertTrue(reason)
                self.assertEqual(len(evaluations), 8)

