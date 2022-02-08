import sys
# Imports required by ocean
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

# Imports required by ids solution
import warnings
import requests
from requests.auth import HTTPBasicAuth
import json
import uuid
from uuid import UUID

#create ocean instance
config = ExampleConfig.get_config()
ocean = Ocean(config)

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

#############################################################################################################################
############################################# END CREATION ##################################################################
#############################################################################################################################

warnings.filterwarnings("ignore")

provider_port = 8080
consumer_port = 8081

userGivenID = 1234

provider_session = requests.Session()
consumer_session = requests.Session()

provider_username = "admin"
provider_password = "password"

consumer_username = "admin"
consumer_password = "password"

provider_user_data = did

headers = {'Content-Type': "application/json", 'Accept': "application/json"}

#N = 1

def provider_login():
    request = "https://localhost:"+str(provider_port)+"/admin/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config#/Connector"
    response = provider_session.get(request,auth=HTTPBasicAuth('admin','password'),verify=False)

    return response


def consumer_login():
    request = "https://localhost:"+str(consumer_port)+"/admin/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config#/Connector"
    response = consumer_session.get(request,auth=HTTPBasicAuth('admin','password'),verify=False)

    return response


def provider_create_resource():

    resource_description={
      "title": "HH - UserData",
      "description": "Membership data of users",
      "policy": "Duration Policy",
      "representations": [
          {
      "uuid": "8e3a5056-1e46-42e1-a1c3-37aa08b2aedd",
      "type": "JSON",
      "byteSize": 420,
      "name": "Membership data Representation",
      "source": {
        "type": "local"
        }
      }
      ]
    }

    #Request
    request = "https://localhost:"+str(provider_port)+"/admin/api/resources/resource"
    params = {'resource-id': ""}

    response = provider_session.post(request,headers=headers, params=params,json = resource_description)

    return response


def provider_add_data_to_resource(resourceUUID):
    user_data = provider_user_data

    #Request
    request = "https://localhost:"+str(provider_port)+"/admin/api/resources/"+resourceUUID+"/data"
    params = {'data': user_data}

    response = provider_session.put(request, headers = headers, params=params,verify=False)

    return response

N = 1

def provider_add_usage_policy_to_resource(resourceUUID):

    request = "https://localhost:"+str(provider_port)+"/admin/api/example/usage-policy?pattern=N_TIMES_USAGE"
    response = provider_session.post(request)
    usage_policy = json.loads(response.text)
    usage_policy["ids:permission"][0]["ids:constraint"][0]["ids:rightOperand"]["@value"] = str(N)

    #Request
    request = "https://localhost:"+str(provider_port)+"/admin/api/resources/"+resourceUUID+"/contract"
    response = provider_session.put(request, headers=headers, data=json.dumps(usage_policy),verify=False)

    return response

def provider_delete_all_resources():

    request = "https://localhost:"+str(provider_port)+"/admin/api/connector"
    response = provider_session.get(request,verify=False)
    response = json.loads(response.text)
    provider_resources = response["ids:resourceCatalog"][0]["ids:offeredResource"]


    for resource in provider_resources:
        resource_uuid = resource["@id"]
        resource_uuid = resource_uuid[39:]
        request = "https://localhost:"+str(provider_port)+"/admin/api/resources/"+str(resource_uuid)
        response = provider_session.delete(request)
        if(response.status_code !=200):
            print("Unable to delete resource with UUID", resource_uuid)
            return False
    print("Resources deleted at Provider", len(provider_resources))


def provider_main():

    # Provider logs in
    response = provider_login()
    try:
        provider_delete_all_resources()
    except:
        print("")

    if(response.status_code!=200):
        print("Provider: unable to login")
        return False
    else:
        print("Provider: logged in")

    # Provider creates resource
    response = provider_create_resource()
    resourceUUID = response.text

    if(response.status_code!=201):
        print("Provider: unable to create resource")
        return False
    else:
        print("Provider: created resource ",resourceUUID)

    # Provider adds data to resource
    response = provider_add_data_to_resource(resourceUUID = resourceUUID)
    if(response.status_code!=201):
        print("Provider: unable to add data to resource")
        print(response.content)
        return False
    else:
        print("Provider: added data to resource ")

    # Provider adds usage policy to resource
    response = provider_add_usage_policy_to_resource(resourceUUID = resourceUUID)
    if(response.status_code!=200):
        print("Provider: unable to add usage policy to resource")
        return False
    else:
        print("Provider: added usage policy to resource")

    return resourceUUID


def consumer_get_availaible_resources_from_provider():
    request = "https://localhost:"+str(consumer_port)+"/admin/api/request/description"
    # Params
    recipient = "https://localhost:"+str(provider_port)+"/api/ids/data"

    params = {'recipient': recipient}

    response = consumer_session.post(request,data=params,verify=False)
    print(response.text)

    return response

