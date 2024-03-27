from BL import EnvReader

env_reader = EnvReader()
mode = env_reader.get("mode")

if mode == "update":
    import update_trades
else:
    import trade_once
