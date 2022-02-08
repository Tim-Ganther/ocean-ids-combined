from ocean_lib.example_config import ExampleConfig
from ocean_lib.ocean.ocean import Ocean
import os
from ocean_lib.web3_internal.wallet import Wallet
from ocean_lib.ocean.mint_fake_ocean import mint_fake_OCEAN
from ocean_lib.data_provider.data_service_provider import DataServiceProvider
from ocean_lib.common.agreements.service_types import ServiceTypes
from ocean_lib.services.service import Service
from ocean_lib.web3_internal.currency import to_wei
from ocean_lib.models.btoken import BToken #BToken is ERC20

from ocean_lib.common.agreements.service_types import ServiceTypes
from ocean_lib.web3_internal.currency import pretty_ether_and_wei
from ocean_lib.web3_internal.constants import ZERO_ADDRESS
from ocean_lib.common.agreements.service_types import ServiceTypes

#create ocean instance
config = ExampleConfig.get_config()
ocean = Ocean(config)

def create_offer():

    print(f"config.network_url = '{config.network_url}'")
    print(f"config.block_confirmations = {config.block_confirmations.value}")
    print(f"config.metadata_cache_uri = '{config.metadata_cache_uri}'")
    print(f"config.provider_url = '{config.provider_url}'")

    #Alice's wallet
    alice_private_key = "0x5d75837394b078ce97bc289fa8d75e21000573520bfa7784a9d28ccaae602bf8"
    alice_wallet = Wallet(ocean.web3, alice_private_key, config.block_confirmations, config.transaction_timeout)
    print(f"alice_wallet.address = '{alice_wallet.address}'")

    #Mint OCEAN
    mint_fake_OCEAN(config)

    #Publish a datatoken
    assert alice_wallet.web3.eth.get_balance(alice_wallet.address) > 0, "need ETH"
    data_token = ocean.create_data_token('DataToken1', 'DT1', alice_wallet, blob=ocean.config.metadata_cache_uri)
    token_address = data_token.address
    print(f"token_address = '{token_address}'")

    #Specify metadata and service attributes, using the Branin test dataset
    date_created = "2019-12-28T10:55:11Z"
    metadata =  {
        "main": {
            "type": "dataset", "name": "branin", "author": "Trent",
            "license": "CC0: Public Domain", "dateCreated": date_created,
            "files": [{"index": 0, "contentType": "text/text",
                   "url": "https://raw.githubusercontent.com/trentmc/branin/main/branin.arff"}]}
    }
    service_attributes = {
            "main": {
                "name": "dataAssetAccessServiceAgreement",
                "creator": alice_wallet.address,
                "timeout": 3600 * 24,
                "datePublished": date_created,
                "cost": 1.0, # <don't change, this is obsolete>
            }
        }

    #Publish metadata and service attributes on-chain.
    # The service urls will be encrypted before going on-chain.
    # They're only decrypted for datatoken owners upon consume.

    service_endpoint = DataServiceProvider.get_url(ocean.config)
    download_service = Service(
        service_endpoint=service_endpoint,
        service_type=ServiceTypes.ASSET_ACCESS,
        attributes=service_attributes,
    )
    assert alice_wallet.web3.eth.get_balance(alice_wallet.address) > 0, "need ETH"
    asset = ocean.assets.create(
      metadata,
      alice_wallet,
      services=[download_service],
      data_token_address=token_address)
    assert token_address == asset.data_token_address

    did = asset.did  # did contains the datatoken address
    print(f"did = '{did}'")

    #Mint the datatokens
    data_token.mint(alice_wallet.address, to_wei(100), alice_wallet)

    #In the create() step below, Alice needs ganache OCEAN. Ensure she has it.
    OCEAN_token = BToken(ocean.web3, ocean.OCEAN_address)
    assert OCEAN_token.balanceOf(alice_wallet.address) > 0, "need OCEAN"

    #Post the asset for sale. This does many blockchain txs: create base
    # pool, bind OCEAN and datatoken, add OCEAN and datatoken liquidity,
    # and finalize the pool.
    pool = ocean.pool.create(
       token_address,
       data_token_amount=to_wei(100),
       OCEAN_amount=to_wei(10),
       from_wallet=alice_wallet
    )
    pool_address = pool.address
    print(f"pool_address = '{pool_address}'")

    return data_token, token_address, OCEAN_token, pool_address, did

def buy_data(data_token, token_address, OCEAN_token, pool_address, did):
    #point to services
    asset = ocean.assets.resolve(did)
    service1 = asset.get_service(ServiceTypes.ASSET_ACCESS)

    #point to pool
    pool = ocean.pool.get(ocean.web3, pool_address)

    #To access a data service, you need 1.0 datatokens.
    #Here, the market retrieves the datatoken price denominated in OCEAN.
    OCEAN_address = ocean.OCEAN_address
    price_in_OCEAN = ocean.pool.calcInGivenOut(
        pool_address, OCEAN_address, token_address, token_out_amount=to_wei(1))
    print(f"Price of 1 {data_token.symbol()} is {pretty_ether_and_wei(price_in_OCEAN, 'OCEAN')}")

    #Bob's wallet
    bob_private_key = os.getenv('TEST_PRIVATE_KEY2')
    bob_wallet = Wallet(ocean.web3, bob_private_key, config.block_confirmations, config.transaction_timeout)
    print(f"bob_wallet.address = '{bob_wallet.address}'")

    #Verify that Bob has ganache ETH
    assert ocean.web3.eth.get_balance(bob_wallet.address) > 0, "need ganache ETH"

    #Verify that Bob has ganache OCEAN
    assert OCEAN_token.balanceOf(bob_wallet.address) > 0, "need ganache OCEAN"

    #Bob buys 1.0 datatokens - the amount needed to consume the dataset.
    data_token = ocean.get_data_token(token_address)
    ocean.pool.buy_data_tokens(
        pool_address,
        amount=to_wei(1), # buy 1.0 datatoken
        max_OCEAN_amount=to_wei(10), # pay up to 10.0 OCEAN
        from_wallet=bob_wallet
    )

    print(f"Bob has {pretty_ether_and_wei(data_token.balanceOf(bob_wallet.address), data_token.symbol())}.")

    assert data_token.balanceOf(bob_wallet.address) >= to_wei(1), "Bob didn't get 1.0 datatokens"

    #Bob points to the service object
    fee_receiver = ZERO_ADDRESS # could also be market address
    asset = ocean.assets.resolve(did)
    service = asset.get_service(ServiceTypes.ASSET_ACCESS)

    #Bob sends his datatoken to the service
    quote = ocean.assets.order(asset.did, bob_wallet.address, service_index=service.index)
    order_tx_id = ocean.assets.pay_for_service(
        ocean.web3,
        quote.amount,
        quote.data_token_address,
        asset.did,
        service.index,
        fee_receiver,
        bob_wallet,
        service.get_c2d_address()
    )
    print(f"order_tx_id = '{order_tx_id}'")

    #Bob downloads. If the connection breaks, Bob can request again by showing order_tx_id.
    file_path = ocean.assets.download(
        asset.did,
        service.index,
        bob_wallet,
        order_tx_id,
        destination='./'
    )
    print(f"file_path = '{file_path}'") #e.g. datafile.0xAf07...