import os
import csv
import sys
import time
import datetime
from decimal import Decimal
from brownie import *


# Network & account config
NETWORK = 'arbitrum-main'
ACCOUNT_NAME = os.getenv('ACCOUNT_NAME') 
PASSWORD = os.getenv('ACCOUNT_PW')
LOG_FILE = 'logs/RENAME_ME.csv'

# Contract addresses  
SUSHI_ROUTER_CONTRACT_ADDRESS = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"

SUSHI_WETH_USDC_POOL_CONTRACT_ADDRESS = "0x905dfCD5649217c42684f23958568e533C711Aa3" # Sushi WETH-USDC pool
SUSHI_WETH_USDT_POOL_CONTRACT_ADDRESS = "0xCB0E5bFa72bBb4d16AB5aA0c60601c438F04b4ad" # Sushi WETH-USDT pool
SUSHI_WETH_MIM_POOL_CONTRACT_ADDRESS = "0xb6DD51D5425861C808Fd60827Ab6CFBfFE604959" # Sushi WETH-MIM pool
SUSHI_WETH_DAI_POOL_CONTRACT_ADDRESS = "0x692a0B300366D1042679397e40f3d2cb4b8F7D30" # Sushi WETH-DAI pool

WETH_CONTRACT_ADDRESS = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC_CONTRACT_ADDRESS = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"
USDT_CONTRACT_ADDRESS = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
MIM_CONTRACT_ADDRESS = "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A"
DAI_CONTRACT_ADDRESS = "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"

CHAINLINK_WETH_PRICE_ADDRESS = "0x639fe6ab55c921f74e7fac1ee960c0b6293ba612"

# Helper values
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
# TO DO: set up a PERCENT constant and then use it for the thresholds below

# WETH -> USDC swap targets
# a zero value will trigger a swap when the ratio matches weth_market_price exactly
# a negative value will trigger a swap when the rate is below weth_market_price
# a positive value will trigger a swap when the rate is above weth_market_price
# THRESHOLD_WETH_TO_USDC = Decimal("0.02")
# If the current_pool_price_discount rate falls below this number: swap WETH for USDC
SELL_WETH_THRESHOLD = Decimal("0.002") 

# USDC -> WETH swap targets
# a positive value will trigger a (USDC -> WETH) swap when the ratio is above weth_market_price
#THRESHOLD_USDC_TO_WETH = Decimal("0.05")
# If the current_pool_price_discount rate goes above this number: swap USDC for WETH
BUY_WETH_THRESHOLD = Decimal("-0.005")


SLIPPAGE = Decimal("0.001")  # tolerated slippage in swap price (0.1%)


# Simulate swaps and approvals
DRY_RUN = True
# Quit after the first successful trade
ONE_SHOT = False
# How often to run the main loop (in seconds)
LOOP_TIME = 2.0
# How long to wait on an error
ERROR_SLEEP_TIME = 60


