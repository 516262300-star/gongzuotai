import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import monthly_ppt as m


class MonthlyPptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "run_monthly_meeting.ps1").touch()
        self.patches = [patch.object(m, "SOURCE", self.source), patch.object(m, "DATA", self.root / "data"),
                        patch.object(m, "STATE_FILE", self.root / "data" / "state.json"), patch.object(m, "_state", None)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def workbook(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
        return stream.getvalue()

    def prepare(self):
        m.upload("designer", "归属.xlsx", self.workbook(), {})
        m.upload("sales", "交易.xlsx", self.workbook(), {})
        m.upload("work", "作品.png", b"test-image", {"role": "美工", "name": "测试人员"})
        models = self.root / "models"
        models.mkdir()
        m.change_settings({"image_root": str(models), "output_dir": str(self.root / "output"), "month": "2026-09"})

    def test_upload_validation_and_draft_persistence(self):
        for name in ("../outside.png", "CON.png", "name.", "a/b.png"):
            with self.assertRaises(ValueError):
                m.upload("work", name, b"x", {"role": "美工", "name": "人员"})
        with self.assertRaises(ValueError):
            m.upload("sales", "broken.xlsx", b"not a workbook", {})
        self.prepare()
        work = m.state()["works"][0]
        work["active"] = False
        m.save()
        m._state = None
        self.assertFalse(m.snapshot()["works"][0]["active"])
        self.assertTrue(Path(work["path"]).exists())
        self.assertEqual(m.snapshot()["settings"]["month"], "2026-09")

    def test_model_batch_does_not_switch_to_partial_upload(self):
        original = m.state()["settings"]["image_root"]
        result = m.upload("model", "2701.png", b"x", {"batch": "a" * 32, "relative": "设计师/2701.png"})
        self.assertTrue(Path(result["path"]).exists())
        self.assertEqual(m.state()["settings"]["image_root"], original)
        with self.assertRaises(ValueError):
            m.upload("model", "2701.png", b"x", {"batch": "a" * 32, "relative": "../2701.png"})

    def test_restart_recovers_draft_and_marks_unfinished_job(self):
        self.prepare()
        with patch.object(m.threading, "Thread"):
            job = m.start_job({})
        m._state = None
        restored = m.snapshot()
        self.assertEqual(restored["jobs"][0]["id"], job["id"])
        self.assertEqual(restored["jobs"][0]["status"], "interrupted")
        self.assertEqual(len(restored["works"]), 1)
        with patch.object(m.threading, "Thread"):
            m.start_job({})

    def test_generation_is_snapshot_and_blocks_duplicates(self):
        self.prepare()
        with patch.object(m.threading, "Thread"):
            first = m.start_job({})
            with self.assertRaisesRegex(ValueError, "正在生成"):
                m.start_job({})
            m.state()["works"][0]["name"] = "改名"
            self.assertEqual(m.state()["jobs"][0]["works"][0]["name"], "测试人员")
            m.state()["jobs"][0]["status"] = "failed"
            second = m.start_job({})
            self.assertNotEqual(first["output"], second["output"])
            self.assertNotEqual(first["build_dir"], second["build_dir"])

    def test_success_requires_valid_ppt_and_runs_without_desktop(self):
        self.prepare()
        with patch.object(m.threading, "Thread"):
            m.start_job({})
        job = m.state()["jobs"][0]
        class Process:
            stdout = io.BytesIO(b"[3/3] rendering\n")
            def wait(self): return 0
        def launch(command, **kwargs):
            self.assertIn("-BuildDirectory", command)
            self.assertTrue(command[5].endswith("run_monthly_meeting.ps1"))
            self.assertFalse(kwargs.get("shell", False))
            output = Path(job["output"])
            output.parent.mkdir(parents=True)
            with zipfile.ZipFile(output, "w") as z:
                z.writestr("ppt/slides/slide1.xml", "<slide/>")
            return Process()
        with patch.object(m.subprocess, "Popen", side_effect=launch), patch.object(m, "append_record") as record:
            m.run_job(job)
        self.assertEqual(job["status"], "success")
        self.assertEqual(job["slide_count"], 1)
        self.assertTrue(m.public_job(job)["download_url"])
        self.assertEqual(record.call_args[0][0]["script"], "designer-monthly-ppt-web")
        # An exit code of zero with no usable PPT must still fail.
        job["output"] = str(self.root / "missing.pptx")
        with patch.object(m.subprocess, "Popen", return_value=Process()), patch.object(m, "append_record"):
            m.run_job(job)
        self.assertEqual(job["status"], "failed")
        self.assertIsNone(m.public_job(job)["download_url"])


if __name__ == "__main__":
    unittest.main()
