from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
from Gan.bl import *

df = Tiingo().load_data_by_date("GBPUSD","2022-10-01","2022-12-31",DataProcessor(),"1hour",False,False)
T_df = get_technical_indicators(df)
# Drop the first 21 rows
# For doing the fourier
dataset = T_df.iloc[20:, :].reset_index(drop=True)
# Get Fourier features
dataset_F = get_fourier_transfer(dataset)
Final_data = pd.concat([dataset, dataset_F], axis=1)
Final_data.to_csv("Finaldata_with_Fourier.csv", index=False)