def main():

    global sushi_router
    global weth_usdc_lp
    global weth
    global usdc
    global usdt
    global mim
    global dai
    global user
    global weth_price

    try:
        network.connect(NETWORK)
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

    print("\nContracts loaded:")
    weth_contract = contract_load(WETH_CONTRACT_ADDRESS, "Arbitrum Token: WETH")
    usdc_contract = contract_load(USDC_CONTRACT_ADDRESS, "Arbitrum Token: USDC")
    usdt_contract = contract_load(USDT_CONTRACT_ADDRESS, "Arbitrum Token: USDT")
    mim_contract = contract_load(MIM_CONTRACT_ADDRESS, "Arbitrum Token: MIM")
    dai_contract = contract_load(DAI_CONTRACT_ADDRESS, "Arbitrum Token: DAI")

    sushi_router = contract_load(
        SUSHI_ROUTER_CONTRACT_ADDRESS, "Sushi: Router"
    )
    weth_usdc_lp = contract_load(
        SUSHI_WETH_USDC_POOL_CONTRACT_ADDRESS, "Sushi LP: WETH-USDC"
    )
    weth_usdt_lp = contract_load(
        SUSHI_WETH_USDT_POOL_CONTRACT_ADDRESS, "Sushi LP: WETH-USDT"
    )
    weth_mim_lp = contract_load(
        SUSHI_WETH_MIM_POOL_CONTRACT_ADDRESS, "Sushi LP: WETH-MIM"
    )
    weth_dai_lp = contract_load(
        SUSHI_WETH_DAI_POOL_CONTRACT_ADDRESS, "Sushi LP: WETH-DAI"
    )

    weth_price = contract_load(CHAINLINK_WETH_PRICE_ADDRESS, "WETH Chainlink Price")

    weth = {
        "address": WETH_CONTRACT_ADDRESS,
        "contract": weth_contract,
        "name": None,
        "symbol": None,
        "balance": None,
        "decimals": None,
    }
    usdc = {
        "address": USDC_CONTRACT_ADDRESS,
        "contract": usdc_contract,
        "name": None,
        "symbol": None,
        "balance": None,
        "decimals": None,
    }
    usdt = {
        "address": USDT_CONTRACT_ADDRESS,
        "contract": usdt_contract,
        "name": None,
        "symbol": None,
        "balance": None,
        "decimals": None,
    }
    mim = {
        "address": MIM_CONTRACT_ADDRESS,
        "contract": mim_contract,
        "name": None,
        "symbol": None,
        "balance": None,
        "decimals": None,
    }
    dai = {
        "address": DAI_CONTRACT_ADDRESS,
        "contract": dai_contract,
        "name": None,
        "symbol": None,
        "balance": None,
        "decimals": None,
    }

    weth["symbol"] = get_token_symbol(weth["contract"])
    weth["name"] = get_token_name(weth["contract"])
    weth["balance"] = get_token_balance(weth_contract, user)
    weth["decimals"] = get_token_decimals(weth_contract)

    usdc["symbol"] = get_token_symbol(usdc["contract"])
    usdc["name"] = get_token_name(usdc["contract"])
    usdc["balance"] = get_token_balance(usdc_contract, user)
    usdc["decimals"] = get_token_decimals(usdc_contract)

    usdt["symbol"] = get_token_symbol(usdt["contract"])
    usdt["name"] = get_token_name(usdt["contract"])
    usdt["balance"] = get_token_balance(usdt_contract, user)
    usdt["decimals"] = get_token_decimals(usdt_contract)
    
    mim["symbol"] = get_token_symbol(mim["contract"])
    mim["name"] = get_token_name(mim["contract"])
    mim["balance"] = get_token_balance(mim_contract, user)
    mim["decimals"] = get_token_decimals(mim_contract)

    dai["symbol"] = get_token_symbol(dai["contract"])
    dai["name"] = get_token_name(dai["contract"])
    dai["balance"] = get_token_balance(dai_contract, user)
    dai["decimals"] = get_token_decimals(dai_contract)

    if (weth["balance"] == 0) and (usdc["balance"] == 0):
        sys.exit("No tokens found!")

    # Confirm approvals for tokens
    print("\nChecking Approvals:")

    # Approve weth
    if get_approval(weth["contract"], sushi_router, user):
        print(f"• {weth['symbol']} OK")
    else:
        token_approve(weth["contract"], sushi_router)

    # Approve usdc
    if get_approval(usdc["contract"], sushi_router, user):
        print(f"• {usdc['symbol']} OK")
    else:
        token_approve(usdc["contract"], sushi_router)

    # Approve usdt
    if get_approval(usdt["contract"], sushi_router, user):
        print(f"• {usdt['symbol']} OK")
    else:
        token_approve(usdt["contract"], sushi_router)

    # Approve mim
    if get_approval(mim["contract"], sushi_router, user):
        print(f"• {mim['symbol']} OK")
    else:
        token_approve(mim["contract"], sushi_router)
    
    # Approve dai
    if get_approval(dai["contract"], sushi_router, user):
        print(f"• {dai['symbol']} OK")
    else:
        token_approve(dai["contract"], sushi_router)

    # get the ETH market price (weth_market_price replaces the base_staking_rate in the tutorial example)
    try:
        weth_market_price = Decimal(weth_price.latestRoundData()[1] / 10**weth_price.decimals() ) # 1162.91
    except FileNotFoundError:
        sys.exit(
            "Cannot load the base Abracadabra WETH/USDC staking rate. Run `python3 abra_rate.py` and try again."
        )

    
    try:
        # Find the market prices for WETH
        weth_market_price = Decimal(weth_price.latestRoundData()[1] / 10**weth_price.decimals()) # 1168.44
    except Exception as e:
        print(f"Error updating price: {e}")

 
    balance_refresh = True
    last_arb_profit = 0

    #
    # Start of arbitrage loop
    #
    while True:

        loop_start = time.time()

        try:
            if balance_refresh:
                time.sleep(3)
                
                print_current_account_balance()
                balance_refresh = False

            
            # The quantity of stablecoins in. This will determine the price of our ETH for now.
            # TODO: refactor this so that it calculates an amount based on the account balance or uses get_tokens_in_for_ratio_out() to calculate the amount in
            amount_in_base = 1_000

            usdc_in = Decimal(amount_in_base * 10**usdc['decimals'])
            usdt_in = Decimal(amount_in_base * 10**usdt['decimals'])
            mim_in = Decimal(amount_in_base * 10**mim['decimals'])
            dai_in = Decimal(amount_in_base * 10**dai['decimals'])
            
            
            # Get price of WETH in the USDC pool
            # Get the pool reserves
            x0, y0 = weth_usdc_lp.getReserves.call()[0:2]        
            # calculate WETH output from USDC input
            weth_out_from_usdc_pool = get_tokens_out_for_tokens_in(pool_reserves_token0=x0, pool_reserves_token1=y0, token0_decimals = weth["decimals"], token1_decimals = usdc["decimals"], quantity_token1_in=usdc_in, fee=Decimal("0.003"),)
            # Calculate the implied price of WETH in the pool and push it to the stablecoin's dictionary
            usdc["pool_price_of_weth"] = (usdc_in / 10**usdc["decimals"]) / ( weth_out_from_usdc_pool / 10**weth["decimals"] )
            
            
            # Get price of WETH in the USDT pool
            # Get the pool reserves
            x0, y0 = weth_usdt_lp.getReserves.call()[0:2]
            # calculate WETH output from USDT input
            weth_out_from_usdt_pool = get_tokens_out_for_tokens_in(pool_reserves_token0=x0, pool_reserves_token1=y0, token0_decimals = weth["decimals"], token1_decimals = usdt["decimals"], quantity_token1_in=usdt_in, fee=Decimal("0.003"),)
            # Calculate the implied price of WETH in the pool and push it to the stablecoin's dictionary
            usdt["pool_price_of_weth"] = (usdt_in / 10**usdt["decimals"]) / ( weth_out_from_usdt_pool / 10**weth["decimals"] )
            

            # Get price of WETH in the MIM pool
            # Get the pool reserves
            x0, y0 = weth_mim_lp.getReserves.call()[0:2]
            # calculate WETH output from MIM input
            weth_out_from_mim_pool = get_tokens_out_for_tokens_in(pool_reserves_token0=x0, pool_reserves_token1=y0, token0_decimals = weth["decimals"], token1_decimals = mim["decimals"], quantity_token1_in=mim_in, fee=Decimal("0.003"),)
            # Calculate the implied price of WETH in the pool and push it to the stablecoin's dictionary
            mim["pool_price_of_weth"] = (mim_in / 10**mim["decimals"]) / ( weth_out_from_mim_pool / 10**weth["decimals"] )


            # Get price of WETH in the DAI pool
            # Get the pool reserves
            x0, y0 = weth_dai_lp.getReserves.call()[0:2]
            # calculate WETH output from DAI input
            weth_out_from_dai_pool = get_tokens_out_for_tokens_in(pool_reserves_token0=x0, pool_reserves_token1=y0, token0_decimals = weth["decimals"], token1_decimals = dai["decimals"], quantity_token1_in=dai_in, fee=Decimal("0.003"),)
            # Calculate the implied price of WETH in the pool and push it to the stablecoin's dictionary
            dai["pool_price_of_weth"] = (dai_in / 10**dai["decimals"]) / ( weth_out_from_dai_pool / 10**weth["decimals"] )



            # Create a list of stablecoins sorted by their corresponding WETH pool price
            stablecoins_list = [usdc, usdt, mim, dai]
            stablecoins_sorted_by_weth_pool_price = []

            for stablecoin in stablecoins_list:
                stablecoins_sorted_by_weth_pool_price.append([stablecoin["pool_price_of_weth"], stablecoin])
            
            stablecoins_sorted_by_weth_pool_price.sort()

            lowest_priced_stablecoin = stablecoins_sorted_by_weth_pool_price[0]
            highest_priced_stablecoin = stablecoins_sorted_by_weth_pool_price[-1]


            # Calculate the arbitrage opportunity
            weth_price_in_lowest_pool = lowest_priced_stablecoin[0]
            weth_price_in_highest_pool = highest_priced_stablecoin[0]

            current_arb_profit = (amount_in_base / weth_price_in_lowest_pool * weth_price_in_highest_pool) - amount_in_base
            estimated_pool_fees = Decimal(amount_in_base * 0.003 * 2) # amount_in_base * 0.003 pool fee * 2 transactions
            estimated_gas_fees = Decimal("0.60")  # 2 x $0.30
            
            if last_arb_profit != current_arb_profit:
                print(
                    f"{datetime.datetime.now().strftime('%D')} | {datetime.datetime.now().strftime('%H:%M:%S')} | USDC: ${usdc['pool_price_of_weth']:.2f} | USDT: ${usdt['pool_price_of_weth']:.2f} | MIM: ${mim['pool_price_of_weth']:.2f} | DAI: ${dai['pool_price_of_weth']:.2f} | Net: ${(current_arb_profit - estimated_gas_fees - estimated_pool_fees):.2f} "
                )

                last_arb_profit = current_arb_profit


        # If there's an error (most likely a timeout or connection issue), print the error and then sleep for a while.
        except Exception as e:
            print(f"Error: {e} \n\nWill wait {ERROR_SLEEP_TIME} seconds and try again...")
            time.sleep(ERROR_SLEEP_TIME)
            continue
        loop_end = time.time()


        # Control the loop timing more precisely by measuring start and end time and sleeping as needed
        if (loop_end - loop_start) >= LOOP_TIME:
            continue
        else:
            time.sleep(LOOP_TIME - (loop_end - loop_start))
            continue
    #
    # End of arbitrage loop
    #



