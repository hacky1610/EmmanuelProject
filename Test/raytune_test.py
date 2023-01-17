import unittest
from Agents.RayTune import RayTune
from Envs.StockSignalEnv import StockSignalEnv
from Tracing.ConsoleTracer import ConsoleTracer

class RayTuneAgentTest(unittest.TestCase):

    def test_init(self):
        ag = RayTune()

    def test_train(self):
        ag = RayTune()
        env_config = RayTune.create_env_config(None,window_size=12,frame_bound=(12,200),tracer=ConsoleTracer())
        result,checkpoint =  ag.train(StockSignalEnv,env_config)

        assert len(checkpoint) > 0


