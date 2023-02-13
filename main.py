import ray
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Tuning.RayTuneQl import QlRayTune
import Utils
from Tracing.ConsoleTracer import ConsoleTracer

ray.init(local_mode=True, num_gpus=1)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD", "2022-08-15", "2022-12-31", dp, "1hour")

# Train
q = QlRayTune(data=df,
              tracer=ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="NewModel")
_, checkpoint = q.train()

exit(0)

# checkpoint_path = checkpoint._local_path
# print(f"use checkpoint {checkpoint_path}")
checkpoint_path = "D:\\Code\\EmmanuelProject\\logs\\QL_Indi\\QTrainer_5982e314_5_beta1=0.9112,beta2=0.9568,decay=0.0025,epsilon=0.8233,gamma=0.9000,hiddens=64_32_16,lr=0.0023,max_cpu_fraction_2023-02-06_01-12-42\\checkpoint_000025"
# Evaluate
q = QlRayTune(stock_name="GSPC_test",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL_Indi")
q.evaluate(model_path=os.path.join(checkpoint_path, "model.h5"))