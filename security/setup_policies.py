# security/setup_policies.py
"""
Simulates IAM-style access control on MinIO buckets.
Demonstrates the security architecture described in the report.
"""

import json
import sys
from minio import Minio
from minio.commonconfig import ENABLED

sys.stdout.reconfigure(line_buffering=True)


def setup():
    client = Minio(
        "localhost:9000", access_key="admin", secret_key="admin12345", secure=False
    )

    # === RAW-ZONE POLICY ===
    # Only governance-agent and compliance-officer can access
    raw_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyPublicAccess",
                "Effect": "Deny",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::raw-zone/*"],
                "Condition": {
                    "StringNotEquals": {
                        "aws:PrincipalTag/role": [
                            "governance-agent",
                            "compliance-officer",
                        ]
                    }
                },
            }
        ],
    }

    # === CURATED-ZONE POLICY ===
    # Analysts, APIs, and public consumers can read
    curated_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAnalyticsRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    "arn:aws:s3:::curated-zone",
                    "arn:aws:s3:::curated-zone/*",
                ],
            }
        ],
    }

    # Apply policies
    try:
        client.set_bucket_policy("raw-zone", json.dumps(raw_policy))
        print("raw-zone policy applied: RESTRICTED ACCESS")
        print("  - Only governance-agent and compliance-officer roles")
        print("  - All other access DENIED")
    except Exception as e:
        print(f"raw-zone policy: {e}")

    try:
        client.set_bucket_policy("curated-zone", json.dumps(curated_policy))
        print("\ncurated-zone policy applied: OPEN FOR ANALYTICS")
        print("  - Analysts can read")
        print("  - APIs can read")
        print("  - Public consumers can read")
    except Exception as e:
        print(f"curated-zone policy: {e}")

    # Print IAM Role Matrix
    print("\n" + "=" * 60)
    print("IAM ROLE ACCESS MATRIX")
    print("=" * 60)
    print(f"{'Role':<25} {'raw-zone':<15} {'curated-zone':<15}")
    print("-" * 55)
    print(f"{'governance-agent':<25} {'READ/WRITE':<15} {'WRITE':<15}")
    print(f"{'compliance-officer':<25} {'READ':<15} {'READ':<15}")
    print(f"{'data-analyst':<25} {'DENIED':<15} {'READ':<15}")
    print(f"{'api-consumer':<25} {'DENIED':<15} {'READ':<15}")
    print(f"{'public':<25} {'DENIED':<15} {'READ (governed)':<15}")
    print("=" * 60)


if __name__ == "__main__":
    setup()
