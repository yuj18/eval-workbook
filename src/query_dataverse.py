import json
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

# ------------------------------------------------------------------------
# Example 1: Read bot component (e.g. agent) description and specification
# ------------------------------------------------------------------------

# Instantiate interface to the entity
# https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/bot_botcomponent
entity = client.entity(logical_name="botcomponent")

# Read data from the entity
data = entity.read(
    select=["name", "description", "data"],
    filter=f"botcomponentid eq '{os.getenv("BOT_COMPONENT_ID")}'",
)[0]

print("\n------------------------- Bot Component -------------------------")
print(f"\nName: {data['name']}")
print(f"\nDescription: {data['description']}")
print(f"\nSpecification: {data['data'][:1500]}\n...")


# --------------------------------------------
# Example 2: Read conversation logs/activities
# --------------------------------------------

# Instantiate interface to the entity
# https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/conversationtranscript
entity = client.entity(logical_name="conversationtranscript")

# Read data from the entity
data = entity.read(
    select=[
        "name",
        "_bot_conversationtranscriptid_value",
        "conversationtranscriptid",
        "content",
        "conversationstarttime",
        "createdon",
        "metadata",
    ],
    filter=f"contains(name, '{os.getenv("CONVERSATION_ID")}')",
)


print("\n\n------------------------- Conversation Logs -------------------------")
for item in data:
    item["metadata"] = json.loads(item["metadata"])
    print(f"\nBot : {item['metadata']['BotName']}")
    print(f"\nBot ID: {item['_bot_conversationtranscriptid_value']}")
    # Name of conversation is prefixed with Conversation ID
    print(f"\nName of Conversation: {item['name']}")
    print(f"\nTranscript ID: {item['conversationtranscriptid']}")
    print(f"\nConversation Start Time: {item['conversationstarttime']}")
    print(f"\nRecord created On: {item['createdon']}")
    # Content field contains conversation logs/activities
    content = json.loads(item["content"])
    print(f"\nConversation Log: {json.dumps(content, indent=2)[:1500]}\n...")

# Close the client session
session.close()
