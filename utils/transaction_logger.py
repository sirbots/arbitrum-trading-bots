import os
from os.path import exists
import csv
import datetime
from brownie import *
from pycoingecko import CoinGeckoAPI

#
# This is just a workspace for testing the logging function before copying it to the actively running bots.
#

# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

# Initialize the CoinGecko API
cg = CoinGeckoAPI()

ACCOUNT_NAME = os.getenv('ACCOUNT_NAME') 
PASSWORD = os.getenv('ACCOUNT_PW')

account_name = ACCOUNT_NAME

network.connect('arbitrum-main')
user = accounts.load(ACCOUNT_NAME, PASSWORD)

# Load contracts
dpx_contract = Contract.from_explorer('0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55')
rdpx_contract = Contract.from_explorer('0x32Eb7902D4134bf98A28b963D26de779AF92A212')
weth_price = Contract.from_explorer('0x639fe6ab55c921f74e7fac1ee960c0b6293ba612')




def log_transaction():
    """
    Writes account data to a CSV file after a successful trade.
    """

    try:
        print('\nLogging transaction...\n')
        
        # get current prices from data feeds
        chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()
        coingecko_price_of_rdpx_in_usd = cg.get_price(ids='dopex-rebate-token', vs_currencies='usd')['dopex-rebate-token']['usd']

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',
            'eth_balance',
            'eth_price',
            'eth_value_in_usd',
            'rdpx_balance',
            'rdpx_price',
            'rdpx_value_in_usd',
            'total_value_in_usd',
            'total_value_in_eth',
            'current_weth_out',
            'curent_rdpx_out'
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = account_name
        csv_eth_balance = user.balance() / 10**18
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_eth_balance * csv_eth_price
        csv_rdpx_balance = rdpx_contract.balanceOf(user.address) / 10**18
        csv_rdpx_price = coingecko_price_of_rdpx_in_usd
        csv_rdpx_value_in_usd = csv_rdpx_balance * csv_rdpx_price
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_rdpx_value_in_usd
        csv_total_value_in_eth = csv_eth_balance + (csv_rdpx_value_in_usd / csv_eth_price)


        # Write the CSV file
        filename = '../logs/test_log.csv'
        row = [
            csv_date, 
            csv_time, 
            csv_account_name, 
            csv_eth_balance, 
            csv_eth_price, 
            csv_eth_value_in_usd,
            csv_rdpx_balance,
            csv_rdpx_price,
            csv_rdpx_value_in_usd,
            csv_total_value_in_usd,
            csv_total_value_in_eth,
            0.0100,
            85.34 
            ]

        # Create a blank CSV file with header rows if one does not already exist
        if (not exists(filename)):
            with open(filename, 'w') as csvfile:
                # create a csv writer object
                csvwriter = csv.writer(csvfile)

                # append the new row
                csvwriter.writerow(headers)

        # Open the CSV file and append the new row of data
        with open(filename, 'a') as csvfile:
            # create a csv writer object
            csvwriter = csv.writer(csvfile)

            # append the new row
            csvwriter.writerow(row)

    except Exception as e:
        print(f"Failed to log transaction with error: {e}")


log_transaction()