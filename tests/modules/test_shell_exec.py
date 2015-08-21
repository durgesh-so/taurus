import os
from tests import setup_test_logging, BZTestCase, RecordingHandler
from tests.mocks import EngineEmul
from bzt.modules.shell_exec import ShellExecutor
from bzt import AutomatedShutdown
import yaml

setup_test_logging()

class TaskTestCase(BZTestCase):
    def setUp(self):
        self.obj = ShellExecutor()
        self.obj.engine = EngineEmul()
        self.log_recorder = RecordingHandler()
        self.obj.log.addHandler(self.log_recorder)

class TestBlockingTasks(TaskTestCase):

    def test_task_prepare_prepare(self):
        task = {"command": "sleep 1", "block": True, "stop-stage":"prepare"}
        self.obj.settings = [task]
        self.obj.prepare()
        self.obj.shutdown()
        self.assertIn("Task sleep 1 already completed, no shutdown needed", self.log_recorder.debug_buff.getvalue())

    def test_task_prepare_shutdown(self):
        task = {"command": "sleep 1", "block": True, "stop-stage": "shutdown"}
        self.obj.settings = [task]
        self.obj.prepare()
        self.obj.shutdown()
        self.assertIn("Task sleep 1 already completed, no shutdown needed", self.log_recorder.debug_buff.getvalue())

    def test_task_output(self):
        task = {"command": "echo hello", "block": True, "stop-stage": "check"}
        self.obj.settings = [task]
        self.obj.prepare()
        self.obj.check()
        self.assertIn("Task echo hello stdout:\n hello", self.log_recorder.debug_buff.getvalue())

    def test_task_start_error(self):
        task = {"label": "task one", "command": "nothing", "block": True}
        self.obj.settings = [task]
        self.obj.prepare()
        self.assertIn("Exception while starting task", self.log_recorder.err_buff.getvalue())

    def test_task_stop_on_fail(self):
        task = {"command": "python -m nosuchmodule", "block": True, "stop-on-fail": True}
        self.obj.settings = [task]
        try:
            self.obj.prepare()
            self.fail()
        except AutomatedShutdown:
            pass


class TestNonBlockingTasks(TaskTestCase):

    def test_task_prepare_prepare(self):
        task = {"command": "sleep 10", "block": False}
        self.obj.settings = [task]
        self.obj.prepare()
        self.obj.shutdown()
        self.assertIn("Task sleep 10 was not completed, shutting it down", self.log_recorder.info_buff.getvalue())

    def test_task_prepare_shutdown(self):
        task = {"command": "sleep 1", "block": False, "stop-stage": "shutdown"}
        blocking_task = {"command": "sleep 2", "block": True}
        self.obj.settings = [task, blocking_task]
        self.obj.prepare()
        self.obj.shutdown()
        self.assertIn("Task sleep 1 already completed, no shutdown needed", self.log_recorder.debug_buff.getvalue())

    def test_task_output(self):
        task = {"command": "echo hello", "block": False, "stop-stage": "check", "out":"out.txt"}
        blocking_task = {"command": "sleep 1", "block": True}
        self.obj.settings = [task, blocking_task]
        self.obj.prepare()
        self.obj.check()
        self.obj.shutdown()
        self.assertIn("Task echo hello stdout:\n hello", self.log_recorder.debug_buff.getvalue())

    def test_task_start_error(self):
        task = {"label": "task one", "command": "nothing", "block": False}
        self.obj.settings = [task]
        self.obj.prepare()
        self.assertIn("Exception while starting task", self.log_recorder.err_buff.getvalue())

    def test_task_stop_on_fail(self):
        task = {"command": "python -m nosuchmodule", "block": False, "stop-on-fail": True, "stop-stage":"prepare"}
        blocking_task = {"command": "sleep 1", "block": True}
        self.obj.settings = [task, blocking_task]
        try:
            self.obj.prepare()
            self.fail()
        except AutomatedShutdown:
            pass

class TestTasksConfigs(TaskTestCase):

    def test_unknown_key_in_config(self):
        task = {"invalid": "invalid", "command": "sleep 10", "block": False,
                "start-stage": "prepare",
                "stop-stage": "shutdown", "force-shutdown": True, "stop-on-fail": False}
        self.obj.settings.append = [task]
        self.obj.prepare()
        self.assertIn("Ignoring unknown option", self.log_recorder.warn_buff.getvalue())

    def test_wrong_stage(self):
        task = {"invalid": "invalid", "command": "sleep 10", "block": False,
                "start-stage": "prepare",
                "stop-stage": "shutTdown", "force-shutdown": True, "stop-on-fail": False}
        self.obj.settings.append = [task]
        self.obj.prepare()

        # try:
        #     obj.prepare()
        #     self.fail()
        # except ValueError:
        #     pass

        self.assertIn("Invalid stage name in task config!", self.log_recorder.err_buff.getvalue())

    def test_shell_exec(self):
        """

        :return:
        """
        command = "echo 1 > /tmp/text1.txt && sleep 5" # "&& sleep 1 && echo 2> {artifacts_dir}/text1.txt && echo <2"
        task = {"command": command.format(artifacts_dir=self.obj.engine.artifacts_dir), "block": True, "stop-stage":"prepare", "label":"test shell"}
        self.obj.settings = [task]
        self.obj.prepare()
        self.assertTrue(os.path.exists("tmp/text1.txt"))

    def test_config(self):
        obj = ShellExecutor()
        obj.engine = EngineEmul()
        obj.engine.config.merge(yaml.load(open("tests/yaml/shell_hook_start").read()))
        obj.settings = obj.engine.config.get("services").get("shellexec")
        obj.prepare()
        obj.check()
        obj.shutdown()