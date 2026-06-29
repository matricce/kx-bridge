#!/usr/bin/env python3
import sys, json
tag, version, body_file = sys.argv[1], sys.argv[2], sys.argv[3]
body = open(body_file).read()
payload = json.dumps({
    "tag_name": tag,
    "name": "KX-Bridge " + version + " Nightly",
    "body": body,
    "draft": False,
    "prerelease": True
})
open("/tmp/release_body.json", "w").write(payload)
