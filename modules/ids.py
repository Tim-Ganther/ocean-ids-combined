import warnings
import requests
from requests.auth import HTTPBasicAuth
import json
import uuid
from uuid import UUID

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


def provider_add_data_to_resource(resourceUUID, provider_user_data):
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


def provider_main(did_str):

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
    response = provider_add_data_to_resource(resourceUUID = resourceUUID, provider_user_data = did_str)
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
