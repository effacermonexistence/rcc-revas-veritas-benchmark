#!/usr/bin/env python3
"""Validate the declared native profile's installed dependency closure.

Only active requirements/extras in this profile are traversed. Unrelated packages
in a host environment are neither validated nor claimed conflict-free. Native
source trees are checked separately, not installed as their full production extras.
"""
from __future__ import annotations
import json
from importlib import metadata
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT=Path(__file__).resolve().parents[1]

def check_profile(path):
    queue=[(Requirement(line), 'native-profile') for line in Path(path).read_text().splitlines()
           if line.strip() and not line.lstrip().startswith('#')]
    seen=set();packages={};errors=[]
    while queue:
        requirement,owner=queue.pop()
        key=canonicalize_name(requirement.name)
        try:dist=metadata.distribution(requirement.name)
        except metadata.PackageNotFoundError:
            errors.append({'owner':owner,'requirement':str(requirement),'error':'MISSING'});continue
        if requirement.specifier and not requirement.specifier.contains(dist.version,prereleases=True):
            errors.append({'owner':owner,'requirement':str(requirement),'installed':dist.version,'error':'VERSION_CONFLICT'})
        packages[key]=dist.version
        extras=frozenset(requirement.extras)|{''}
        for extra in extras:
            if (key,extra) in seen:continue
            seen.add((key,extra))
            for text in dist.requires or ():
                child=Requirement(text)
                if child.marker is None or child.marker.evaluate({'extra':extra}):queue.append((child,key))
    # Deduplicate diagnostics while preserving exact constraints.
    unique={json.dumps(e,sort_keys=True):e for e in errors}
    return {'status':'PASS' if not unique else 'FAIL','scope':'DECLARED_NATIVE_PROFILE_ACTIVE_DEPENDENCY_CLOSURE',
            'package_count':len(packages),'packages':dict(sorted(packages.items())),
            'errors':list(unique.values()),'entire_host_environment_checked':False}
if __name__=='__main__':
    report=check_profile(ROOT/'requirements-native.txt')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='PASS' else 2)
