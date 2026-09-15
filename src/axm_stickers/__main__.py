"""Independent registry CLI: JSON in/out, no UC import or runtime needed."""
import argparse
import json
from pathlib import Path
from .core import Registry, instance
from .assembly import save_assembly, library_bundle, import_library


def main(argv=None):
    parser = argparse.ArgumentParser(description='Portable local sticker registry')
    parser.add_argument('database',type=Path)
    parser.add_argument('request',type=Path)
    args = parser.parse_args(argv)
    with args.request.open('rb') as handle: raw = handle.read(48*1024*1024+1)
    if len(raw) > 48*1024*1024: parser.error('request exceeds 48 MiB')
    request = json.loads(raw)
    if not isinstance(request,dict): parser.error('request must be an object')
    operation = request.pop('operation',None)
    if operation not in {'search','get','register','register_many','bundle','import_bundle','save_assembly','library_bundle','import_library','instance'}:
        parser.error('unknown operation')
    with Registry(args.database) as registry:
        functions={'save_assembly':save_assembly,'library_bundle':library_bundle,'import_library':import_library}
        if operation in functions: result=functions[operation](registry,**request)
        elif operation=='instance':
            d=registry.get(request.pop('sticker_id'),request.pop('version'))
            result=instance(d,**request)
        else: result = getattr(registry,operation)(**request)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__ == '__main__': main()
