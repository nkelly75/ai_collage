using './main.bicep'

param resourceGroupName = 'ai-collage-dev'
param location = 'eastus'
param developerObjectId = readEnvironmentVariable('AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID')
