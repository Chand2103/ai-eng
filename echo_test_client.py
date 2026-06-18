import asyncio
import websockets
import argparse
import time
import sys

async def test_echo(url: str, idle_seconds: int = 120):
    """
    Test WebSocket echo server:
    1. Connect
    2. Send a message and verify echo
    3. Wait idle for specified seconds
    4. Send another message to verify connection still alive
    """
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✓ Connected successfully")
            
            # First message
            test_msg = b"Hello, WebSocket!"
            print(f"Sending first message: {test_msg}")
            await websocket.send(test_msg)
            
            response = await websocket.recv()
            if response == test_msg:
                print(f"✓ First echo received correctly: {response}")
            else:
                print(f"✗ First echo mismatch: expected {test_msg}, got {response}")
                return False
            
            # Idle period
            print(f"\nWaiting {idle_seconds} seconds idle (testing timeout behavior)...")
            start_idle = time.time()
            await asyncio.sleep(idle_seconds)
            idle_duration = time.time() - start_idle
            print(f"✓ Idle period completed ({idle_duration:.1f}s)")
            
            # Second message after idle
            test_msg2 = b"Still connected?"
            print(f"\nSending second message after idle: {test_msg2}")
            await websocket.send(test_msg2)
            
            response2 = await websocket.recv()
            if response2 == test_msg2:
                print(f"✓ Second echo received correctly: {response2}")
            else:
                print(f"✗ Second echo mismatch: expected {test_msg2}, got {response2}")
                return False
            
            print("\n✓ All tests passed - WebSocket connection survived idle period")
            return True
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n✗ Connection closed: {e}")
        print(f"   Code: {e.code}, Reason: {e.reason}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test WebSocket echo server")
    parser.add_argument("--url", type=str, required=True, help="WebSocket URL (e.g., ws://localhost:8000/ws/echo)")
    parser.add_argument("--idle", type=int, default=120, help="Idle seconds to test (default: 120)")
    
    args = parser.parse_args()
    
    success = asyncio.run(test_echo(args.url, args.idle))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
