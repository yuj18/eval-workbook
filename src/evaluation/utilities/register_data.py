# This is a utility script to register data assets in an Azure Fundry Hub project.

import argparse
import json
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Data
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


def main():
    """
    Example usage:
        python register_data.py --config ../../../config/data_registration_config.json

    Config structure:
        {
            "name": "interactive_conversations_test",
            "path": "../../../data/input/interactive_conversations_patched.jsonl",
            "description": (
                "A dataset that captures the trace of interactive "
                "conversations with MCS agents."
            ),
            "notes": (
                "The path to the dataset is relative to the parent directory "
                "of register_data.py."
            )
        }
    """
    parser = argparse.ArgumentParser(description="Register data asset using config.")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to data registration config JSON file.",
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)

    name = config["name"]
    path = (Path(__file__).parent / config["path"]).resolve()
    data_description = config.get("description", "")

    print(f"About to register data asset with name: {name}")
    print(f"Path: {path}")
    print(f"Description: {data_description}")
    confirm = input("Proceed with registration? (y/n): ").strip().lower()
    if confirm != "y":
        print("Registration cancelled by user.")
        return

    ml_client = MLClient(
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_HUB_PROJECT_NAME"],
        credential=DefaultAzureCredential(),
    )

    try:
        # Increment the version if the data asset already exists
        data_asset = ml_client.data.get(name=name, label="latest")
        version = data_asset.version
        print(f"Data asset '{name}' already exists with version: {version}")
        version = str(int(version) + 1)
    except Exception:
        version = "1"

    data = Data(
        path=path,
        type=AssetTypes.URI_FILE,
        name=name,
        is_anonymous=True,
        version=version,
        description=data_description,
    )

    data_asset = ml_client.data.create_or_update(data)

    print(f"Registered data asset: {data_asset.id} with version: {data_asset.version}")


if __name__ == "__main__":
    main()
