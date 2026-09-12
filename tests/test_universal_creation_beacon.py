import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / ".axm" / "beacon" / "beacon.py"
spec = importlib.util.spec_from_file_location("universal_creation_beacon", MODULE_PATH)
beacon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = beacon
assert spec.loader is not None
spec.loader.exec_module(beacon)
network = sys.modules["network"]

REFERENCE_CAPSULE_ID = "2345cdcd6107af8a453480e50b2e598c91ac63f4440179ef459f78418f474e8d"


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE)
    return proc.stdout.strip()


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.content


class UniversalCreationBeaconTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="universal-creation-beacon-"))
        git(root, "init", "-q")
        git(root, "config", "user.email", "beacon-test@example.invalid")
        git(root, "config", "user.name", "Beacon Test")
        (root / ".axm").mkdir()
        shutil.copy2(ROOT / ".axm" / "beacon.json", root / ".axm" / "beacon.json")
        (root / "machine.contract.json").write_text('{"machine":"canonical"}\n', encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "seed creation-machine fixture")
        return root

    def add_creation_change(self, root: Path) -> tuple[str, str]:
        base = git(root, "rev-parse", "HEAD")
        (root / "src" / "axm_uc").mkdir(parents=True)
        (root / "tests").mkdir()
        (root / "docs").mkdir()
        (root / "src" / "axm_uc" / "creation_transform.py").write_text(
            "def compile_creation_recipe(recipe_state):\n"
            "    return {**recipe_state, 'receipt': 'deterministic-transform'}\n",
            encoding="utf-8",
        )
        (root / "tests" / "test_creation_transform.py").write_text(
            "from axm_uc.creation_transform import compile_creation_recipe\n",
            encoding="utf-8",
        )
        (root / "docs" / "CREATION_TRANSFORM.md").write_text("# Deterministic creation transform receipt\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "add deterministic creation recipe transform")
        return base, git(root, "rev-parse", "HEAD")

    def test_real_creation_change_publishes_reproducibly_and_surfaces_domain_signal(self):
        root = self.make_repo()
        base, head = self.add_creation_change(root)
        first = beacon.publish(root, base, head, root / "feed-a", ".axm/beacon.json")
        second = beacon.publish(root, base, head, root / "feed-b", ".axm/beacon.json")
        self.assertEqual(first["capsule_id"], second["capsule_id"])
        self.assertEqual(first["evidence"]["patch_sha256"], second["evidence"]["patch_sha256"])
        self.assertFalse(first["transfer"]["auto_apply"])
        source = next(item for item in first["evidence"]["files"] if item["path"] == "src/axm_uc/creation_transform.py")
        self.assertIn("compile_creation_recipe", source["symbols"])
        self.assertTrue({"creation", "recipe", "transform"}.issubset(first["signals"]["tags"]))
        self.assertIn("test-change", first["signals"]["kinds"])
        self.assertEqual(beacon.verify_capsule(first), (True, "ok"))

    def test_outputs_snapshots_private_and_reference_state_cannot_leak(self):
        root = self.make_repo()
        base = git(root, "rev-parse", "HEAD")
        safe = root / "src" / "axm_uc" / "offline_capability.py"
        safe.parent.mkdir(parents=True)
        safe.write_text("def offline_creation_receipt():\n    return 'safe'\n", encoding="utf-8")
        forbidden = {
            "creations/private-project/output.txt": "CREATED-PRIVATE-OUTPUT",
            "daily-snapshots/machine.zip": "SNAPSHOT-BYTES",
            "reference/imported-body/credential.pem": "REFERENCE-CREDENTIAL",
            "private/operator-note.txt": "PRIVATE-OPERATOR-NOTE",
            ".env.local": "GITHUB_TOKEN=DO-NOT-LEAK",
        }
        for relative, content in forbidden.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "add safe offline capability beside excluded state")
        capsule = beacon.publish(root, base, "HEAD", root / "feed", ".axm/beacon.json")
        paths = {item["path"] for item in capsule["evidence"]["files"]}
        self.assertEqual(paths, {"src/axm_uc/offline_capability.py"})
        patch = (root / "feed" / "patches" / f"{capsule['capsule_id']}.patch").read_text(encoding="utf-8")
        self.assertIn("offline_creation_receipt", patch)
        for relative, content in forbidden.items():
            self.assertNotIn(relative, patch)
            self.assertNotIn(content, patch)

    def test_receiver_ranks_the_exact_discovery_buddy_reference_capsule(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "axm_beacon_reference_index.json").read_text(encoding="utf-8"))
        config = beacon.load_config(ROOT, ".axm/beacon.json")
        ranked = network.rank_candidates([fixture], config["repo"], config["interests"])
        self.assertEqual(ranked[0]["capsule_id"], REFERENCE_CAPSULE_ID)
        self.assertGreater(ranked[0]["relevance_score"], ranked[0]["attention_score"])
        self.assertTrue({"canonical", "identity", "organ", "protocol"}.intersection(ranked[0]["interest_overlap"]))

    def test_fetch_writes_only_proposal_state_and_preserves_machine_contract(self):
        root = self.make_repo()
        base, head = self.add_creation_change(root)
        capsule = beacon.publish(root, base, head, root / "source-feed", ".axm/beacon.json")
        patch = (root / "source-feed" / "patches" / f"{capsule['capsule_id']}.patch").read_bytes()
        contract = root / "machine.contract.json"
        before = contract.read_bytes()
        inbox = root / ".axm" / "beacon" / "inbox"
        with mock.patch.object(network, "_request_json", return_value=capsule), mock.patch.object(network.urllib.request, "urlopen", return_value=_Response(patch)):
            capsule_path, patch_path = network.fetch_capsule("example/source", capsule["capsule_id"], "axm-beacon-feed", inbox)
        self.assertEqual(contract.read_bytes(), before)
        self.assertTrue(capsule_path.is_relative_to(inbox))
        self.assertTrue(patch_path.is_relative_to(inbox))
        self.assertEqual((capsule_path.parent / "STATUS.txt").read_text(encoding="utf-8").splitlines()[:2], ["proposal-only", "not applied"])

    def test_tampered_capsule_and_patch_are_rejected(self):
        root = self.make_repo()
        base, head = self.add_creation_change(root)
        capsule = beacon.publish(root, base, head, root / "source-feed", ".axm/beacon.json")
        altered = json.loads(json.dumps(capsule))
        altered["signals"]["attention_score"] += 1
        self.assertFalse(beacon.verify_capsule(altered)[0])
        with mock.patch.object(network, "_request_json", return_value=capsule), mock.patch.object(network.urllib.request, "urlopen", return_value=_Response(b"altered patch")):
            with self.assertRaises(beacon.BeaconError):
                network.fetch_capsule("example/source", capsule["capsule_id"], "axm-beacon-feed", root / "inbox")


if __name__ == "__main__":
    unittest.main()
