import letta_client
from pprint import pprint

# Print all available modules and classes
print("Available in letta_client:")
pprint(dir(letta_client))

# Get more detailed info about the Letta class
print("\nLetta class details:")
help(letta_client.Letta)

# Try to find config/model related modules
for item in dir(letta_client):
    if any(x in item.lower() for x in ['config', 'model', 'memory', 'schema']):
        print(f"\nFound potential match: {item}")
        try:
            help(getattr(letta_client, item))
        except:
            pass
