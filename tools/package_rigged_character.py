"""Verify a staged character folder and create a portable, checksummed ZIP."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_character(root: Path, archive: Path):
    root=root.resolve()
    archive=archive.resolve()
    if not root.is_dir() or archive.exists() or archive.is_relative_to(root):
        raise ValueError("choose an existing package directory and a new archive outside it")
    manifest=json.loads((root/"character-manifest.json").read_text(encoding="utf-8"))
    rows=[manifest["source"],*manifest["exports"].values(),*manifest["render_proofs"],
          *[clip["fbx"] for clip in manifest["animations"]]]
    for row in rows:
        path=(root/row["path"]).resolve()
        if not path.is_relative_to(root) or sha(path)!=row["sha256"]:
            raise ValueError(f"package artifact does not match manifest: {row['path']}")
    report=json.loads((root/"roundtrip-verification.json").read_text(encoding="utf-8"))
    if report.get("status")!="PASS" or len(report.get("separate_animation_fbx",[]))!=4:
        raise ValueError("complete round-trip verification with four separate animation takes is required")
    for row in report["artifacts"]+report["separate_animation_fbx"]:
        name=Path(row["path"]).name
        path=root/"animations"/name if "clip" in row else root/name
        if sha(path)!=row["sha256"]:
            raise ValueError(f"round-trip evidence is stale: {name}")
    for proof_path in (root/"previews").glob("*-proof.json"):
        proof=json.loads(proof_path.read_text(encoding="utf-8"))
        if proof.get("source_sha256")!=manifest["exports"]["lod0"]["sha256"]:
            raise ValueError(f"motion proof is bound to a different GLB: {proof_path.name}")
    files=sorted(path for path in root.rglob("*") if path.is_file() and path.name!="package-checksums.json")
    if any(not path.resolve().is_relative_to(root) for path in files):
        raise ValueError("package contains a link outside its root")
    checksums={path.relative_to(root).as_posix():sha(path) for path in files}
    checksum_file=root/"package-checksums.json"
    checksum_file.write_text(json.dumps({"schema":"axm.character-package/v0.1","files":checksums,
        "truth":"Package hashes and prior importer checks are not target-engine certification."},indent=2)+"\n",encoding="utf-8")
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in [*files,checksum_file]:
            bundle.write(path,arcname=f"{root.name}/{path.relative_to(root).as_posix()}")
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("archive CRC validation failed")
        for relative,digest in checksums.items():
            if hashlib.sha256(bundle.read(f"{root.name}/{relative}")).hexdigest()!=digest:
                raise ValueError(f"archive content mismatch: {relative}")
    return {"archive":str(archive),"sha256":sha(archive),"bytes":archive.stat().st_size,
            "files":len(files)+1,"status":"PACKAGE_VERIFIED"}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("package",type=Path)
    parser.add_argument("archive",type=Path)
    args=parser.parse_args()
    print(json.dumps(package_character(args.package,args.archive),indent=2))
