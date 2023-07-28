from multiprocessing.sharedctypes import Value
import os
import sys
import time
from decimal import Decimal
import datetime
from brownie import *

#
# Program Config
#
ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')
PASSWORD = os.getenv('ACCOUNT_PW')

# Contract addresses
SUSHI_ROUTER_CONTRACT_ADDRESS = '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
DAI_CONTRACT_ADDRESS = '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
MIM_CONTRACT_ADDRESS = '0XFEA7A6A0B346362BF88A9E4A88416B77A57D6C2A'
USDC_CONTRACT_ADDRESS = '0XFF970A61A04B1CA14834A43F5DE4533EBDDB5CC8'
USDT_CONTRACT_ADDRESS = '0XFD086BC7CD5C481DCC9C85EBE478A1C0B69FCBB9'
# WETH_CONTRACT_ADDRESS = '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1' # TO DO: do we need this? I don't think it ever gets used for the swaps.

# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

# Time
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

# Loop time config
PAIR_SLEEP_TIME = 1
LOOP_SLEEP_TIME = 60

# Trading options
SWAP_THRESHOLD = Decimal("1.01")
SLIPPAGE = Decimal("0.001")

# Admin options
DRY_RUN = True
ONE_SHOT = True



def main():

    global sushi_router
    # global sushi_lp -- do we need to initalize all LP contracts or variables?
    global dai
    global mim
    global usdc
    global usdt
    global user

    # Connect to Arbitrum Mainnet
    try:
        network.connect('arbitrum-main')        
    except:
        sys.exit(
            "Could not connect to Arbitrum! Verify that brownie lists the Arbitrum Mainnet using 'brownie networks list'"
        )
    
    # Load the user account
    try:
        user = accounts.load(ACCOUNT_NAME, PASSWORD)
    except:
        sys.exit(
            "Could not load account! Verify that your account is listed using 'brownie accounts list' and that you are using the correct password. If you have not added an account, run 'brownie accounts new' now."
        )

    # Load the contracts
    print("\nLoading contracts...")
    dai_contract = contract_load(DAI_CONTRACT_ADDRESS, "Arbitrum Token: DAI")
    mim_contract = contract_load(MIM_CONTRACT_ADDRESS, "Arbitrum Token: MIM")
    usdt_contract = contract_load(USDT_CONTRACT_ADDRESS, "Arbitrum Token: USDT")
    usdc_contract = contract_load(USDC_CONTRACT_ADDRESS, "Arbitrum Token: USDC")

    sushi_router = contract_load(SUSHI_ROUTER_CONTRACT_ADDRESS, "Sushi: Router")

    # TO DO: do we need to get these pool contracts? and do we need one for each of the pairs?
    # sushi_lp = contract_load()


    # Initialize dictionaries for our tokensconra
    dai = {
        "address": DAI_CONTRACT_ADDRESS,
        "contract": dai_contract,
        "name:": None,
        "symbol": None,
        "decimals": None,
    }
    mim = {
        "address": MIM_CONTRACT_ADDRESS,
        "contract": mim_contract,
        "name:": None,
        "symbol": None,
        "decimals": None,
    }
    usdc = {
        "address": USDC_CONTRACT_ADDRESS,
        "contract": usdc_contract,
        "name:": None,
        "symbol": None,
        "decimals": None,
    }
    usdt = {
        "address": USDT_CONTRACT_ADDRESS,
        "contract": usdt_contract,
        "name:": None,
        "symbol": None,
        "decimals": None,
    }
    
    # Fill out the dictionaries
    dai["name"] = get_token_name(dai["contract"])
    mim["name"] = get_token_name(mim["contract"])
    usdc["name"] = get_token_name(usdc["contract"])
    usdt["name"] = get_token_name(usdt["contract"])
    
    dai["symbol"] = get_token_symbol(dai["contract"])
    mim["symbol"] = get_token_symbol(mim["contract"])
    usdc["symbol"] = get_token_symbol(usdc["contract"])
    usdt["symbol"] = get_token_symbol(usdt["contract"])
    
    dai["balance"] = get_token_balance(dai_contract, user)
    mim["balance"] = get_token_balance(mim_contract, user)
    usdc["balance"] = get_token_balance(usdc_contract, user)
    usdt["balance"] = get_token_balance(usdt_contract, user)

    # left off here. add the decimals.


    # A list of tuples with our dictionaries
    token_pairs = [
        (dai, mim),
        (mim, dai),
        (dai, usdc),
        (usdc, dai),
        (dai, usdt),
        (usdt, dai),
        (mim, usdc),
        (usdc, mim),
        (mim, usdt),
        (usdt, mim),
        (usdc, usdt),
        (usdt, usdc),
    ]


def contract_load(address, alias):
    """ 
    Attempts to load the saved contract by alias.
    If not found, fetch from network explorer and set alias.
    """
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract

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

def get_token_balance(token, user):
    try:
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













# Only executes main loop if this file is called directly
if __name__ == "__main__":
    main()