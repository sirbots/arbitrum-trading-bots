

# Warning: I don't think this works because the market value of RDPX is 1:1 related with the market price of ETH, or something like that. Basically, the ratio or discount never changes!





import os
from os.path import exists
import csv
import sys
import time
import datetime
from brownie import *
from pycoingecko import CoinGeckoAPI


# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

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

sys.exit("Cancelling. This bot does not work because there's no market price for RDPX...")

# Load the token and router contracts
print('\nAccount and network loaded. Loading contracts:')

# token contracts
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
rdpx_contract = Contract.from_explorer('0x32Eb7902D4134bf98A28b963D26de779AF92A212')

# sushi router contract
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')

# Price contracts / APIs
weth_price = Contract.from_explorer('0x639fe6ab55c921f74e7fac1ee960c0b6293ba612')
cg = CoinGeckoAPI()



# Create dictionaries for our tokens
rdpx = {
    "address": rdpx_contract.address,
    "symbol": rdpx_contract.symbol(),
    "decimals": rdpx_contract.decimals(),
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
# SWAP_THRESHOLD = 0.01
# What percentage of token or WETH balance do you want to swap when a trade opportunity becomes available?
SWAP_PERCENT = 0.50
# max slippage
MAX_SLIPPAGE = 0.001
# How often to run the main loop (in seconds)
LOOP_TIME = 7.0
# How long to wait on an error
ERROR_SLEEP_TIME = 30


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
    coingecko_price_of_rdpx_in_usd = cg.get_price(ids='dopex-rebate-token', vs_currencies='usd')['dopex-rebate-token']['usd']

    # calculate the dollar values based on current balances
    account_value_of_weth_in_usd = (user.balance() / 10**weth["decimals"]) * chainlink_price_of_weth_in_usd
    account_value_of_rdpx_in_usd = (rdpx_contract.balanceOf(user.address) / 10**rdpx['decimals']) * coingecko_price_of_rdpx_in_usd
    account_usd_value = account_value_of_rdpx_in_usd + account_value_of_weth_in_usd
    account_eth_value = (user.balance() / 10**weth['decimals']) + (account_value_of_rdpx_in_usd / chainlink_price_of_weth_in_usd )

    print(
    f"------------------------ \
        \n{datetime.datetime.now().strftime('%D')} @ {datetime.datetime.now().strftime('%H:%M:%S')} \
        \nCurrent account value:\n \
        \nWETH: {round(user.balance() / 10**weth['decimals'],3)} @ ${round(chainlink_price_of_weth_in_usd,2)}: ${round(account_value_of_weth_in_usd,2)} \
        \nRDPX: {round(rdpx_contract.balanceOf(user.address) / 10**rdpx['decimals'],3)} @ ${round(coingecko_price_of_rdpx_in_usd, 2)}: ${round(account_value_of_rdpx_in_usd, 2)} \
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
        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_eth_balance * csv_eth_price
        csv_rdpx_balance = rdpx_contract.balanceOf(user.address) / 10**rdpx['decimals']
        csv_rdpx_price = coingecko_price_of_rdpx_in_usd
        csv_rdpx_value_in_usd = csv_rdpx_balance * csv_rdpx_price
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_rdpx_value_in_usd
        csv_total_value_in_eth = csv_eth_balance + (csv_rdpx_value_in_usd / csv_eth_price)


        # Write the CSV file
        filename = 'logs/trade_rdpx_weth_dollar_arb.csv'
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
            current_weth_out,
            current_rdpx_out 
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
    """ Get the current rdpx -> weth ratio """
    return router.getAmountsOut(
        1 * (10 ** rdpx["decimals"]),
        [
            rdpx["address"],
            weth["address"],
        ],
    )[-1] / (10 ** weth["decimals"])

def get_current_rdpx_out():
    """ Get the current weth -> rdpx ratio """
    return router.getAmountsOut(
        1 * (10 ** weth["decimals"]),
        [
            weth["address"],
            rdpx["address"],
        ],
    )[-1] / (10 ** rdpx["decimals"])



def swap_weth_for_rdpx():
    """ Swap WETH for RDPX. """

    print(f"*** EXECUTING SWAP ***\n")
    
    router.swapETHForExactTokens(
        # amount of RDPX to get out
        (user.balance() * SWAP_PERCENT) * (10**rdpx["decimals"]) * ( current_rdpx_out / 10**rdpx["decimals"] ),
        # address path (from WETH to RDPX)
        [weth["address"], rdpx["address"]],
        # address to send RDPX tokens to
        user.address,
        # deadline
        1000*int(time.time()+30),
        # the maximum amount of WETH that will be consumed by the swap (this ensures that WETH cannot be over-consumed during the transaction). you calculate this value like this: 
        {'from':user.address, 'value': user.balance() * SWAP_PERCENT * (1 + MAX_SLIPPAGE)}
    )

def swap_rdpx_for_weth():
    """ Swap RDPX for WETH. """

    print(f"*** EXECUTING SWAP ***\n")

    router.swapExactTokensForETH(
        # amount of RDPX in (includes slippage)
        (rdpx_contract.balanceOf(user.address) * SWAP_PERCENT * (1 + MAX_SLIPPAGE)),

        # minimum amount of WETH to get out
        (rdpx_contract.balanceOf(user.address) * SWAP_PERCENT) * (10**weth["decimals"]) * ( current_weth_out / 10**weth["decimals"] ),

        # address path (from RDPX to WETH)
        [rdpx["address"], weth["address"]],

        # address to send WETH tokens to
        user.address,

        # deadline
        1000*int(time.time()+30),

        # 
        {'from':user.address}
    )

# Confirm approvals for tokens
print("\nChecking approvals:")

if get_approval(rdpx_contract, router, user):
    print(f"• {rdpx['symbol']} OK\n")
else:
    token_approve(rdpx_contract, router)

# print current account value for reference
print_current_account_value()

# Initialize as 0 so that the arb percentage prints on initial program load
last_arb_percentage_weth = 0



#
#  *** THE LOOP ***
#
print('\nStarting the loop...\n')
while True:

    try:
        # See how much you can get out with a trade on either side
        current_weth_out = get_current_weth_out()
        current_rdpx_out = get_current_rdpx_out()

        # Find the market prices for the assets
        weth_market_price = weth_price.latestRoundData()[1] / 10**weth_price.decimals() # 1243.52

        # The thing about the RDPX price feed from CoinGecko is that it's just using the Sushi RDPX/WETH pool. So it doesn't make sense for us to use that because it would be redundant. So let's try running this bot with just the WETH market price. We'll buy WETH when it's cheaper in the pool and sell it when it's more expensive.
        # rdpx_usd_price = cg.get_price(ids='dopex-rebate-token', vs_currencies='usd')['dopex-rebate-token']['usd']
        rdpx_usd_price = 1 * weth_market_price / current_rdpx_out # 1 * 1243.52 / 83.1422170235035 = 14.9565412677

        # The cost of getting 1 ETH out of the pool:
        # 1 / 0.011925 * 14.7192732 = $1,234.32
        weth_pool_price = 1 / current_weth_out * rdpx_usd_price # 1 / 0.011950956366669855 * 14.9565412677 = 1251.4932536623 

        # Calculate the cost of getting 1 RDPX out of the pool:
        # 1 / 83.31662 * 1226.36 = $14.7192732
        #value_of_rdpx_in_pool = 1 / current_rdpx_out * weth_market_price

        # Calculate the pool discount (or premium)
        weth_pool_discount = weth_market_price - weth_pool_price # 1243.52 - 1251.4932536623 = -7.9732536623
        
        # Calculate the arbitrage percentage
        current_arb_percentage_weth = weth_pool_discount / weth_market_price * 100 # -7.9732536623 / 1243.52 * 100 = -0.6406001328
        
        # Print current market conditions on initial program load and whenever the arb percentage changes
        # TO DO: fix this, because it's always comparing to 0
        if (current_arb_percentage_weth != last_arb_percentage_weth):

            print(
                f"{datetime.datetime.now().strftime('%D')} | {datetime.datetime.now().strftime('%H:%M:%S')} | MKT: ${round(weth_market_price, 2)} | POOL: ${round(weth_pool_price, 2)} | ${round(weth_pool_discount, 2)} | {round(current_arb_percentage_weth, 5)}% | Current WETH out: {current_weth_out} | Current RDPX out: {current_rdpx_out}"
                )
            
            last_arb_percentage_weth = current_arb_percentage_weth

            # An alternate formatting option for the market conditions:
            # print(
            #     f"\n---------------------------- \
            #     \n{datetime.datetime.now().strftime('%D')} @ {datetime.datetime.now().strftime('%H:%M:%S')}\n \
            #     \nWETH Market Price: ${round(weth_market_price, 2)} \
            #     \nWETH Pool Price: ${round(weth_pool_price, 2)} \
            #     \nPool Discount: ${round(weth_pool_discount, 2)}\n \
            #     \nArbitrage % (before fees): {round(current_arb_percentage_weth, 2)}%\n \
            #     \n----------------------------\n"
            #     )
    

        # The minimum price discount required before making a trade (in percentage points)
        MINIMUM_DISCOUNT = 0.5


        # If ETH is cheaper in the pool than on the market: Buy ETH in the pool
        if (current_arb_percentage_weth > MINIMUM_DISCOUNT and rdpx_contract.balanceOf(user.address) / 10**rdpx["decimals"] > 2):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: the price of ETH in the pool (${round(weth_pool_price,2)}) is {round(current_arb_percentage_weth,2)}% less than the market price (${round(weth_market_price, 2)}).\n \
                \nTherefore: swap WETH for RDPX."
                )

            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break

            # If there's no RDPX in your wallet, then no trade happens but we alert the console
            # if (rdpx_contract.balanceOf(user.address) / 10**rdpx["decimals"] == 0):
            #     print('\nYour RDPX balance is 0. Cannot initiate a trade right now.')

            # If you have RDPX to trade...
            # else: 
            print('\nYou have enough RDPX in your wallet. Attempting a trade...\n')

            try:
                swap_rdpx_for_weth()
                print("\nTrade successful!\n")
                print_current_account_value()
                log_transaction()

            except Exception as e:
                print(f"Exception: {e}")

        elif (current_arb_percentage_weth < -1 * MINIMUM_DISCOUNT and user.balance() / 10**weth["decimals"] > 0.1):
            # Print the trade opportunity
            print(
                f"\nTrade opportunity detected: the price of ETH in the pool (${round(weth_pool_price,2)}) is {-1 * round(current_arb_percentage_weth,2)}% more than the market price (${round(weth_market_price, 2)}).\n \
                \nTherefore: swap WETH for RDPX."
                )
            
            # break if it's a dry run
            if DRY_RUN:
                print(f"*** Dry run enabled. Not initiating trade. ***")
                break
            
            # If there's no WETH in your wallet, then no trade happens but we alert the console
            # if (user.balance() / 10**weth["decimals"] > 0):
            #     print('\nYour WETH balance is 0. Cannot initiate a trade right now.')


            # If you have WETH to trade...
            # else: 
            print('\nYou have enough WETH in your wallet. Attempting a trade...\n')

            try:
                swap_weth_for_rdpx()
                print("\nTrade successful!\n")
                print_current_account_value()
                log_transaction()

            except Exception as e:
                print(f"Exception: {e}")


        if ONE_SHOT:
            print(f"Breaking the loop because ONE_SHOT = {ONE_SHOT}.")
            break


    except Exception as e:
            print(f"Error: {e} \n\nWill wait 60 seconds and try again...")
            time.sleep(ERROR_SLEEP_TIME)
            continue

    time.sleep(LOOP_TIME)


