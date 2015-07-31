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
    if 'login' in url and not decoded['isAuthenticated']:
        print("Wrong username or password!")
        print(response, file=sys.stderr)
        sys.exit(1)
    return decoded

def merge_list(key, master, latest, complain=False):
    # If a list is called "entries", the unique index is "entryId".
    # If a list is called "sleeps", the unique index is "sleepId".
    index = key
    index = index.replace('iesTo','yTo')
    index = index.replace('sTo','To')
    if index.endswith('ies'):
        index = "%syId" % (index[:-3])
    elif index.endswith('s'):
        index = "%sId" % (index[:-1])
    else:
        print("How do I merge key '%s'?" % (key), file=sys.stderr)
        sys.exit(1)

    # Find existing positions.
    ids = dict()
    for pos in range(len(master)):
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
        if not key in master:
            master[key] = latest[key]
        if isinstance(latest[key], dict):
            merge(master[key], latest[key], complain)
        elif isinstance(latest[key], list):
            merge_list(key, master[key], latest[key], complain)
        elif master[key] != latest[key]:
            if complain:
                print("Mismatch for id %s key %s master:%s latest:%s", query['entryId'], key, master[key], latest[key], file=sys.stderr)
            else:
                master[key] = latest[key]

try:
    email = sys.argv[1]
    password = sys.argv[2]
    datafile = None
    if len(sys.argv) > 3:
        datafile = sys.argv[3]
except:
    print("Usage: %s EMAIL PASSWORD [DATA.json]\n", sys.argv[0])
    sys.exit(1)

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
         'version': '2.0.8',
         'locale': 'en-US',
}

query = dict(common)
query['email'] = email
query['password'] = password

print("Fetching session ...", file=sys.stderr)
login = fetch("http://app.elitehrv.com/application/index/login", headers=headers, data=query)

# Refresh dict with latest values.
merge(data, login)

# Install authenticated session.
common['sessionId'] = data['sessionId']

# Fetch full entry details for each entry.
count = 0
for entry in data['entries']:
    count += 1
    # Assume that if we have rrs in the entry, it's already up to date.
    if 'rrs' in entry:
        continue

    query = dict(common)
    query['entryId'] = entry['entryId']

    print("Fetching entry %d ..." % (entry['entryId']), file=sys.stderr)
    detailed = fetch("http://app.elitehrv.com/application/entry/get", headers=headers, data=query)

    # I would expect only to _add_ the rrs or other missing fields, so complain if not.
    merge(entry, detailed['entry'], complain=True)

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
    os.link(datafile, old)
    os.rename(new, datafile)