#
# FUNCTIONS
#
def account_get_balance(account):
    try:
        return account.balance()
    except Exception as e:
        print(f"Exception in account_get_balance: {e}")


def contract_load(address, alias):
    # Attempts to load the saved contract by alias.
    # If not found, fetch from network explorer and set alias.
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract


def get_approval(token, router, user):
    try:
        return token.allowance.call(user, router.address)
    except Exception as e:
        print(f"Exception in get_approval: {e}")
        return False


def get_token_name(token):
    try:
        return token.name.call()
    except Exception as e:
        print(f"Exception in get_token_name: {e}")
        raise


def get_token_symbol(token):
    try:
        return token.symbol.call()
    except Exception as e:
        print(f"Exception in get_token_symbol: {e}")
        raise


def get_token_balance(token, user, protocol_token = False):
    try:
        if protocol_token:
            return user.balance()
        else:
            return token.balanceOf.call(user)
    except Exception as e:
        print(f"Exception in get_token_balance: {e}")
        raise


def get_token_decimals(token):
    try:
        return token.decimals.call()
    except Exception as e:
        print(f"Exception in get_token_decimals: {e}")
        raise


def token_approve(token, router, value="unlimited"):
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


def token_swap(
    token_in_quantity,
    token_in_address,
    token_out_quantity,
    token_out_address,
    router,
):
    if DRY_RUN:
        return True
 
    try:
        router.swapExactTokensForTokens(
            token_in_quantity,
            int(token_out_quantity * (1 - SLIPPAGE)),
            [token_in_address, token_out_address],
            user.address,
            1000 * int(time.time() + 60 * SECOND),
            {"from": user},
        )
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False


