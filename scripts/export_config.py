"""Exporta somente o output público pipeline_config das raízes aplicadas."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clouds", choices=["aws", "azure", "both"], default="both")
    args = parser.parse_args()
    roots = ["aws", "azure"] if args.clouds == "both" else [args.clouds]
    result = {"source_revision": "42efa594aaf3ef5b24877c7b61f1c1d7abc280cc"}
    for root in roots + ["databricks"]:
        output = subprocess.check_output(["terraform", f"-chdir={ROOT / 'terraform' / root}",
                                          "output", "-json", "pipeline_config"], text=True)
        result[root] = json.loads(output)
    (ROOT / ".runtime").mkdir(exist_ok=True)
    (ROOT / ".runtime/config.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Outputs públicos exportados para .runtime/config.json")


if __name__ == "__main__":
    main()
