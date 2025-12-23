#!/usr/bin/env python3
"""Test SSE flow for note creation without refresh."""

import asyncio

import httpx

BASE_URL = "http://localhost:8000"


async def test_sse_flow():
    async with httpx.AsyncClient() as client:
        # 1. Register/login to get cookie
        print("1. Registering user...")
        response = await client.post(
            f"{BASE_URL}/register",
            data={"username": "sse_test_user", "password": "testpass123"},
        )
        print(f"   Status: {response.status_code}")

        # 2. Check home page loads
        print("\n2. Loading home page...")
        response = await client.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")

        # 3. Create a text note
        print("\n3. Creating a text note...")
        response = await client.post(
            f"{BASE_URL}/web/notes/text",
            data={"text": "Test note for SSE flow verification"},
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Note HTML returned: {len(response.text)} chars")

        # 4. Get recent notes
        print("\n4. Getting recent notes...")
        response = await client.get(f"{BASE_URL}/web/notes/recent")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Notes HTML returned: {len(response.text)} chars")
            if "Test note" in response.text:
                print("   ✓ Note found in recent notes")
            else:
                print("   ✗ Note not found in recent notes")


if __name__ == "__main__":
    asyncio.run(test_sse_flow())
