import unittest
from Agents.RayTune import RayTune
from Envs.forexEnv import ForexEnv
from Tracing.ConsoleTracer import ConsoleTracer
from unittest.mock import MagicMock


class RayTuneAgentTest(unittest.TestCase):

    def test_init(self):
        ag = RayTune()

    def test_train(self):
        ag = RayTune()

        result = MagicMock()
        result.config = "myconf"
        result.log_dir = "log"
        result.checkpoint = "check"

        best_results = MagicMock()
        best_results.get_best_result = MagicMock(return_value=result)

        tune = MagicMock()
        tune.fit = MagicMock(return_value=best_results)
        ag._create_tuner = MagicMock(return_value=tune)

        env_config = RayTune.create_env_config(None, window_size=12, tracer=ConsoleTracer())
        res, checkpoint = ag.train(ForexEnv, env_config)

        assert checkpoint == result.checkpoint

    def test_tuner_creation(self):
        ag = RayTune()
        env_config = RayTune.create_env_config(None, window_size=12, tracer=ConsoleTracer())
        tune = ag._create_tuner(ForexEnv, env_config)
        assert tune != None
