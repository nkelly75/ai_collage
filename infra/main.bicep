targetScope = 'subscription'

@description('Development resource group. Existing Foundry resources are not part of this deployment.')
param resourceGroupName string

param location string

@description('Object ID of the signed-in developer in the target subscription tenant.')
param developerObjectId string

@minLength(3)
@maxLength(24)
param storageAccountName string = 'stclgdev${uniqueString(subscription().subscriptionId, resourceGroupName)}'

var tags = {
  application: 'ai-collage'
  environment: 'dev'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module storage './storage.bicep' = {
  name: 'collage-dev-storage'
  scope: resourceGroup
  params: {
    location: location
    storageAccountName: storageAccountName
    developerObjectId: developerObjectId
    tags: tags
  }
}

output resourceGroupName string = resourceGroup.name
output storageAccountName string = storage.outputs.storageAccountName
output blobEndpoint string = storage.outputs.blobEndpoint
output containerName string = storage.outputs.containerName
output containerId string = storage.outputs.containerId