def consumer_get_resource_description(requestedResource):
    request = "https://localhost:"+str(consumer_port)+"/admin/api/request/description"
    # Params
    recipient = "https://localhost:"+str(provider_port)+"/api/ids/data"
    params = {'recipient': recipient,
              'requestedResource': requestedResource
              }

    response = consumer_session.post(request,data=params, verify=False)

    return response


def consumer_get_resource_contract_and_valkey_from_provider(requestedResource):
    request = "https://localhost:"+str(consumer_port)+"/admin/api/request/description"
    # Params
    recipient = "https://localhost:"+str(provider_port)+"/api/ids/data"
    params = {'recipient': recipient,
              'requestedResource': requestedResource
              }

    response = consumer_session.post(request,data=params, verify=False)

    return response


def consumer_get_contract_agreement(requested_artifact,resource_contract_offer):
    request = "https://localhost:"+str(consumer_port)+"/admin/api/request/contract?"
    # Params
    recipient = "https://localhost:"+str(provider_port)+"/api/ids/data"
    params = {'recipient': recipient,
              'requestedArtifact': requested_artifact
              }

    response = consumer_session.post(request, params=params, json=resource_contract_offer)

    return response

def consumer_get_resource(requested_artifact,transferContract, key):
    request = "https://localhost:"+str(consumer_port)+"/admin/api/request/artifact"
    # Params
    recipient = "https://localhost:"+str(provider_port)+"/api/ids/data"

    params = {'recipient': recipient,
              'requestedArtifact': requested_artifact,
              'transferContract' : transferContract,
               'key' : key
              }

    response = consumer_session.post(request,data=params,verify=False)

    return response

def consumer_delete_all_resources():

    request = "https://localhost:"+str(consumer_port)+"/admin/api/connector"
    response = consumer_session.get(request,verify=False)
    response = json.loads(response.text)
    consumer_resources = response["ids:resourceCatalog"][0]["ids:offeredResource"]


    for resource in consumer_resources:
        resource_uuid = resource["@id"]
        resource_uuid = resource_uuid[39:]
        request = "https://localhost:"+str(consumer_port)+"/admin/api/resources/"+str(resource_uuid)
        response = consumer_session.delete(request)
        if(response.status_code !=200):
            print("Unable to delete resource with UUID", resource_uuid)
            return False
    print("Resources deleted at Consumer", len(consumer_resources))


def consumer_main():

    # Consumer logs in the Connector
    response = consumer_login()
    try:
        consumer_delete_all_resources()
    except:
        print("")

    if(response.status_code!=200):
        print("Consumer: unable to login")
        return False
    else:
        print("Consumer: logged in")

    # Consumer gets available resources from Provider
    response = consumer_get_availaible_resources_from_provider()
    if(response.status_code!=200):
        print("Consumer: unable to get resources description from Provider")
        return False
    else:
        print("Consumer: received resources description from Provider")

    # Get specifc resource with the given title
    response = json.loads(response.text)
    provider_resources = response["ids:resourceCatalog"][0]["ids:offeredResource"]

    for resource in provider_resources:
        title = resource["ids:title"][0]['@value']
        if(title == "HH - UserData"):
            user_data_uuid = resource["@id"]
            #user_data_uuid = user_data_uuid[39:]
            break

    # Consumer gets metadata of a specific resource from Provider
    response = consumer_get_resource_description(requestedResource = user_data_uuid)
    if(response.status_code!=200):
        print("Consumer: unable to get metadata of specific resource from Provider")
        return False
    else:
        print("Consumer: received metadata and validation key of specific resource from Provider")

    resource_val_key = response.text.partition('\n')[0][12:]
    resource_metadata = response.text.partition('\n')[1:][1][10:]
    resource_metadata = json.loads(resource_metadata)

    requested_artifact = resource_metadata["ids:representation"][0]["ids:instance"][0]["@id"]
    resource_contract_offer = resource_metadata["ids:contractOffer"][0]

    # Consumer gets Contract agreement from Provider
    response = consumer_get_contract_agreement(requested_artifact = requested_artifact, resource_contract_offer = resource_contract_offer)
    print(response)
    transferContract = response.text

    if(response.status_code!=200):
        print("Consumer: unable to make Contract Agreement with Provider")
        return False
    else:
        print("Consumer: received Contract Agreement from Provider")

    # Consumer access the resource from  Provider
    response = consumer_get_resource(requested_artifact = requested_artifact, transferContract = transferContract, key = resource_val_key)
    if(response.status_code!=200):
        print("Consumer: unable to request artifact from Provider")
        return False
    else:
        print("Consumer: received artifact from Provider")


    resource_uuid = response.text[10:46]
    print(provider_user_data)
    print(resource_uuid)
    resource_data = response.text[57:]

    #resource_data = json.load(resource_data)


    return resource_uuid, resource_data



resourceUUID = provider_main()

resource_uuid, resource_data = consumer_main()



print("Was ist der Unterschied:")
print(type(did))
print(did)
print(type(resource_data))
print(resource_data)
#sys.exit("Genug Schabernack!")
#did = resource_data

#point to services
asset = ocean.assets.resolve(resource_data)
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
asset = ocean.assets.resolve(resource_data)
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
