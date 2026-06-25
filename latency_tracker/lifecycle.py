from .db import save_digests, load_digests
from .middleware import digest_map


def shutdown():
    save_digests(digest_map)
    print("saved to db")


def startup():
    loaded = load_digests()
    digest_map.update(loaded)
   