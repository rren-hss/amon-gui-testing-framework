import argparse
import json
import sys
from multistep_guis import show_manual_popup

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test-case-id",
        required=True,
    )
    parser.add_argument(
        "--test-case-name",
        required=True,
    )
    parser.add_argument(
        "--step-id",
        required=True,
    )
    parser.add_argument(
        "--instruction",
        required=True,
    )
    parser.add_argument(
        "--expected",
        required=True,
    )

    args = parser.parse_args()

    test_case = {
        "id": args.test_case_id,
        "name": args.test_case_name,
    }

    step = {
        "step_id": args.step_id,
        "instruction": args.instruction,
        "expected": args.expected,
    }

    result = show_manual_popup(
        test_case,
        step,
    )

    print(
        json.dumps(result),
        flush=True,
    )

    if result["action"] == "abort":
        sys.exit(3)

    if result["status"] == "PASS":
        sys.exit(0)

    if result["status"] in {
        "FAIL",
        "FAILED",
    }:
        sys.exit(1)

    sys.exit(2)


if __name__ == "__main__":
    main()