def get_tokens_in_for_ratio_out(
    # I modified this function to include decimals because otherwise it was assuming that both coins had the same decimals!
    pool_reserves_token0, # WETH pool reserves
    pool_reserves_token1, # USDC pool reserves
    token0_out=False,    
    token1_out=False,     # True, because we're pulling USDC out 
    token0_decimals = 18,
    token1_decimals = 18,
    token0_per_token1=0,  # 0.0009571667
    fee=Decimal("0.0"),
):
    assert not (token0_out and token1_out)
    assert token0_per_token1

    # token1 input, token0 output
    if token0_out:
        # dy = x0/C - y0/(1-FEE)
        dy = int(
            Decimal(pool_reserves_token0 / 10**token0_decimals) / token0_per_token1 - Decimal(pool_reserves_token1 / 10**token1_decimals) / (1 - fee)
        )
        if dy > 0:
            return dy * 10**token0_decimals
        else:
            return 0

    # token0 input, token1 output
    if token1_out:
        # dx = y0*C - x0/(1-FEE)
        dx = int(
            Decimal(pool_reserves_token1 / 10**token1_decimals) * token0_per_token1 - Decimal(pool_reserves_token0 / 10**token0_decimals) / (1 - fee)
        )
        if dx > 0:
            return dx * 10**token1_decimals
        else:
            return 0


