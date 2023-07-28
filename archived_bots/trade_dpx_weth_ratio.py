import os
from os.path import exists
import csv
import sys
import time
import datetime
from brownie import *
from pycoingecko import CoinGeckoAPI


# Initialize API keys
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN


ACCOUNT_NAME = os.getenv('ACCOUNT_NAME_DPX_BOT') 
PASSWORD = os.getenv('ACCOUNT_PW')

try:
    network.connect('arbitrum-main')
except:
    sys.exit(
        "Could not connect to Arbitrum! Verify that brownie lists the Arbitrum Mainnet using 'brownie networks list'"
    )

try:
    user = accounts.load(ACCOUNT_NAME, PASSWORD)
except:
    sys.exit(
        "Could not load account! Verify that your account is listed using 'brownie accounts list' and that you are using the correct password. If you have not added an account, run 'brownie accounts new' now."
    )


# Load the token and router contracts
print('Loading Contracts:')
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
dpx_contract = Contract.from_explorer('0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55')
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')
weth_price = Contract.from_explorer('0x639fe6ab55c921f74e7fac1ee960c0b6293ba612')

# Initialize the CoinGecko API
cg = CoinGeckoAPI()

# Create dictionaries for our tokens
dpx = {
    "address": dpx_contract.address,
    "symbol": dpx_contract.symbol(),
    "decimals": dpx_contract.decimals(),
}
weth = {
    "address": weth_contract.address,
    "symbol": weth_contract.symbol(),
    "decimals": weth_contract.decimals(),
}

#
# Config Variables
#

# Simulate swaps and approvals
DRY_RUN = False
# Quit after the first successful trade
ONE_SHOT = False
# How much of a difference between the last trade price and the current trade price before you initiate a swap?
SWAP_THRESHOLD = 0.01
# What percentage of token or WETH balance do you want to swap when a trade opportunity becomes available?
SWAP_PERCENT = 0.25
# max slippage
MAX_SLIPPAGE = 0.001
# How often to run the main loop (in seconds)
LOOP_TIME = 3.0



#
# Helper functions
# 
def get_approval(token, router, user):
    """ 
    Retrieves the token approval value for a given routing contract and user.
    """
    try:
        return token.allowance.call(user, router.address)
    except Exception as e:
        print(f"Exception in get_approval: {e}")
        return False

def token_approve(token, router, value="unlimited"):
    """ 
    Will set the token approval for a given router contract to 
    spend tokens at a given token contract address on behalf of
    our user. Note this includes a default value that will set 
    unlimited approval if not specified. I do this for my bot since 
    it only holds tokens that I am actively swapping, and do not
    want to issue hundreds of approvals for partial balances.
    """
    if DRY_RUN:
        return True

    if value == "unlimited":
        try:
            token.approve(
                router,
                2 ** 256 - 1,
                {"from": user},
            )
            return True
        except Exception as e:
            print(f"Exception in token_approve: {e}")
            raise
    else:
        try:
            token.approve(
                router,
                value,
                {"from": user},
            )
            return True
        except Exception as e:
            print(f"Exception in token_approve: {e}")
            raise

def print_current_account_value():
    """
    Print the current account balance in USD.
    """
    # get current prices from data feeds
    chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()
    coingecko_price_of_dpx_in_usd = cg.get_price(ids='dopex', vs_currencies='usd')['dopex']['usd']

    # calculate the dollar values based on current balances
    account_value_of_weth_in_usd = (user.balance() / 10**weth["decimals"]) * chainlink_price_of_weth_in_usd
    account_value_of_dpx_in_usd = (dpx_contract.balanceOf(user.address) / 10**dpx['decimals']) * coingecko_price_of_dpx_in_usd
    account_usd_value = account_value_of_dpx_in_usd + account_value_of_weth_in_usd
    account_eth_value = (user.balance() / 10**weth['decimals']) + (account_value_of_dpx_in_usd / chainlink_price_of_weth_in_usd )

    print(
    f"------------------------ \
        \n{datetime.datetime.now().strftime('[%H:%M:%S]')} \
        \nCurrent account value:\n \
        \nWETH: {round(user.balance() / 10**weth['decimals'],3)} @ ${round(chainlink_price_of_weth_in_usd,2)}: ${round(account_value_of_weth_in_usd,2)} \
        \nDPX: {round(dpx_contract.balanceOf(user.address) / 10**dpx['decimals'],3)} @ ${round(coingecko_price_of_dpx_in_usd, 2)}: ${round(account_value_of_dpx_in_usd, 2)} \
        \n\nTotal (USD): ${round(account_usd_value, 2)} \
        \nTotal (ETH): {round(account_eth_value, 4)} \
        \n------------------------\n" 
    )

