import os
from os.path import exists
import csv
import sys
import time
import datetime
from decimal import Decimal
from brownie import *
 

# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')

ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')
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
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
usdc_contract = Contract.from_explorer('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')

# sushi router contract
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')

# Price contracts / APIs
weth_price = Contract.from_explorer('0x639fe6ab55c921f74e7fac1ee960c0b6293ba612')
usdc_price = Contract.from_explorer('0x50834f3163758fcc1df9973b6e91f0f0f0434ad3')


# Create dictionaries for our tokens
usdc = {
    "address": usdc_contract.address,
    "symbol": usdc_contract.symbol(),
    "decimals": usdc_contract.decimals(),
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
# If the current_pool_price_discount rate goes above this number: swap USDC for WETH
BUY_WETH_THRESHOLD = 0.10
# If the current_pool_price_discount rate falls below this number: swap WETH for USDC
SELL_WETH_THRESHOLD = -0.50
# What percentage of token or WETH balance do you want to swap when a trade opportunity becomes available?
SWAP_PERCENT = 0.97 # Keep it below 100%, otherwise there will be no ETH left over to pay for gas
# max slippage
MAX_SLIPPAGE = 0.005
# How often to run the main loop (in seconds)
LOOP_TIME = 3
# How long to wait on an error
ERROR_SLEEP_TIME = 60


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
    chainlink_price_of_usdc_in_usd = usdc_price.latestRoundData()[1] / 10**usdc_price.decimals()

    # calculate the dollar values based on current balances
    account_value_of_weth_in_usd = (user.balance() / 10**weth["decimals"]) * chainlink_price_of_weth_in_usd
    account_value_of_usdc_in_usd = (usdc_contract.balanceOf(user.address) / 10**usdc['decimals']) * chainlink_price_of_usdc_in_usd
    account_usd_value = account_value_of_usdc_in_usd + account_value_of_weth_in_usd
    account_eth_value = (user.balance() / 10**weth['decimals']) + (account_value_of_usdc_in_usd / chainlink_price_of_weth_in_usd )

    print(
    f"------------------------ \
        \n{datetime.datetime.now().strftime('%D')} @ {datetime.datetime.now().strftime('%H:%M:%S')} \
        \nCurrent account value:\n \
        \nWETH: {round(user.balance() / 10**weth['decimals'],3)} @ ${round(chainlink_price_of_weth_in_usd,2)}: ${round(account_value_of_weth_in_usd,2)} \
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
        chainlink_price_of_usdc_in_usd = usdc_price.latestRoundData()[1] / 10**weth_price.decimals()

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',
            'eth_balance',
            'eth_price',
            'eth_value_in_usd',
            'usdc_balance',
            'usdc_price',
            'usdc_value_in_usd',
            'total_value_in_usd',
            'total_value_in_eth',
            'current_weth_out',
            'curent_usdc_out'
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = account_name
        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_eth_balance * csv_eth_price
        csv_usdc_balance = usdc_contract.balanceOf(user.address) / 10**usdc['decimals']
        csv_usdc_price = chainlink_price_of_usdc_in_usd
        csv_usdc_value_in_usd = csv_usdc_balance * csv_usdc_price
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_usdc_value_in_usd
        csv_total_value_in_eth = csv_eth_balance + (csv_usdc_value_in_usd / csv_eth_price)


        # Write the CSV file
        filename = 'logs/trade_usdc_weth_dollar_arb.csv'
        row = [
            csv_date, 
            csv_time, 
            csv_account_name, 
            csv_eth_balance, 
            csv_eth_price, 
            csv_eth_value_in_usd,
            csv_usdc_balance,
            csv_usdc_price,
            csv_usdc_value_in_usd,
            csv_total_value_in_usd,
            csv_total_value_in_eth,
            current_weth_out,
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



def get_current_weth_out():
    """ Get the current usdc -> weth ratio """
    return router.getAmountsOut(
        1 * (10 ** usdc["decimals"]),
        [
            usdc["address"],
            weth["address"],
        ],
    )[-1] / (10 ** weth["decimals"])

def get_current_usdc_out():
    """ Get the current weth -> usdc ratio """
    return router.getAmountsOut(
        1 * (10 ** weth["decimals"]),
        [
            weth["address"],
            usdc["address"],
        ],
    )[-1] / (10 ** usdc["decimals"])




def swap_weth_for_usdc():
    """ Swap WETH for USDC. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapETHForExactTokens(
        # amount of usdc to get out
        (user.balance() * SWAP_PERCENT / 10**weth["decimals"]) * current_usdc_out * 10**usdc["decimals"],
        # address path (from WETH to usdc)
        [weth["address"], usdc["address"]],
        # address to send usdc tokens to
        user.address,
        # deadline
        1000*int(time.time()+30),
        # the maximum amount of WETH that will be consumed by the swap (this ensures that WETH cannot be over-consumed during the transaction). you calculate this value like this: 
        {'from':user.address, 'value': user.balance() * SWAP_PERCENT * (1 + MAX_SLIPPAGE)}
    )

def swap_usdc_for_weth():
    """ Swap USDC for WETH. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForETH(
        # amount of usdc in (includes slippage)
        (usdc_contract.balanceOf(user.address) * SWAP_PERCENT * (1 + MAX_SLIPPAGE)),

        # minimum amount of WETH to get out
        (usdc_contract.balanceOf(user.address) * SWAP_PERCENT / 10**usdc["decimals"]) * current_weth_out * 10**weth["decimals"],

        # address path (from usdc to WETH)
        [usdc["address"], weth["address"]],

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

# print current account value for reference
print_current_account_value()

# Initialize as 0 so that the arb percentage prints on initial program load
last_pool_price_discount_rate = 0



#
#  *** THE LOOP ***
#
print('\nStarting the loop...\n')
while True:

    try:
        # See how much you can get out with a trade on either side
        current_weth_out = get_current_weth_out() # 0.000801646549562477
        current_usdc_out = get_current_usdc_out() # 1239.605049

        # Find the market prices for the assets
        weth_market_price = weth_price.latestRoundData()[1] / 10**weth_price.decimals() # 1242.84
        usdc_market_price = usdc_price.latestRoundData()[1] / 10**weth_price.decimals() 

        # Calculate the cost of pulling one unit out of the pool
        weth_pool_price = 1 / current_weth_out * usdc_market_price # 1 / 0.000801646549562477 = 1247.4325505995
        usdc_pool_price = 1 / current_usdc_out * usdc_market_price # 1 / 1239.605049 = 0.0008067085567

        # Calculate the pool discount (or premium)
        weth_market_price_minus_pool_price = weth_market_price - weth_pool_price # 1242.84 - 1247.4325505995 = -4.5925505995
        
        # Calculate the arbitrage percentage
        current_pool_price_discount_rate = weth_market_price_minus_pool_price / weth_market_price * 100 # -4.5925505995 / 1242.84 * 100 = -0.3695206623
        
        # Print current market conditions on initial program load and whenever the arb percentage changes
        if (current_pool_price_discount_rate != last_pool_price_discount_rate):
            print(
                f"{datetime.datetime.now().strftime('%D')} | {datetime.datetime.now().strftime('%H:%M:%S')} | MKT: ${round(weth_market_price, 2)} | POOL: ${round(weth_pool_price, 2)} | ${round(weth_market_price_minus_pool_price, 2)} | {round(current_pool_price_discount_rate, 3)}%"
                )
            last_pool_price_discount_rate = current_pool_price_discount_rate

        # If ETH is cheaper in the pool than on the market: Buy ETH in the pool
        if (current_pool_price_discount_rate > BUY_WETH_THRESHOLD and usdc_contract.balanceOf(user.address) / 10**usdc["decimals"] > 200):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: the price of ETH in the pool (${round(weth_pool_price,2)}) is {round(current_pool_price_discount_rate,2)}% less than the market price (${round(weth_market_price, 2)}).\n \
                \nTherefore: swap WETH for USDC."
                )

            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break

            # If you have usdc to trade...
            print('\nYou have enough usdc in your wallet. Attempting a trade...\n')

            try:
                swap_usdc_for_weth()
                print("\nTrade successful!\n")
                print_current_account_value()
                log_transaction()

            except Exception as e:
                print(f"Exception: {e}")
        
        elif (current_pool_price_discount_rate < SELL_WETH_THRESHOLD and user.balance() / 10**weth["decimals"] > 0.2):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: the price of ETH in the pool (${round(weth_pool_price,2)}) is {-1 * round(current_pool_price_discount_rate,2)}% more than the market price (${round(weth_market_price, 2)}).\n \
                \nTherefore: swap WETH for USDC."
                )
            
            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break
            

            # If you have WETH to trade...
            # else: 
            print('\nYou have enough WETH in your wallet. Attempting a trade...\n')

            try:
                swap_weth_for_usdc()
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


