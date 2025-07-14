# This is a utility script to register evaluators in an Azure Foundry Hub project.
# It dynamically imports evaluator classes from specified paths, converts them
# into flows, and registers them in the Foundry Hub project as custom evaluators.

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from promptflow.client import PFClient

load_dotenv()


def register_evaluator(evaluator_cfg, module_name):
    """
    Register a single evaluator based on the configuration.
    Handles dynamic import, flow saving, and evaluator registration
    within a Foundry Hub project.
    """

    # Path to the evaluator definition script
    # This path is relative to the current file's directory.
    evaluator_path = (Path(__file__).parent / evaluator_cfg["path"]).resolve()
    # Add the script's directory to sys.path to support local imports
    script_dir = evaluator_path.parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    # Load the class dynamically and register it in sys.modules
    # This allows the class to be imported as if it were a regular module.
    spec = importlib.util.spec_from_file_location(module_name, str(evaluator_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    if not hasattr(module, "__file__"):
        module.__file__ = str(evaluator_path)
    evaluator_name = getattr(module, "EVALUATOR_NAME")
    evaluator_description = getattr(module, "EVALUATOR_DESCRIPTION", "")
    EvaluatorClass = getattr(module, evaluator_name)
    EvaluatorClass.__module__ = module_name

    # Ask user for the flow save location
    default_local_path = Path(__file__).parent / f"{evaluator_name}_flow"
    user_input = input(
        f"Enter path to save the flow for {evaluator_name} "
        f"[default: {default_local_path}]: "
    ).strip()
    local_path = Path(user_input) if user_input else default_local_path

    # Confirm with user before saving
    confirm_save = input(f"Save flow to {local_path}? (y/n): ").strip().lower()
    if confirm_save != "y":
        print(f"Skipping registration for {evaluator_name}.")
        return

    # If the folder exists, confirm overwrite
    if local_path.exists():
        overwrite = (
            input(f"Path {local_path} already exists. Overwrite? (y/n): ")
            .strip()
            .lower()
        )
        if overwrite == "y":
            shutil.rmtree(local_path)
        else:
            print("Skipping registration for this evaluator.")
            return

    # Save the flow locally.
    pf_client = PFClient()
    pf_client.flows.save(
        entry=EvaluatorClass,
        path=local_path,
    )

    # Upload the flow to Foundry.
    ml_client = MLClient(
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_HUB_PROJECT_NAME"],
        credential=DefaultAzureCredential(),
    )
    custom_evaluator = Model(
        path=local_path,
        name=evaluator_name,
        description=evaluator_description,
    )
    result = ml_client.evaluators.create_or_update(custom_evaluator)
    print(f"Registered evaluator for {evaluator_name}: " f"{result.id}")

    # Optionally, clean up the local flow directory
    # Ask user if they want to delete the local flow directory
    delete_local = (
        input(f"Do you want to delete the local flow directory {local_path}? (y/n): ")
        .strip()
        .lower()
    )
    if delete_local == "y":
        print(f"Deleting local flow directory: {local_path}")
        if Path(local_path).exists():
            shutil.rmtree(local_path)


def main():
    """
    Example usage:
        python register_evaluator.py --config ../../../config/evaluator_registration_config.json # noqa: E501

    Config structure:
        {
            "module_name": "custom_evaluators",
            "evaluators": [
                {
                    "path": "../evaluators/routing_accuracy/routing_accuracy.py",
                    "register": true
                }
            ],
            "notes": (
                "The paths to the evaluator definition scripts are relative to the "
                "parent directory of register_evaluator.py."
            )
        }
    """
    parser = argparse.ArgumentParser(description="Register evaluators using config.")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to evaluator_registration_config JSON file.",
    )
    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config = json.load(f)

    module_name = config.get("module_name", "custom_evaluators")
    for evaluator_cfg in config.get("evaluators", []):
        if not evaluator_cfg.get("register", False):
            continue
        register_evaluator(evaluator_cfg, module_name)


if __name__ == "__main__":
    main()