def log_transaction():
    """
    Writes account data to a CSV file after a successful trade.
    """

    try:
        print('\nLogging transaction...')
        
        # get current prices from data feeds
        chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()
        coingecko_price_of_dpx_in_usd = cg.get_price(ids='dopex', vs_currencies='usd')['dopex']['usd']

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',
            'eth_balance',
            'eth_price',
            'eth_value_in_usd',
            'dpx_balance',
            'dpx_price',
            'dpx_value_in_usd',
            'total_value_in_usd',
            'total_value_in_eth',
            'curent_weth_out',
            'curent_dpx_out'
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = account_name
        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_eth_balance * csv_eth_price
        csv_dpx_balance = dpx_contract.balanceOf(user.address) / 10**dpx['decimals']
        csv_dpx_price = coingecko_price_of_dpx_in_usd
        csv_dpx_value_in_usd = csv_dpx_balance * csv_dpx_price
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_dpx_value_in_usd
        csv_total_value_in_eth = csv_eth_balance + (csv_dpx_value_in_usd / csv_eth_price)

        # Write the CSV file
        filename = 'logs/trade_dpx_weth_ratio.csv'
        row = [
            csv_date, 
            csv_time, 
            csv_account_name, 
            csv_eth_balance, 
            csv_eth_price, 
            csv_eth_value_in_usd,
            csv_dpx_balance,
            csv_dpx_price,
            csv_dpx_value_in_usd,
            csv_total_value_in_usd,
            csv_total_value_in_eth,
            current_weth_out,
            current_dpx_out
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


def get_current_weth_out():
    """ Get the current dpx -> weth ratio """
    return router.getAmountsOut(
        1 * (10 ** dpx["decimals"]),
        [
            dpx["address"],
            weth["address"],
        ],
    )[-1] / (10 ** weth["decimals"])
 
def get_current_dpx_out():
    """ Get the current weth -> dpx ratio """
    return router.getAmountsOut(
        1 * (10 ** weth["decimals"]),
        [
            weth["address"],
            dpx["address"],
        ],
    )[-1] / (10 ** dpx["decimals"])
    
def swap_weth_for_dpx():
    """ Swap WETH for dpx. """

    print(f"*** EXECUTING SWAP ***\n")
    
    router.swapETHForExactTokens(
        # amount of dpx to get out
        (user.balance() * SWAP_PERCENT) * (10**dpx["decimals"]) * ( current_dpx_out / 10**dpx["decimals"] ),
        # address path (from WETH to dpx)
        [weth["address"], dpx["address"]],
        # address to send dpx tokens to
        user.address,
        # deadline
        1000*int(time.time()+30),
        # the maximum amount of WETH that will be consumed by the swap (this ensures that WETH cannot be over-consumed during the transaction). you calculate this value like this: 
        {'from':user.address, 'value': user.balance() * SWAP_PERCENT * (1 + MAX_SLIPPAGE)}
    )

def swap_dpx_for_weth():
    """ Swap dpx for WETH. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForETH(
        # amount of dpx in (includes slippage)
        (dpx_contract.balanceOf(user.address) * SWAP_PERCENT * (1 + MAX_SLIPPAGE)),

        # minimum amount of WETH to get out
        (dpx_contract.balanceOf(user.address) * SWAP_PERCENT) * (10**weth["decimals"]) * ( current_weth_out / 10**weth["decimals"] ),

        # address path (from dpx to WETH)
        [dpx["address"], weth["address"]],

        # address to send WETH tokens to
        user.address,

        # deadline
        1000*int(time.time()+30),

        # 
        {'from':user.address}
    )

# Confirm approvals for tokens
print("\nChecking approvals:")

if get_approval(dpx_contract, router, user):
    print(f"• {dpx['symbol']} OK\n")
else:
    token_approve(dpx_contract, router)


# Initialize this outside of the loop so it doesn't get overwrittern on loop start. 
# Multiply by a small fraction so the loop functions properly on initial load.
last_weth_out = get_current_weth_out() * 0.9999
last_dpx_out = get_current_dpx_out() * 0.9999

# Initialize these with neutral values. The loop will update them whenever a trade occurs.
# weth_out_at_last_trade = last_weth_out
# dpx_out_at_last_trade = last_dpx_out

# Manually insert last trade values if there was a recent trade
weth_out_at_last_trade = 0.119713
dpx_out_at_last_trade = 8.300890


# print current account value for reference
print_current_account_value()


#
#  *** THE LOOP ***
#
print('Starting the loop...')
while True:

    try:
        current_weth_out = get_current_weth_out()
        current_dpx_out = get_current_dpx_out()

        # if the dpx -> weth ratio has changed...
        if current_weth_out != last_weth_out:
            # update the current ratio
            last_weth_out = current_weth_out

            # Determine the difference between the ratio at the last trade and the current ratio.
            weth_out_difference = (current_weth_out - weth_out_at_last_trade ) / weth_out_at_last_trade
            
            print(
                    f"{datetime.datetime.now().strftime('[%H:%M:%S]')} | {dpx['symbol']} -> {weth['symbol']} | ({current_weth_out:.6f}) | {round(weth_out_difference * 100, 2)}%"
                )

        # if the weth -> dpx ratio has changed...
        if current_dpx_out != last_dpx_out:
            # update the current ratio
            last_dpx_out = current_dpx_out

            # Determine the difference between the ratio at the last trade and the current ratio.
            dpx_out_difference = (current_dpx_out - dpx_out_at_last_trade ) / dpx_out_at_last_trade

            print(
                    f"{datetime.datetime.now().strftime('[%H:%M:%S]')} | {weth['symbol']} -> {dpx['symbol']} | ({current_dpx_out:.6f}) | {round(dpx_out_difference * 100, 2)}%"
                )

        # If the amount of dpx you can get out has increased, then swap some WETH for dpx
        if (dpx_out_difference > SWAP_THRESHOLD):

            # Print the trade opportunity
            print(
            f"\nTrade opportunity detected! The current swap rate is {SWAP_THRESHOLD * 100}% or more than the rate of the last trade.\n\
            \nLast WETH-DPX ratio: {round(dpx_out_at_last_trade, 6)}. \
            \nCurrent WETH-DPX ratio: {round(current_dpx_out, 6)}. \
            \nDifference: {round(dpx_out_difference * 100, 2)}%. \
            \nTherefore: swap WETH for DPX."
            )
            
            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break

            # If there's no WETH in your wallet, then no trade happens but we alert the console
            if (user.balance() == 0):
                print('\nYour WETH balance is 0. Cannot initiate a trade right now.')

            # If you have WETH to trade...
            else: 
                print('\nYou have WETH in your wallet. Attempting a trade...\n')

                try:
                    swap_weth_for_dpx()
                    print("\nTrade successful!\n")
                    print_current_account_value()
                    log_transaction()

                    # Update the last traded values
                    dpx_out_at_last_trade = current_dpx_out
                    weth_out_at_last_trade = current_weth_out

                except Exception as e:
                    print(f"Exception: {e}")

        # If the amount of WETH you can get out has increased, then swap some dpx for WETH
        if (weth_out_difference > SWAP_THRESHOLD):
            
            # Print the trade opportunity
            print(
            f"\nTrade opportunity detected! The current swap rate is {SWAP_THRESHOLD * 100}% or more than the rate of the last trade.\n\
            \nLast DPX-WETH ratio: {round(weth_out_at_last_trade, 6)}. \
            \nCurrent DPX-WETH ratio: {round(current_weth_out, 6)}. \
            \nDifference: {round(weth_out_difference * 100, 2)}%. \
            \nTherefore: swap DPX for WETH."
            )
            
            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break

            # If there's no dpx in your wallet, then no trade happens but we alert the console
            if (dpx_contract.balanceOf(user.address) / 10**dpx["decimals"] == 0):
                print('\nYour dpx balance is 0. Cannot initiate a trade right now.')

            # If you have dpx to trade...
            else: 
                print('\nYou have dpx in your wallet. Attempting a trade...\n')

                try:
                    swap_dpx_for_weth()
                    print("\nTrade successful!\n")
                    print_current_account_value()
                    log_transaction()

                    # Update the last traded values
                    dpx_out_at_last_trade = current_dpx_out
                    weth_out_at_last_trade = current_weth_out

                except Exception as e:
                    print(f"Exception: {e}")

        if ONE_SHOT:
            print(f"Breaking the loop because ONE_SHOT = {ONE_SHOT}.")
            break
    
    except Exception as e:
        print(f"Error: {e} \n\nWill wait 30 seconds and try again...")
        time.sleep(30)
        continue

    # TO DO: refactor this to be a bit more advanced (see avax/avalanche_sspell_spell.py)
    time.sleep(LOOP_TIME)
