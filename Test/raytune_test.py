import unittest
from Agents.RayTune import RayTune
from Envs.forexEnv import ForexEnv
from Tracing.ConsoleTracer import ConsoleTracer

class RayTuneAgentTest(unittest.TestCase):

    def test_init(self):
        ag = RayTune()

    def test_train(self):
        ag = RayTune()
        env_config = RayTune.create_env_config(None,window_size=12,tracer=ConsoleTracer())
        result,checkpoint =  ag.train(ForexEnv,env_config)

        assert len(checkpoint) > 0


