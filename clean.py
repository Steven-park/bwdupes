from urllib.parse import urlsplit, urlunsplit
import json
import re
import ping3
import requests

# Constants for file names
input_file_name = "t.json"  # Replace this with your export file from Bitwarden
output_file_name = f"{input_file_name.replace('.json', '_output.json')}"
deleted_file_name = f"{input_file_name.replace('.json', '_deleted.json')}"

# Load data from the input file
with open(input_file_name, 'r') as input_file:
    data = json.load(input_file)

# Initialize variables
processed_items = 0
total_items = len(data['items'])
duplicates = {}  # Initialize duplicates as a dictionary
deleted_items = []
ip_address_pattern = r'\b(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d{1,5})?)\b'
tld_pattern = r'^(?:[a-zA-Z0-9-]+\.)+([a-zA-Z0-9-]+\.[a-zAZ]+)(?::\d+)?$'

def add_https_to_uri(uri):
    if uri.startswith("http://"):
        return uri
    elif uri.startswith("https://"):
        return uri
    else:
        return "https://" + uri

def get_final_redirect_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def is_url_reachable(address):
    try:
        response_time = ping3.ping(address, timeout=5)
        return response_time is None or response_time
    except Exception as e:
        print(f"Error while pinging URL: {address}, Error: {e}")
        return False

def get_valid_url(uri):
    if not uri:
        return None

    uri = add_https_to_uri(uri)
    uri_parts = urlsplit(uri)
    scheme, netloc, path, _, _ = uri_parts
    clean_uri = urlunsplit((scheme, netloc, path, '', ''))

    if netloc == '':
        return uri

    print(f"> Processing: [{scheme}]:[{netloc}]:[{path}]")

    if re.match(ip_address_pattern, netloc) is not None:
        print(f"> Matched IP Address for: {clean_uri}")
        return clean_uri    
    print(f"> Failed matching IP Address for: {netloc}")

    if is_url_reachable(netloc):
        print(f"> Found reachable domain for: {clean_uri}")
        return clean_uri
    print(f"> Failed pinging: {netloc}")

    tld = urlunsplit((scheme, netloc, '', '', ''))
    clean_uri = get_final_redirect_url(tld)
    if clean_uri is not None: 
        print(f"> Found reachable redirect for {tld} to {clean_uri}")
        return clean_uri        
    print(f"> Skipping unreachable URL for: {tld}")
    return None

def get_tld(netloc):
    match = re.search(tld_pattern, netloc)
    if match:
        return match.group(1)
    else:
        return None

items_copy = data['items'][:]

for item in items_copy:
    item_name = item['name']
    print(f"Processing item ({processed_items}/{total_items}): {item_name}")

    # Check if the item has a "login" field
    if 'login' not in item or not isinstance(item['login'], dict):
        print("> Skipping item as it does not have a 'login' field")
        processed_items += 1
        continue

    uris = item['login']['uris']
    username = item['login']['username']
    password = item['login']['password']

    # Ensure uris, username, and password are not None
    if uris is None or username is None or password is None:
        print("> Skipping item as it has missing data")
        processed_items += 1
        continue

    corrected_uris = []
    uri_keys = []
    for uri_data in uris:
        uri = uri_data['uri']
        if uri is None:
            continue

        url = add_https_to_uri(uri)
        uri_parts = urlsplit(url)
        scheme, netloc, path, _, _ = uri_parts        
        if not netloc:
            corrected_uris.append({"uri": uri})
            uri_keys.append(uri)
            continue

        clean_uri = urlunsplit((scheme, netloc, path, '', ''))
        valid_uri = get_valid_url(clean_uri)
        if valid_uri is not None:
            corrected_uris.append({"uri": valid_uri})
            uri_keys.append(netloc)
            continue

        tld = get_tld(netloc)
        clean_uri = urlunsplit((scheme, tld, path, '', ''))
        valid_uri = get_valid_url(clean_uri)
        if valid_uri and tld:
            print(f"> Keeping item since TLD is still valid: {valid_uri}")
            corrected_uris.append({"uri": valid_uri})
            uri_keys.append(tld)
        else:
            print(f"> TLD is invalid: {clean_uri}")

    # Only check for duplicates now (not based on URI validity)
    item_key = f"{username}_{password}_{'|'.join(sorted(uri_keys))}"
    
    reason_for_deletion = ""
    if len(corrected_uris) == 0:
        print(f"> Item {item_name} has no valid URIs, but will not be deleted")
    else:
        item['login']['uris'] = corrected_uris

        # Check if the item is a duplicate based on the item_key
        if item_key in duplicates:
            reason_for_deletion = f"Duplicate of {duplicates[item_key]}"
        else:
            duplicates[item_key] = item_name

    # Only delete if it's a duplicate
    if reason_for_deletion:
        print(f"> Removing item: {item_name} due to {reason_for_deletion}")
        deleted_items.append({**item, "reasonForDeletion": reason_for_deletion})
        data['items'].remove(item)

    # Save the data and deleted items in real-time
    with open(output_file_name, 'w') as output_file:
        json.dump(data, output_file, indent=2)

    with open(deleted_file_name, 'w') as deleted_file:
        json.dump(deleted_items, deleted_file, indent=2)

    processed_items += 1

# Save the final data with updated and deleted items
with open(output_file_name, 'w') as output_file:
    json.dump(data, output_file, indent=2)

print(f"Processed {processed_items} items out of {total_items}.")
print(f"Deleted items: {len(deleted_items)}")
