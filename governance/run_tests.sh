#!/bin/bash
echo "Running Tests in 3 seconds"
sleep 3

python3 -m pytest test_governance.py -v
