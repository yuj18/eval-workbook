#!/bin/bash

# Initialize conda
source /opt/conda/etc/profile.d/conda.sh

# Create a new conda environment
echo "Creating conda environment 'eval'..."
conda create -n eval python=3.12 -y

# Activate the environment
conda activate eval

# Install pip packages from requirements
echo "Installing packages from requirements.txt..."
pip install -r environment/requirements.txt

echo "Installing packages from requirements-dev.txt..."
pip install -r environment/requirements-dev.txt

# Make the environment available in VS Code
echo "Setting up VS Code Python interpreter..."
conda activate eval
python -m ipykernel install --user --name=eval --display-name="eval"

# Add conda activation to bashrc for this environment
echo "" >> ~/.bashrc
echo "# Auto-activate conda environment" >> ~/.bashrc
echo "conda activate eval" >> ~/.bashrc

echo "Setup complete! Conda environment 'eval' is ready."
echo "To activate manually: conda activate eval"
