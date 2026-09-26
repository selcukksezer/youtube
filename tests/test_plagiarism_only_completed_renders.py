# -*- coding: utf-8 -*-
"""
Test Item 120: Plagiarism check only compares against successfully completed renders.
Failed or incomplete renders must never block re-rendering.
"""
import unittest
import sqlite3
import os
import database
from plagiarism_checker import (
    check_script_originality,
    add_script_to_db,
    clear_plagiarism_db,
    _load_db,
)


class TestPlagiarismOnlyCompletedRenders(unittest.TestCase):
    def setUp(self):
        clear_plagiarism_db()
        database.init_db()

    def tearDown(self):
        clear_plagiarism_db()

    def test_failed_video_is_ignored_by_plagiarism_checker(self):
        topic = "Hayatınızı kolaylaştıracak 3 harika ürün testi"
        script = "Bu ürün hayatınızı tamamen kolaylaştıracak ve mutfakta geçirdiğiniz her saniyeyi değerli kılacaktır."

        # 1. Simüle: Veritabanında bu konu için bir failed video kaydı var
        with database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO videos (keyword, title, status) VALUES (?, ?, 'failed')",
                (topic, topic)
            )
            failed_id = cur.lastrowid
            conn.commit()

        # 2. Yanlışlıkla veya önceden eklenmiş olsa bile (render_status='failed' veya video_id=failed_id)
        add_script_to_db(script, keyword=topic, title=topic, video_id=failed_id, render_status="failed")

        # 3. İntihal kontrolü yapıldığında failed kayıt yoksayılmalı ve onaylanmalı
        is_orig, sim, matched = check_script_originality(
            script,
            keyword=topic,
            title=topic,
            auto_add_if_approved=False,
            only_completed_renders=True
        )
        self.assertTrue(is_orig, "Başarısız render intihal kontrolünü engellememeli!")
        self.assertLess(sim, 0.45)

    def test_completed_video_is_checked_properly(self):
        topic = "Başarılı tamamlanan harika video konusu"
        script = "Bu ürün hayatınızı tamamen kolaylaştıracak ve mutfakta geçirdiğiniz her saniyeyi değerli kılacaktır."

        # 1. Başarılı video tamamlandı
        with database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO videos (keyword, title, status) VALUES (?, ?, 'completed')",
                (topic, topic)
            )
            completed_id = cur.lastrowid
            conn.commit()

        # 2. Yalnızca başarılı tamamlanınca DB'ye eklendi
        add_script_to_db(script, keyword=topic, title=topic, video_id=completed_id, render_status="completed")

        # 3. Aynı senaryo tekrar üretilmek istendiğinde intihal olarak yakalanmalı
        is_orig, sim, matched = check_script_originality(
            script,
            keyword=topic,
            title=topic,
            auto_add_if_approved=False,
            only_completed_renders=True
        )
        self.assertFalse(is_orig, "Başarıyla tamamlanan video kopyası intihal olarak yakalanmalı!")
        self.assertGreaterEqual(sim, 0.45)


if __name__ == "__main__":
    unittest.main()
