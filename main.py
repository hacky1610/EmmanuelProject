from BL import ConfigReader, EnvReader
from zulu_trade import trade
import sys
import os


def check_config_folder():

    path_to_config = os.path.join(os.path.dirname(__file__), "Config")
    return os.path.exists(path_to_config) and os.path.isdir(path_to_config)
 


def main():
    # Zugriff auf die Befehlszeilenargumente
    arguments = sys.argv

    if len(arguments) <= 1:
        account_type = "DEMO"
    else:
        account_type = arguments[1]

    if check_config_folder():
        conf_reader = ConfigReader(account_type)
    else:
        conf_reader = EnvReader()

    print(f"Trade {account_type} account")
    trade(conf_reader, account_type)

if __name__ == "__main__":
    main()