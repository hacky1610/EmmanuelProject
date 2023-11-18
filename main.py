from BL import ConfigReader
from zulu_trade import trade
import sys

def main():
    # Zugriff auf die Befehlszeilenargumente
    arguments = sys.argv

    if len(arguments) <= 1:
        account_type = "DEMO"
    else:
        account_type = arguments[1]
    conf_reader = ConfigReader(account_type)

    print(f"Trade {account_type} account")
    trade(conf_reader, account_type)

if __name__ == "__main__":
    main()