# TODO: make fully generic with one return, instead of labeling 0/1, use in/out
def get_tokens_out_for_tokens_in(
    pool_reserves_token0, # WETH pool reserves
    pool_reserves_token1, # USDC pool reserves
    token0_decimals = 18,
    token1_decimals = 18,
    quantity_token0_in=0, # weth_in (in this example)
    quantity_token1_in=0,
    fee=0,
):
    # fails if two input tokens are passed, or if both are 0
    assert not (quantity_token0_in and quantity_token1_in)
    assert quantity_token0_in or quantity_token1_in

    if quantity_token0_in:
        return (pool_reserves_token1 * quantity_token0_in * (1 - fee)) // (
            pool_reserves_token0 + quantity_token0_in * (1 - fee) / 10**token1_decimals
        )

    if quantity_token1_in:
        return (pool_reserves_token0 * quantity_token1_in * (1 - fee)) // (
            pool_reserves_token1 + quantity_token1_in * (1 - fee) / 10**token0_decimals
        )

def log_transaction():
    """
    Writes account data to a CSV file after a successful trade.
    """
    
    try:
        print('\nLogging transaction...\n')
        
        # get current prices from data feeds
        chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',
            
            'eth_balance',
            'weth_balance',
            'total_eth',
            'eth_price',
            'eth_value_in_usd',

            'usdc_balance',
            'usdt_balance',
            'mim_balance',
            'dai_balance',
            'total_stablecoin_balance',

            'total_value_in_usd',
            'total_value_in_eth',
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = ACCOUNT_NAME

        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_weth_balance = weth["contract"].balanceOf(user.address) / 10**weth['decimals']
        csv_total_eth = csv_eth_balance + csv_weth_balance
        csv_eth_price = chainlink_price_of_weth_in_usd
        csv_eth_value_in_usd = csv_total_eth * csv_eth_price
        
        csv_usdc_balance = usdc["contract"].balanceOf(user.address) / 10**usdc['decimals']
        csv_usdt_balance = usdt["contract"].balanceOf(user.address) / 10**usdt['decimals']
        csv_mim_balance = mim["contract"].balanceOf(user.address) / 10**mim['decimals']
        csv_dai_balance = dai["contract"].balanceOf(user.address) / 10**dai['decimals']
        csv_total_stablecoin_balance = csv_usdc_balance + csv_usdt_balance + csv_mim_balance + csv_dai_balance
        
        csv_total_value_in_usd = csv_eth_value_in_usd + csv_total_stablecoin_balance
        csv_total_value_in_eth = csv_total_eth + (csv_total_stablecoin_balance / csv_eth_price)

        # Write the CSV file
        
        row = [
            csv_date,
            csv_time,
            csv_account_name,

            csv_eth_balance,
            csv_weth_balance,
            csv_total_eth,
            csv_eth_price, 
            csv_eth_value_in_usd,

            csv_usdc_balance,
            csv_usdt_balance,
            csv_mim_balance,
            csv_dai_balance,
            csv_total_stablecoin_balance,

            csv_total_value_in_usd,
            csv_total_value_in_eth,
            ]

        # Create a blank CSV file with header rows if one does not already exist
        if (not exists(LOG_FILE)):
            with open(LOG_FILE, 'w') as csvfile:
                # create a csv writer object
                csvwriter = csv.writer(csvfile)

                # append the new row
                csvwriter.writerow(headers)

        # Open the CSV file and append the new row of data
        with open(LOG_FILE, 'a') as csvfile:
            # create a csv writer object
            csvwriter = csv.writer(csvfile)

            # append the new row
            csvwriter.writerow(row)

    except Exception as e:
        print(f"Failed to log transaction with error: {e}")


