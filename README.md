# flask-aks
Launch flask application in the AKS using python script

## Process

### Flask application docker image build

```
docker build -t flask-helloworld:v1 .
```

### Create container registry in Azure

```
# create an Azure Container Registry instance
az acr create --resource-group Admin --name admincr --sku Standard
```

```
# To get the acr login server address
az acr list --resource-group Admin --query "[].{acrLoginServer:loginServer}" --output table
```

```
# Tag the local image with the acrLoginServer address of the container registry.
docker tag flask-helloworld:v1 admincr.azurecr.io/flask-helloworld:v1
```

```
# Log in to the Azure container registry
az acr login --name admincr
```

```
# Push images to registry
docker push admincr.azurecr.io/flask-helloworld:v1
```

```
# List images in registry
az acr repository list --name admincr --output table
```

```
# Delete repository
az acr repository delete --name admincr --repository flask-helloworld
```

### Create kubernetes cluster

```Azure CLI
az aks create \ 
    --location uksouth \
    --resource-group Admin \
    --name adminAKSCluster \
    --node-count 2 \
    --generate-ssh-keys \ 
    --attach-acr admincr
```

```
# connect to cluster using kubectl
az aks get-credentials --resource-group Admin --name adminAKSCluster
```

```
# install kubectl
sudo az aks install-cli
```
