import json

# Constants for input and output file names
deleted_file_name = "t_deleted.json"  # The file containing deleted items
output_readable_file_name = "t_deleted_readable.txt"  # The output readable file

# Load deleted items from the JSON file
try:
    with open(deleted_file_name, 'r') as deleted_file:
        deleted_items = json.load(deleted_file)
except FileNotFoundError:
    print(f"Error: File '{deleted_file_name}' not found.")
    exit()
except json.JSONDecodeError:
    print(f"Error: Failed to parse JSON from '{deleted_file_name}'.")
    exit()

# Prepare the readable format
output_lines = []
output_lines.append("Deleted Items Report")
output_lines.append("=" * 50)
output_lines.append("\n")

for idx, item in enumerate(deleted_items, start=1):
    item_name = item.get("name", "Unknown Name")
    reason_for_deletion = item.get("reasonForDeletion", "No reason provided")
    username = item.get("login", {}).get("username", "N/A")
    password = item.get("login", {}).get("password", "N/A")
    uris = item.get("login", {}).get("uris", [])

    # Add item details to output
    output_lines.append(f"Item {idx}: {item_name}")
    output_lines.append(f"  Reason for Deletion: {reason_for_deletion}")
    output_lines.append(f"  Username: {username}")
    output_lines.append(f"  Password: {password}")
    if uris:
        output_lines.append("  URIs:")
        for uri in uris:
            output_lines.append(f"    - {uri.get('uri', 'Unknown URI')}")
    else:
        output_lines.append("  URIs: None")
    output_lines.append("\n")

# Write to the output file
try:
    with open(output_readable_file_name, 'w') as output_file:
        output_file.write("\n".join(output_lines))
    print(f"Readable format saved to '{output_readable_file_name}'.")
except IOError as e:
    print(f"Error writing to file '{output_readable_file_name}': {e}")
