import pandas as pd

def analyze_by_symbol(df):
    required_columns = [
        '_symbol', '_train_precision', '_train_reward', '_test_precision',
        '_test_reward', '_test_trade_count', '_atr_factor_stop', '_atr_factor_limit'
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    grouped = df.groupby('_symbol')

    summary = grouped.agg({
        '_train_precision': ['mean', 'median'],
        '_train_reward': ['mean', 'median'],
        '_test_precision': ['mean', 'median'],
        '_test_reward': ['mean', 'median'],
        '_test_trade_count': ['sum'],
    })

    # Spaltennamen flach machen
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={'_symbol_count': 'num_entries'})

    return summary
pd.set_option('display.max_columns', None)
df = pd.read_parquet("../predictor_3.parquet" )
print(df["_test_precision"].mean())
print(df["_test_reward"].mean())
print(df[df["_trade_mode"] == "sell"]["_test_precision"].mean())

for f in [2.0,1.5,1.2,1.0,0.8]:

    print(f"Factor {f} - {df[df['_atr_factor_stop'] == f]['_test_precision'].mean()}")
#print(analyze_by_symbol(df))



