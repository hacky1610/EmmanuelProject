from BL import EnvReader

env_reader = EnvReader()
mode = env_reader.get("mode")

if mode == "evaluate":
    import evaluate
else:
    import trade_once
