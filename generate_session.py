# Run this FIRST on your PC to generate felix_session.session file
# python generate_session.py

from telethon.sync import TelegramClient

API_ID = 34635054
API_HASH = 'b8e93ca4f3abdcba65cc020504f82f08'

print("="*50)
print("FELIX SESSION GENERATOR")
print("="*50)
print("Apna phone number enter karo (with country code)")
print("Example: +919876543210")
print("="*50)

with TelegramClient('felix_session', API_ID, API_HASH) as client:
    print("\n✅ Login successful!")
    print("✅ felix_session.session file ban gayi!")
    print("\nAb ye file Render pe upload karo.")
