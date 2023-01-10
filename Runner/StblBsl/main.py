import datetime as dt
from matplotlib import pyplot as plt
from Tracing.FileTracer import FileTracer
from Connectors.Loader import Loader
from Agents.AgentCollection import AgentCollection
import os

logDir = os.path.abspath("../../runs")

ac = AgentCollection()
ac.loadFromFile("../../Config/Runs.csv")

df = Loader.loadFromOnline("USDJPY=X", dt.datetime.today() - dt.timedelta(350), dt.datetime.today())

tracer = FileTracer(os.path.join(logDir,"trace.log"))
agents = ac.Run(df, plt, tracer=tracer, logdir=logDir)
