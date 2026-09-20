"""A source-backed view of UC knowledge, construction parts and executable routes.

The atlas joins existing libraries. Indexing a record never upgrades its evidence
or installs its resource. New categories are data; new execution stays in the
ordinary capability machinery.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .asset_atoms import AssetPackageLibrary
from .organ_library import ExecutableOrganLibrary
from .registry import Registry

SCHEMA = "axm.creation-atlas/v0.1"
PACK_SCHEMA = "axm.creation-atlas-pack/v0.1"
RUNTIME = Path(__file__).resolve().parent
REFERENCE_DEPENDENCIES = {"reference Universal Creation Map v0.1": "registry:universal-creation-map"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def text(value, label):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 4000:
        raise ValueError(label + " requires non-empty text up to 4000 characters")
    return value.strip()


def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(label + " must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(label + " contains duplicates")
    return list(value)


def local_file(root, name):
    """Only explicit ordinary files inside the requested source root."""
    base, relative = Path(root).resolve(), Path(text(name, "source path"))
    if relative.is_absolute() or ".." in relative.parts or "\\" in name:
        raise ValueError("source path must stay inside its library")
    path = base / relative
    if any(p.is_symlink() for p in [path, *path.parents] if p != base and base in p.parents):
        raise ValueError("atlas source paths must not use symlinks")
    if not path.is_file() or not path.resolve().is_relative_to(base):
        raise ValueError("atlas source is missing: " + name)
    if path.stat().st_size > 16_000_000:
        raise ValueError("atlas source exceeds 16 MB")
    return path


def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


class CreationAtlas:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.records = {}
        self.blueprints = {}
        self.sources = {}
        self._load()

    def source(self, path, selector=None):
        path = Path(path).absolute()
        if path.is_relative_to(self.root):
            scope, base = "machine", self.root
        elif path.is_relative_to(RUNTIME):
            scope, base = "runtime", RUNTIME
        else:
            raise ValueError("atlas source is outside the machine and installed runtime")
        relative = path.relative_to(base).as_posix()
        path = local_file(base, relative)
        key = scope + ":" + relative
        if key not in self.sources:
            self.sources[key] = {"scope": scope, "path": relative,
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return {**self.sources[key], "selector": selector}

    def add(self, identity, category, label, summary, source, *, data=None,
            status="DESCRIPTIVE", relations=None, tags=None):
        identity, category = text(identity, "entry id"), text(category, "category")
        if identity in self.records:
            raise ValueError("duplicate atlas entry: " + identity)
        self.records[identity] = {"id": identity, "category": category,
            "label": text(label, "label"), "summary": str(summary), "source": source,
            "evidence": {"status": status, "execution_observed_by_indexing": False},
            "relations": deepcopy(relations or []), "tags": strings(tags or [], "tags"),
            "data": deepcopy(data or {})}

    def _load(self):
        registry = Registry(self.root)
        for cap in registry.capability_manifests():
            source = self.source(self.root / cap.pop("_manifest_path"))
            relations = [{"relation": "requires", "target": REFERENCE_DEPENDENCIES.get(c, "capability:" + c)}
                         for c in cap.get("dependencies", [])]
            for ref in cap.get("anatomy_refs", []):
                if isinstance(ref, dict) and ref.get("id"):
                    relations.append({"relation": ref.get("role", "references"), "target": "anatomy:" + ref["id"]})
            impl = cap.get("implementation", {})
            pins = []
            if impl.get("source"):
                try:
                    pins.append(self.source(local_file(self.root, impl["source"])))
                except ValueError:
                    # Minimal embedded bodies may load Python from an installed package.
                    candidate = RUNTIME / Path(impl["source"]).name
                    if candidate.is_file():
                        pins.append(self.source(candidate))
            self.add("capability:" + cap["id"], "capability", cap["id"], cap.get("purpose", ""), source,
                     data={**cap, "implementation_sources": pins}, status="INSTALLED_MANIFEST",
                     relations=relations, tags=list(cap.get("handles", [])))

        if registry.master_path.is_file():
            source = self.source(registry.master_path)
            self.add("registry:universal-creation-map", "metadata", "Universal Creation Map v0.1",
                     "Source registry of descriptive anatomy; not a list of implemented capabilities.", source,
                     data={"records": len(registry.master_records())}, status="DESCRIPTIVE_RESEARCH")
            for row in registry.master_records():
                self.add("anatomy:" + row["id"], row.get("level", "knowledge"), row.get("name", row["id"]),
                         row.get("definition", ""), {**source, "selector": row["id"]}, data=row,
                         status="DESCRIPTIVE_RESEARCH", tags=[row.get("domain_code", "unknown")])

        organs = ExecutableOrganLibrary(self.root)
        providers = {}
        for organ in organs.list():
            for interface in organ["provides"]:
                providers.setdefault(interface, []).append("organ:" + organ["ref"])
        for organ in organs.list():
            relations = [{"relation": "requires-interface-provider", "target": target}
                         for interface in organ.get("requires", []) for target in providers.get(interface, [])]
            self.add("organ:" + organ["ref"], "organ", organ["id"], organ.get("purpose", ""),
                     self.source(self.root / organ["source_path"]), data=organ,
                     status="VALIDATED_PACKAGE_FIXTURES_NOT_RUN", relations=relations,
                     tags=list(dict.fromkeys(organ["provides"] + organ.get("requires", []))))

        assets = AssetPackageLibrary(self.root)
        for package in assets.list():
            body = assets.inspect(package["ref"])
            source = self.source(body["source"])
            prefix = "asset:" + package["ref"] + "/"
            for atom in body["atoms"]:
                self.add(prefix + atom["id"], atom["kind"], atom["id"], atom.get("purpose", ""),
                         {**source, "selector": atom["id"]}, data=atom,
                         status="VALIDATED_DESCRIPTOR_RESOURCES_NOT_RESOLVED",
                         relations=[{"relation": "uses", "target": prefix + ref} for ref in atom.get("uses", [])],
                         tags=[body["asset_class"]])

        from .form_pattern import form_pattern_summary
        from .game_material_bridge import MAP_CHANNELS
        from .game_material_styles import FAMILIES
        from .grammar import GRAMMAR_BY_SUFFIX
        from .product_workflow import PROFILES
        for name in form_pattern_summary()["patterns"]:
            self.add("shape:" + name, "shape", name, "Parameterized surface construction pattern",
                     self.source(RUNTIME / "form_pattern.py", name), data={"pattern": name}, status="IMPLEMENTED_GRAMMAR",
                     relations=[{"relation": "realized-by", "target": "capability:AXM-CAP-GENERATE-FORM-PATTERN-3D"}])
        for family in FAMILIES:
            self.add("material:generator:" + family, "material", family, "Procedural material map family",
                     self.source(RUNTIME / "game_material_styles.py", family),
                     data={"recipe": {"family": family, "size": 128, "seed": 1}}, status="IMPLEMENTED_GENERATOR",
                     relations=[{"relation": "realized-by", "target": "capability:AXM-CAP-GENERATE-GAME-MATERIAL"}])
        pack_path = RUNTIME / "data/material_response/pack.json"
        pack = json.loads(pack_path.read_text())
        for family in pack["families"]:
            self.add("material:response:" + family["id"], "material", family["id"], family.get("purpose", ""),
                     self.source(pack_path, family["id"]), data=family, status="RESPONSE_INTENT_RENDERER_NOT_PROVEN",
                     relations=[{"relation": "resolved-by", "target": "capability:AXM-CAP-MATERIAL-RESPONSE-INTENT"}])
        for channel, count in sorted(MAP_CHANNELS.items()):
            self.add("texture:" + channel, "texture", channel, "Material map channel contract",
                     self.source(RUNTIME / "game_material_bridge.py", channel), data={"channels": count},
                     status="IMPLEMENTED_BUNDLE_CHANNEL",
                     relations=[{"relation": "checked-by", "target": "capability:AXM-CAP-INSPECT-GAME-MATERIAL"}])
        for suffix, profile in sorted(GRAMMAR_BY_SUFFIX.items()):
            self.add("file:" + suffix[1:], "file", suffix, "File grammar and available validation",
                     self.source(RUNTIME / "grammar.py", suffix), data=profile, status="DECLARED_VALIDATION_SCOPE")
        for name, profile in sorted(PROFILES.items()):
            self.add("workflow:" + name, "workflow", name, "Product lifecycle, owners and expected evidence",
                     self.source(RUNTIME / "product_workflow.py", name), data=profile, status="LIFECYCLE_CONTRACT",
                     relations=[{"relation": "planned-by", "target": "capability:AXM-CAP-PRODUCT-WORKFLOW"}])
        for filename in ("direction-catalog.json", "axis-catalog.json"):
            path = self.root / "reference/software-directions" / filename
            if path.is_file():
                body = json.loads(local_file(self.root, str(path.relative_to(self.root))).read_text())
                for profile in body.get("profiles", []):
                    self.add("direction:" + profile["id"], "direction", profile["id"], profile.get("purpose", profile.get("name", "")),
                             self.source(path, profile["id"]), data=profile, status="DIRECTION_KNOWLEDGE")
        for path in sorted((self.root / "atlas").glob("*.json")):
            body = json.loads(local_file(self.root, str(path.relative_to(self.root))).read_text())
            if body.get("schema") != PACK_SCHEMA or set(body) - {"schema", "entries", "blueprints"}:
                raise ValueError("invalid creation atlas pack: " + path.name)
            for entry in body.get("entries", []):
                source, data = self.source(path, entry["id"]), deepcopy(entry.get("data", {}))
                if "source_data" in entry:
                    ref = entry["source_data"]
                    source_path = local_file(self.root, ref["path"])
                    data = json.loads(source_path.read_text())
                    for part in ref.get("pointer", []):
                        data = data[part]
                    data = {"value": data}
                    source = {**source, "data_source": self.source(source_path, ref.get("pointer", []))}
                self.add(entry["id"], entry["category"], entry.get("label", entry["id"]), entry.get("summary", ""),
                         source, data=data, status=entry.get("status", "DESCRIPTIVE"),
                         relations=entry.get("relations"), tags=entry.get("tags"))
            for blueprint in body.get("blueprints", []):
                identity = "blueprint:" + text(blueprint.get("id"), "blueprint id")
                self.add(identity, "blueprint", blueprint["id"], blueprint.get("purpose", ""), self.source(path, identity),
                         data=blueprint, status="DECLARED_EXECUTABLE_RECIPE",
                         relations=[{"relation": "uses", "target": ref} for ref in blueprint.get("uses", [])]
                         + [{"relation": "executes", "target": "capability:" + s["capability"]} for s in blueprint.get("steps", [])],
                         tags=[blueprint["direction"], *blueprint.get("goals", {})])
                self.blueprints[blueprint["id"]] = deepcopy(blueprint)

        from .workflow_contracts import load_operators
        operators, _ = load_operators(self.root)
        for identity, operator in operators.items():
            self.add("operator:" + identity, "operator", identity, operator["purpose"],
                     self.source(self.root / operator["source"]["path"], identity), data=operator,
                     status="TYPED_OPERATOR_EXECUTION_REQUIRED",
                     relations=[{"relation": "executes", "target": "capability:" + cap}
                                for cap in [operator["capability"], *operator["dependencies"]]],
                     tags=[operator["provides"]["kind"], *operator["metrics"]])

    def add_experience(self, records, collection):
        """Expose retained observations and semantic construction candidates, not canon."""
        patterns = {}
        for record in records:
            identity = "experience:" + digest(record)
            source = {"scope": "experience", "collection": str(collection), "record_sha256": digest(record)}
            self.add(identity, "experience", record["intent"]["purpose"], record["status"], source,
                     data=record, status="PAST_OBSERVATION_RECHECK_REQUIRED",
                     tags=[record["blueprint"], record["intent"]["direction"]],
                     relations=[{"relation": "used-blueprint", "target": "blueprint:" + record["blueprint"]}])
            if record["status"] == "CHECKS_PASSED":
                for search in record.get("searches", []):
                    patterns.setdefault(search["semantic_signature"], []).append((identity, search))
        for signature, observations in sorted(patterns.items()):
            self.add("construction:" + signature, "construction-pattern", signature,
                     "Measured construction candidate; every reuse needs the current request's checks.",
                     {"scope": "derived-experience", "semantic_signature": signature},
                     data={"observations": [{"experience": identity, **deepcopy(search)} for identity, search in observations]},
                     status="MEASURED_CANDIDATE_NOT_CANON",
                     relations=[{"relation": "observed-in", "target": identity} for identity, _ in observations])

    def summary(self):
        categories = dict(sorted(Counter(r["category"] for r in self.records.values()).items()))
        missing = sorted({edge["target"] for r in self.records.values() for edge in r["relations"]
                          if edge["target"] not in self.records})
        return {"schema": SCHEMA, "entries": len(self.records), "categories": categories,
                "blueprints": sorted(self.blueprints), "snapshot_sha256": digest(self.records),
                "unresolved_references": missing, "indexing_proves_execution": False}

    def get(self, identity):
        if identity not in self.records:
            raise ValueError("unknown atlas entry: " + str(identity))
        return deepcopy(self.records[identity])

    def query(self, query="", categories=None, limit=20):
        if not isinstance(query, str) or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("query requires text and limit 1..100")
        categories = strings(categories or [], "categories")
        wanted, rows = _tokens(query), []
        for row in self.records.values():
            if categories and row["category"] not in categories:
                continue
            words = _tokens(" ".join([row["id"], row["label"], row["summary"], *row["tags"]]))
            score = len(wanted & words)
            if wanted and not score:
                continue
            rows.append((score, row["id"], row))
        rows.sort(key=lambda r: (-r[0], r[1]))
        return {"schema": SCHEMA, "query": query, "matches": len(rows),
                "entries": [{**{k: deepcopy(v) for k, v in row.items() if k != "data"}, "score": score}
                            for score, _, row in rows[:limit]],
                "selection": "Lexical retrieval only; a match does not prove goal sufficiency."}

    def closure(self, identities):
        pending, selected, missing = list(identities), {}, set()
        while pending:
            identity = pending.pop()
            if identity in selected or identity in missing:
                continue
            if identity not in self.records:
                missing.add(identity)
                continue
            row = self.get(identity)
            selected[identity] = row
            pending.extend(edge["target"] for edge in row["relations"])
        return {"entries": [selected[k] for k in sorted(selected)], "missing": sorted(missing)}


def runtime_pin():
    """Pin Python/data dependencies, not just the immediate capability wrapper."""
    hashes = {p.relative_to(RUNTIME).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(RUNTIME.rglob("*")) if p.is_file() and p.suffix in {".py", ".json"}}
    return digest(hashes)
