import os

from dataverse_api import DataverseClient
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
from msal_requests_auth.auth import ClientCredentialAuth
from requests import Session

load_dotenv()

# Authenticate
app_reg = ConfidentialClientApplication(
    client_id=os.getenv("CLIENT_ID"),
    client_credential=os.getenv("CLIENT_SECRET"),
    authority=os.getenv("TOKEN_AUTHORITY_ENDPOINT"),
)
environment_url = os.getenv("ENVIRONMENT_URL")

auth = ClientCredentialAuth(client=app_reg, scopes=[environment_url + "/.default"])

# Prepare Session
session = Session()
session.auth = auth

# Instantiate DataverseClient
client = DataverseClient(session=session, environment_url=environment_url)

# Instantiate interface to Entity
entity = client.entity(logical_name="botcomponent")

# Read data from the entity
data = entity.read(
    select=["name", "description", "data"],
    filter=f"botcomponentid eq '{os.getenv("BOT_COMPONENT_ID")}'",
)[0]

# Check the data
print(f"Name: {data['name']}")
print(f"Description: {data['description']}")
print(f"Data: {data['data']}")

# Close the client session
session.close()
