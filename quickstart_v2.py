import os
import time
from dotenv import load_dotenv
import argparse
from letta import create_client
from .npc_memory_v2.memory import NPCMemoryV2 