def print_current_account_balance():
    """
    Print the current account balance in USD.
    """

    # get current prices from data feeds
    chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()

    # calculate the dollar values based on current balances
    eth_balance = user.balance() / 10**weth['decimals']
    weth_balance = weth['contract'].balanceOf(user.address) / 10**weth['decimals']
    total_eth = eth_balance + weth_balance
    account_value_of_eth_in_usd = total_eth * chainlink_price_of_weth_in_usd
    
    usdc_balance = usdc['contract'].balanceOf(user.address) / 10**usdc['decimals']
    usdt_balance = usdt['contract'].balanceOf(user.address) / 10**usdt['decimals']
    dai_balance = dai['contract'].balanceOf(user.address) / 10**dai['decimals']
    mim_balance = mim['contract'].balanceOf(user.address) / 10**mim['decimals']
    total_stablecoin_balance = + usdc_balance + usdt_balance + dai_balance + mim_balance

    total_usd_value = account_value_of_eth_in_usd + total_stablecoin_balance
    total_eth_value = total_eth + (total_usd_value / chainlink_price_of_weth_in_usd)


    print(
    f"\n---------------------- \
        \n{datetime.datetime.now().strftime('%D')} @ {datetime.datetime.now().strftime('%H:%M:%S')}\n \
        \nCurrent account value: \
        \n \
        \nETH: {eth_balance:.4f} \
        \nWETH: {weth_balance:.4f} \
        \nTotal: {total_eth:.4f} @ ${chainlink_price_of_weth_in_usd:.2f} = ${account_value_of_eth_in_usd:.0f}  \
        \n \
        \nUSDC: ${usdc_balance:.0f} \
        \nUSDT: ${usdt_balance:.0f} \
        \nMIM: ${mim_balance:.0f} \
        \nDAI: ${dai_balance:.0f} \
        \nTotal: ${total_stablecoin_balance:.0f} \
        \n \
        \nTotal (USD): ${total_usd_value:.0f} \
        \nTotal (ETH): {total_eth_value:.4f} \
        \n----------------------\n"
    )


# Only executes main loop if this file is called directly
if __name__ == "__main__":
    main()