"""Prepare supported static output without transforming tested browser assets."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
source=root/'web';target=root/'dist'
target.mkdir(exist_ok=True)
files={p.relative_to(source) for p in source.rglob('*') if p.is_file()}
# Only remove stale individual output files after resolving the exact boundary.
for p in target.rglob('*'):
 if p.is_file() and p.relative_to(target) not in files:
  assert p.resolve().is_relative_to(target.resolve())
  p.unlink()
for relative in files:
 out=target/relative;out.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source/relative,out)
 assert hashlib.sha256(out.read_bytes()).digest()==hashlib.sha256((source/relative).read_bytes()).digest()
print(json.dumps({'static_directory':'dist','byte_identical_assets':len(files)}))
