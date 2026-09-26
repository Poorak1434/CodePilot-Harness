import unittest
import tempfile
from pathlib import Path
from codepilot.safety.policy import SafetyPolicy
from codepilot.tools.router import ToolRouter


class TestTools(unittest.TestCase):
    def test_tool_router_and_filesystem_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            safety = SafetyPolicy(workspace_root=tmpdir)
            router = ToolRouter(safety)

            # 1. Create file tool
            res_create = router.dispatch("create_file", {"path": "hello.py", "content": "def greet():\n    print('Hello World')\n\ngreet()\n"})
            self.assertTrue(res_create.success)
            self.assertTrue(Path(tmpdir, "hello.py").exists())

            # 2. List dir tool
            res_list = router.dispatch("list_dir", {"path": "."})
            self.assertTrue(res_list.success)
            self.assertIn("hello.py", res_list.output)

            # 3. Read file tool
            res_read = router.dispatch("read_file", {"path": "hello.py"})
            self.assertTrue(res_read.success)
            self.assertIn("greet()", res_read.output)

            # 4. Search code tool
            res_search = router.dispatch("search_code", {"query": "greet"})
            self.assertTrue(res_search.success)
            self.assertIn("hello.py", res_search.output)

            # 5. Edit file tool
            res_edit = router.dispatch("edit_file", {"path": "hello.py", "old_str": "World", "new_str": "CodePilot"})
            self.assertTrue(res_edit.success)
            res_read_after = router.dispatch("read_file", {"path": "hello.py"})
            self.assertIn("CodePilot", res_read_after.output)

            # 6. Run command tool
            res_cmd = router.dispatch("run_command", {"command": "python3 hello.py"})
            self.assertTrue(res_cmd.success)
            self.assertIn("Hello CodePilot", res_cmd.output)


if __name__ == "__main__":
    unittest.main()
