import datetime
import csv
import os
from brownie import *

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




def log_transaction():
    """
    Writes account data to a CSV file after a successful trade.
    """

    NETWORK = 'arbitrum-main'
    ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')
    PASSWORD = os.getenv('ACCOUNT_PW')
    LOG_FILE = 'logs/arbitrum_bot.csv'
    
    WETH_CONTRACT_ADDRESS = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
    USDC_CONTRACT_ADDRESS = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"
    USDT_CONTRACT_ADDRESS = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
    MIM_CONTRACT_ADDRESS = "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A"
    DAI_CONTRACT_ADDRESS = "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"
    CHAINLINK_WETH_PRICE_ADDRESS = "0x639fe6ab55c921f74e7fac1ee960c0b6293ba612"
    
    network.connect(NETWORK)
    user = accounts.load(ACCOUNT_NAME, PASSWORD)
    
    weth_contract = contract_load(WETH_CONTRACT_ADDRESS, "Arbitrum Token: WETH")
    usdc_contract = contract_load(USDC_CONTRACT_ADDRESS, "Arbitrum Token: USDC")
    usdt_contract = contract_load(USDT_CONTRACT_ADDRESS, "Arbitrum Token: USDT")
    mim_contract = contract_load(MIM_CONTRACT_ADDRESS, "Arbitrum Token: MIM")
    dai_contract = contract_load(DAI_CONTRACT_ADDRESS, "Arbitrum Token: DAI")

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


    try:
        print('\nLogging transaction...\n')
        
        # get current prices from data feeds
        chainlink_price_of_weth_in_usd = weth_price.latestRoundData()[1] / 10**weth_price.decimals()

        # CSV Column Headers
        headers = [
            'date', 
            'time', 
            'account_name',
            'logged_from',

            'LOOP_TIME',
            'TRADE_SIZE',
            'SLIPPAGE',
            'SWAP_THRESHOLD',
            
            'eth_balance',
            'weth_balance',
            'total_eth',
            'eth_price',

            'usdc_balance',
            'usdt_balance',
            'mim_balance',
            'dai_balance',
            'total_stablecoin_balance',
        ]

        # CSV Columns
        csv_date = datetime.datetime.now().strftime('%D')
        csv_time = datetime.datetime.now().strftime('%H:%M:%S')
        csv_account_name = ACCOUNT_NAME
        csv_logged_from = 'manual'

        csv_LOOP_TIME = 'manual'
        csv_TRADE_SIZE = 'manual'
        csv_SLIPPAGE = 'manual'
        csv_SWAP_THRESHOLD = 'manual'

        csv_eth_balance = user.balance() / 10**weth['decimals']
        csv_weth_balance = weth["contract"].balanceOf(user.address) / 10**weth['decimals']
        csv_total_eth = csv_eth_balance + csv_weth_balance
        csv_eth_price = chainlink_price_of_weth_in_usd
        
        csv_usdc_balance = usdc["contract"].balanceOf(user.address) / 10**usdc['decimals']
        csv_usdt_balance = usdt["contract"].balanceOf(user.address) / 10**usdt['decimals']
        csv_mim_balance = mim["contract"].balanceOf(user.address) / 10**mim['decimals']
        csv_dai_balance = dai["contract"].balanceOf(user.address) / 10**dai['decimals']
        csv_total_stablecoin_balance = csv_usdc_balance + csv_usdt_balance + csv_mim_balance + csv_dai_balance


        # Write the CSV file
        row = [
            csv_date,
            csv_time,
            csv_account_name,
            csv_logged_from,

            csv_LOOP_TIME,
            csv_TRADE_SIZE,
            csv_SLIPPAGE,
            csv_SWAP_THRESHOLD,

            csv_eth_balance,
            csv_weth_balance,
            csv_total_eth,
            csv_eth_price, 

            csv_usdc_balance,
            csv_usdt_balance,
            csv_mim_balance,
            csv_dai_balance,
            csv_total_stablecoin_balance,
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

log_transaction()








