# Data Exchange Example

This quickstart describes a batteries-included flow including using off-chain services for metadata (Aquarius) and consuming datasets (Provider). Instead of passing through the `did` directly IDS Connectors are used to store the `did` with usage policies and whenever users buy data on ocean they need to receive the `did` though IDS Connectors first.

## Setup

### Prerequisites

-   Linux/MacOS
-   Docker, [allowing non-root users](https://www.thegeekdiary.com/run-docker-as-a-non-root-user/)
-   Python 3.8.5+

### Run barge services

In a new console:

```console
#grab repo
git clone https://github.com/oceanprotocol/barge
cd barge

#clean up old containers (to be sure)
docker system prune -a --volumes

#run barge: start ganache, Provider, Aquarius; deploy contracts; update ~/.ocean
./start_ocean.sh  --with-provider2
```

### Run Ocean Market service

In a new console:

```console
#install
git clone https://github.com/oceanprotocol/market.git
cd market
npm install

#run Ocean Market app
npm start
```

Check out the Ocean Market webapp at http://localhost:8000.

Ocean Market is a graphical interface to the backend smart contracts and Ocean services (Aquarius, Provider). The following steps will interface to the backend in a different fashion: using the command-line / console, and won't need Ocean Market. But it's good to understand there are multiple views.

### Install the library

In a new console that we'll call the _work_ console (navigate to git root):

```console
#Clone this repo
git clone https://github.com/Tim-Ganther/ocean-ids-combined.git

#Initialize virtual environment and activate it.
python -m venv venv
source venv/bin/activate

#Install the ocean.py library. Install wheel first to avoid errors.
pip install wheel
pip install ocean-lib
```

### Set envvars

In the work console:
```console
#set private keys of two accounts
export TEST_PRIVATE_KEY1=0x5d75837394b078ce97bc289fa8d75e21000573520bfa7784a9d28ccaae602bf8
export TEST_PRIVATE_KEY2=0xef4b441145c1d0f3b4bc6d61d29f5c6e502359481152f869247c7a4244d45209

#needed to mint fake OCEAN for testing with ganache
export FACTORY_DEPLOYER_PRIVATE_KEY=0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58

#set the address file only for ganache
export ADDRESS_FILE=~/.ocean/ocean-contracts/artifacts/address.json

#set network URL
export OCEAN_NETWORK_URL=http://127.0.0.1:8545

#start python
python
```

### Run app.py
In the work console:
```console
python app.py
```

In console:

```console
#verify that the file is downloaded
cd datafile.0xAf07...
cat branin.arff
```

Congrats to Bob for buying and consuming a data asset!

_Note_. The file is in ARFF format, used by some AI/ML tools. In this case there are two input variables (x0, x1) and one output.

```console
% 1. Title: Branin Function
% 3. Number of instances: 225
% 6. Number of attributes: 2

@relation branin

@attribute 'x0' numeric
@attribute 'x1' numeric
@attribute 'y' numeric

@data
-5.0000,0.0000,308.1291
-3.9286,0.0000,206.1783
...
```
