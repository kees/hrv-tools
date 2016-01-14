#!/usr/bin/env python3
# EliteHRV is fantastic, but doesn't have a very good export method. This fetches the raw JSON.
# Sad that it's not over https, though it made traffic analysis easier! ;)
# © 2015 Kees Cook <kees@ubuntu.com>
# License: GPLv3
import os, sys, requests, json

def fetch(url, headers, data):
    req = requests.post(url, headers=headers, data=data)
    response = req.content.decode("utf-8")
    if req.status_code != 200:
        print("%d %s" % (req.status_code, req.reason), file=sys.stderr)
        print(response, file=sys.stderr)
        sys.exit(1)
    try:
        decoded = json.loads(response)
    except:
        print(response, file=sys.stderr)
        raise
    if 'login' in url and not decoded.get('isAuthenticated',None):
        print("Wrong username or password!")
        print(response, file=sys.stderr)
        sys.exit(1)
    return decoded

def merge_list(key, master, latest, complain=False):
    # If a list is called "entries", the unique index is "entryId".
    # If a list is called "sleeps", the unique index is "sleepId".
    #index = key
    #index = index.replace('iesTo','yTo')
    #index = index.replace('sTo','To')
    #if index.endswith('ies'):
    #    index = "%syId" % (index[:-3])
    #elif index.endswith('s'):
    #    index = "%sId" % (index[:-1])
    #else:
    #    print("How do I merge key '%s'?" % (key), file=sys.stderr)
    #    sys.exit(1)
    index = 'id'

    # Find existing positions.
    ids = dict()
    for pos in range(len(master)):
        if not master[pos].get(index,None):
            raise ValueError("Missing index '%s' in '%s':\n%s" % (index,
                             key, json.dumps(master[pos], sort_keys=True,
                                             indent=4)))
        ids[master[pos][index]] = pos
    # Merge matching Ids.
    for pos in range(len(latest)):
        newid = latest[pos][index]
        if newid in ids:
            merge(master[ids[newid]], latest[pos], complain)
        else:
            master.append(latest[pos])

def merge(master, latest, complain=False):
    for key in latest:
        # Handle "tags" list separately, as it's always complete and updated.
        if key == "tags":
            master[key] = latest[key]
            continue

        if not master.get(key, None):
            master[key] = latest[key]
        if isinstance(latest[key], dict):
            merge(master[key], latest[key], complain)
        elif isinstance(latest[key], list):
            merge_list(key, master[key], latest[key], complain)
        elif master[key] != latest[key]:
            if complain:
                print("Mismatch for id %s key %s master:%s latest:%s" % (query['id'], key, master[key], latest[key]), file=sys.stderr)
            else:
                master[key] = latest[key]

conffile = open(os.path.expanduser("~/.config/elitehrv.conf"))
for line in conffile:
    line = line.strip()
    name, value = line.split('=')
    if name == "username":
        email = value
    elif name == "password":
        password = value
    else:
        raise ValueError("Unknown configuration option '%s'" % (name))

datafile = None
if len(sys.argv) > 1:
    if sys.argv[1] in ["-h", "--help"]:
        print("Usage: %s [DATA.json]\n", sys.argv[0])
        sys.exit(1)
    datafile = sys.argv[1]

if datafile:
    try:
        data = json.load(open(datafile))
        count = len(data['entries'])
        print("Loaded %d entr%s." % (count, "y" if count == 1 else "ies"), file=sys.stderr)
    except FileNotFoundError:
        data = dict()
else:
    data = dict()

headers = {'user-agent': '''Mozilla/5.0 (Linux; Android 5.1.1; Nexus 5 Build/LMY48B; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/43.0.2357.121 Mobile Safari/537.36'''}

common = { 'deviceModel': 'Nexus 5',
         'devicePlatform': 'Android',
         'deviceVersion': '5.1.1',
         'version': '3.7.2',
         'locale': 'en-US',
}

query = dict(common)
query['email'] = email
query['password'] = password

print("Fetching session ...", file=sys.stderr)
login = fetch("http://app.elitehrv.com/application/index/login", headers=headers, data=query)

if data.get('entries', None):
    print("Performing full refresh for v3 protocol update...")
    os.rename(datafile, '%s.v2' % (datafile))
    data = dict()

# Refresh dict with latest values.
#print(json.dumps(login, sort_keys=True, indent=4))
merge(data, login)

# Install authenticated session.
common['sessionId'] = data['sessionId']

# Fetch full entry details for each entry.
count = 0
for entry in data['readings']:
    count += 1
    # Assume that if we have rrs in the entry, it's already up to date.
    if entry.get('rrs',None):
        continue

    query = dict(common)
    query['id'] = entry['id']

    print("Fetching reading %d ..." % (entry['id']), file=sys.stderr)
    detailed = fetch("http://app.elitehrv.com/application/reading/get", headers=headers, data=query)

    #print(json.dumps(detailed['reading'], sort_keys=True, indent=4))
    # I would expect only to _add_ the rrs or other missing fields, so complain if not.
    merge(entry, detailed['reading'], complain=True)

if datafile:
    output = open("%s.new" % (datafile), "w")
else:
    output = sys.stdout

print(json.dumps(data, sort_keys=True, indent=4), file=output)
print("Wrote %d entr%s." % (count, "y" if count == 1 else "ies"), file=sys.stderr)

if datafile:
    new = '%s.new' % (datafile)
    old = '%s.old' % (datafile)
    if os.path.exists(old):
        os.unlink(old)
    if os.path.exists(datafile):
        os.link(datafile, old)
    os.rename(new, datafile)
