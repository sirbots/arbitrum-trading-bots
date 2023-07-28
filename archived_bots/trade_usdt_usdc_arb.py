import os
from os.path import exists
import csv
import sys
import time
import datetime
from brownie import *


# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')


# The ARBISCAN_TOKEN has been added to .zshrc
# ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
# os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

ACCOUNT_NAME = os.getenv('ACCOUNT_NAME_USDT_USDC_BOT') 
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
print('\nAccount and network loaded. Loading contracts:')

# token contracts
usdt_contract = Contract.from_explorer('0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9')
usdc_contract = Contract.from_explorer('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')

# sushi router contract
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')

# Price contracts / APIs
usdt_price = Contract.from_explorer('0x3f3f5df88dc9f13eac63df89ec16ef6e7e25dde7')
usdc_price = Contract.from_explorer('0x50834f3163758fcc1df9973b6e91f0f0f0434ad3')
weth_price = Contract.from_explorer('0x639fe6ab55c921f74e7fac1ee960c0b6293ba612')


# Create dictionaries for our tokens
usdc = {
    "address": usdc_contract.address,
    "symbol": usdc_contract.symbol(),
    "decimals": usdc_contract.decimals(),
}
usdt = {
    "address": usdt_contract.address,
    "symbol": usdt_contract.symbol(),
    "decimals": usdt_contract.decimals(),
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
# If the current_pool_price_discount rate goes above this number: swap USDC for USDT
TRADE_THRESHOLD = 1.05
# What percentage of token or USDT balance do you want to swap when a trade opportunity becomes available?
SWAP_PERCENT = 0.5
# max slippage
MAX_SLIPPAGE = 0.05
# How often to run the main loop (in seconds)
LOOP_TIME = 5
# How long to wait on an error
ERROR_SLEEP_TIME = 90


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
    chainlink_price_of_usdt_in_usd = usdt_price.latestRoundData()[1] / 10**usdt_price.decimals()
    chainlink_price_of_usdc_in_usd = usdc_price.latestRoundData()[1] / 10**usdc_price.decimals()
    chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()

    # calculate the dollar values based on current balances
    account_value_of_weth_in_usd = (user.balance() / 10**weth["decimals"]) * chainlink_price_of_weth_in_usd
    account_value_of_usdt_in_usd = (usdt_contract.balanceOf(user.address) / 10**usdt["decimals"]) * chainlink_price_of_usdt_in_usd
    account_value_of_usdc_in_usd = (usdc_contract.balanceOf(user.address) / 10**usdc['decimals']) * chainlink_price_of_usdc_in_usd
    account_usd_value = account_value_of_weth_in_usd + account_value_of_usdc_in_usd + account_value_of_usdt_in_usd
    account_eth_value = (user.balance() / 10**weth['decimals']) + (account_value_of_usdt_in_usd / chainlink_price_of_weth_in_usd) + (account_value_of_usdc_in_usd / chainlink_price_of_weth_in_usd)

    print(
    f"------------------------ \
        \n{datetime.datetime.now().strftime('%D')} @ {datetime.datetime.now().strftime('%H:%M:%S')} \
        \nCurrent account value:\n \
        \nWETH: {round(user.balance() / 10**weth['decimals'],3)} @ ${round(chainlink_price_of_weth_in_usd,2)}: ${round(account_value_of_weth_in_usd,2)} \
        \nUSDT: {round(usdt_contract.balanceOf(user.address) / 10**usdt['decimals'],3)} @ ${round(chainlink_price_of_usdt_in_usd,2)}: ${round(account_value_of_usdt_in_usd,2)} \
        \nUSDC: {round(usdc_contract.balanceOf(user.address) / 10**usdc['decimals'],3)} @ ${round(chainlink_price_of_usdc_in_usd, 4)}: ${round(account_value_of_usdc_in_usd, 2)} \
        \n\nTotal (USD): ${round(account_usd_value, 2)} \
        \nTotal (ETH): {round(account_eth_value, 4)} \
        \n------------------------" 
    )

def log_transaction():
    """
    Writes account data to a CSV file after a successful trade.
    """

    try:
        print('\nLogging transaction...\n')
        
        # get current prices from data feeds
        chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()
        chainlink_price_of_usdt_in_usd = usdt_price.latestRoundData()[1] / 10**usdt_price.decimals()
        chainlink_price_of_usdc_in_usd = usdc_price.latestRoundData()[1] / 10**usdt_price.decimals()

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',

            'eth_balance',
            'eth_price',
            'eth_value_in_usd',

            'usdt_balance',
            'usdt_price',
            'usdt_value_in_usd',

            'usdc_balance',
            'usdc_price',
            'usdc_value_in_usd',

            'total_value_in_usd',
            'total_value_in_eth',
            
            'current_usdt_out',
            'curent_usdc_out'
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = account_name
        
        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_eth_balance * csv_eth_price

        csv_usdt_balance = usdt_contract.balanceOf(user.address) / 10**usdt['decimals']
        csv_usdt_price = chainlink_price_of_usdt_in_usd
        csv_usdt_value_in_usd = csv_usdt_balance * csv_usdt_price

        csv_usdc_balance = usdc_contract.balanceOf(user.address) / 10**usdc['decimals']
        csv_usdc_price = chainlink_price_of_usdc_in_usd
        csv_usdc_value_in_usd = csv_usdc_balance * csv_usdc_price
        
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_usdt_value_in_usd + csv_usdc_value_in_usd
        csv_total_value_in_eth = csv_eth_balance + (csv_usdt_value_in_usd / csv_eth_price) + (csv_usdc_value_in_usd / csv_eth_price)

        # Write the CSV file
        filename = 'logs/trade_usdc_usdt_dollar_arb.csv'
        row = [
            csv_date, 
            csv_time, 
            csv_account_name, 

            csv_eth_balance, 
            csv_eth_price, 
            csv_eth_value_in_usd,

            csv_usdt_balance,
            csv_usdt_price,
            csv_usdt_value_in_usd,

            csv_usdc_balance,
            csv_usdc_price,
            csv_usdc_value_in_usd,

            csv_total_value_in_usd,
            csv_total_value_in_eth,
            
            current_usdt_out,
            current_usdc_out
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


def get_current_usdt_out():
    """ Get the current usdc -> usdt ratio """
    return router.getAmountsOut(
        1 * (10 ** usdc["decimals"]),
        [
            usdc["address"],
            usdt["address"],
        ],
    )[-1] / (10 ** usdt["decimals"])

def get_current_usdc_out():
    """ Get the current usdt -> usdc ratio """
    return router.getAmountsOut(
        1 * (10 ** usdt["decimals"]),
        [
            usdt["address"],
            usdc["address"],
        ],
    )[-1] / (10 ** usdc["decimals"])





def swap_usdt_for_usdc():
    """ Swap USDT for USDC. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForTokens(
        # amount of USDT to put in (includes slippage)
        usdt_contract.balanceOf(user.address) * SWAP_PERCENT * (1 + MAX_SLIPPAGE),
        # minimum amount of USDC to get out
        usdt_contract.balanceOf(user.address) * SWAP_PERCENT,
        # address path (from USDT to USDC)
        [usdt["address"], usdc["address"]],
        # address to send usdc tokens to
        user.address,
        # deadline
        1000*int(time.time()+30),
        # the maximum amount of WETH that will be consumed by the swap (this ensures that WETH cannot be over-consumed during the transaction). you calculate this value like this: 
        {'from':user.address, 'value': user.balance() * SWAP_PERCENT * (1 + MAX_SLIPPAGE)}
    )

def swap_usdc_for_usdt():
    """ Swap USDC for USDT. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForTokens(
        # amount of USDT to put in (includes slippage)
        usdc_contract.balanceOf(user.address) * SWAP_PERCENT * (1 + MAX_SLIPPAGE),
        # minimum amount of USDC to get out
        usdc_contract.balanceOf(user.address) * SWAP_PERCENT,
        # address path (from USDC to USDT)
        [usdc["address"], usdt["address"]],
        # address to send usdc tokens to
        user.address,
        # deadline
        1000*int(time.time()+30),
        # the maximum amount of WETH that will be consumed by the swap (this ensures that WETH cannot be over-consumed during the transaction). you calculate this value like this: 
        {'from':user.address}
    )





def swap_usdc_for_usdt():
    """ Swap USDC for USDT. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForTokens(
        # amount of USDC in (includes slippage)
        usdc_contract.balanceOf(user.address) * SWAP_PERCENT,
        # 300000000 * 0.1 = 30,000,000

        # minimum amount of USDT to get out
        usdc_contract.balanceOf(user.address) * SWAP_PERCENT * (1 - MAX_SLIPPAGE),
        # 300000000 * 0.1 * (1 - 0.01) = 29,700,000

        # address path (from usdc to WETH)
        [usdc["address"], usdt["address"]],

        # address to send WETH tokens to
        user.address,

        # deadline
        1000*int(time.time()+30),

        # 
        {'from':user.address}
    )


# Confirm approvals for tokens
print("\nChecking approvals:")

if get_approval(usdc_contract, router, user):
    print(f"• {usdc['symbol']} OK\n")
else:
    token_approve(usdc_contract, router)

if get_approval(usdt_contract, router, user):
    print(f"• {usdt['symbol']} OK\n")
else:
    token_approve(usdt_contract, router)

# print current account value for reference
print_current_account_value()

# Initialize as 0 so that the arb percentage prints on initial program load
last_usdt_out = 0
last_usdc_out = 0


#
#  *** THE LOOP ***
#
print('\nStarting the loop...\n')
while True:

    try:
        # See how much you can get out with a trade on either side
        current_usdt_out = get_current_usdt_out() 
        current_usdc_out = get_current_usdc_out() 

        # Print current market conditions on initial program load and whenever the arb percentage changes
        if (current_usdt_out != last_usdt_out or current_usdc_out != last_usdc_out):
            print(
                f"{datetime.datetime.now().strftime('%D')} | {datetime.datetime.now().strftime('%H:%M:%S')} | USDT Out: ${round(current_usdt_out, 4)} | USDC Out: ${round(current_usdc_out, 4)}"
                )
            last_usdt_out = current_usdt_out
            last_usdc_out = current_usdc_out

        
        # If you can get more USDT out, get it out.
        if (current_usdt_out > TRADE_THRESHOLD and usdc_contract.balanceOf(user.address) / 10**usdc["decimals"] > 50):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: you can get {round(current_usdt_out, 4)} USDT for 1 USDC. Therefore: swap USDC for USDT."
                )

            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break

            try:
                swap_usdc_for_usdt()
                print("\nTrade successful!\n")
                print_current_account_value()
                log_transaction()

            except Exception as e:
                print(f"Exception: {e}")

        # If you can get more USDC out, get it out.
        elif (current_usdc_out > TRADE_THRESHOLD and usdt_contract.balanceOf(user.address) / 10**usdt["decimals"] > 50):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: you can get {round(current_usdc_out, 4)} USDC for 1 USDT. Therefore: swap USDC for USDT."
                )
            
            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break
            
            try:
                swap_usdt_for_usdc()
                print("\nTrade successful!\n")
                print_current_account_value()
                log_transaction()

            except Exception as e:
                print(f"Exception: {e}")


        if ONE_SHOT:
            print(f"Breaking the loop because ONE_SHOT = {ONE_SHOT}.")
            break


    except Exception as e:
            print(f"Error: {e} \n\nWill wait {ERROR_SLEEP_TIME} seconds and try again...")
            time.sleep(ERROR_SLEEP_TIME)
            continue

    time.sleep(LOOP_TIME)


