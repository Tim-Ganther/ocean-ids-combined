import modules.ocean as oc
import modules.ids as ids

token_address, pool_address, did = oc.create_offer()

resourceUUID = ids.provider_main(did_str = did)
resource_uuid, resource_data = ids.consumer_main()

oc.buy_data(token_address, pool_address, resource_data)