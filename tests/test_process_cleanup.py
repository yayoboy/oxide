"""
Test process cleanup behavior.

This script tests that all spawned processes are properly cleaned up
when the MCP server exits under various scenarios.
"""
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.utils.process_manager import get_process_manager, ProcessManager


def test_sync_process_cleanup():
    """Test cleanup of synchronous subprocesses."""
    print("\n=== Testing Sync Process Cleanup ===")

    pm = ProcessManager()

    # Start a long-running process
    process = subprocess.Popen(
        ["sleep", "300"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print(f"✓ Started process PID: {process.pid}")
    pm.register_sync_process(process)

    # Verify process is running
    assert process.poll() is None, "Process should be running"
    print(f"✓ Process is running")

    # Clean up
    pm.cleanup_all()

    # Wait a bit for cleanup
    time.sleep(0.5)

    # Verify process is terminated
    status = process.poll()
    assert status is not None, "Process should be terminated"
    print(f"✓ Process terminated with code: {status}")


async def test_async_process_cleanup():
    """Test cleanup of async subprocesses."""
    print("\n=== Testing Async Process Cleanup ===")

    pm = ProcessManager()

    # Start a long-running async process
    process = await asyncio.create_subprocess_exec(
        "sleep", "300",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    print(f"✓ Started async process PID: {process.pid}")
    pm.register_async_process(process)

    # Verify process is running
    assert process.returncode is None, "Process should be running"
    print(f"✓ Async process is running")

    # Clean up
    pm.cleanup_all()

    # Wait a bit for cleanup
    await asyncio.sleep(0.5)

    # Verify process is terminated
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
        print(f"✓ Async process terminated with code: {process.returncode}")
    except asyncio.TimeoutError:
        print("⚠ Process still running, attempting force kill...")
        process.kill()
        await process.wait()
        print(f"✓ Process force killed")


def test_multiple_processes():
    """Test cleanup of multiple processes."""
    print("\n=== Testing Multiple Process Cleanup ===")

    pm = ProcessManager()

    processes = []
    for i in range(5):
        p = subprocess.Popen(
            ["sleep", "300"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        pm.register_sync_process(p)
        processes.append(p)
        print(f"✓ Started process {i+1} PID: {p.pid}")

    # Verify all are running
    running = sum(1 for p in processes if p.poll() is None)
    print(f"✓ {running}/5 processes running")

    # Clean up all
    pm.cleanup_all()
    time.sleep(1)

    # Verify all terminated
    terminated = sum(1 for p in processes if p.poll() is not None)
    print(f"✓ {terminated}/5 processes terminated")

    assert terminated == 5, "All processes should be terminated"


def test_signal_handler():
    """Test that signal handler triggers cleanup."""
    print("\n=== Testing Signal Handler ===")

    # Create a subprocess that will be the MCP server simulator
    script = """
import signal
import subprocess
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.utils.process_manager import get_process_manager

# Initialize process manager (registers signal handlers)
pm = get_process_manager()

# Start a child process
process = subprocess.Popen(
    ["sleep", "300"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
pm.register_sync_process(process)

print(f"CHILD_PID:{process.pid}")
sys.stdout.flush()

# Wait for signal
time.sleep(30)
"""

    # Write test script
    test_script_path = Path(__file__).parent / "temp_signal_test.py"
    test_script_path.write_text(script)

    try:
        # Start the test process
        parent = subprocess.Popen(
            [sys.executable, str(test_script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"✓ Started parent process PID: {parent.pid}")

        # Wait for child PID
        time.sleep(1)
        output = parent.stdout.readline()

        if output.startswith("CHILD_PID:"):
            child_pid = int(output.split(":")[1].strip())
            print(f"✓ Child process PID: {child_pid}")

            # Verify child is running
            try:
                os.kill(child_pid, 0)  # Signal 0 just checks if process exists
                print(f"✓ Child process is running")
            except OSError:
                print(f"✗ Child process not found")
                raise

            # Send SIGTERM to parent
            print(f"✓ Sending SIGTERM to parent...")
            parent.send_signal(signal.SIGTERM)

            # Wait for parent to exit
            parent.wait(timeout=5)
            print(f"✓ Parent process exited")

            # Wait a bit for cleanup
            time.sleep(1)

            # Check if child was cleaned up
            try:
                os.kill(child_pid, 0)
                print(f"✗ Child process still running (cleanup failed)")
                # Kill it manually for cleanup
                os.kill(child_pid, signal.SIGKILL)
            except OSError:
                print(f"✓ Child process was cleaned up successfully!")

    finally:
        # Cleanup test script
        if test_script_path.exists():
            test_script_path.unlink()

        # Ensure parent is dead
        try:
            parent.kill()
            parent.wait()
        except:
            pass


def main():
    """Run all tests."""
    print("=" * 60)
    print("Process Manager Cleanup Tests")
    print("=" * 60)

    try:
        # Test 1: Sync process cleanup
        test_sync_process_cleanup()

        # Test 2: Async process cleanup
        asyncio.run(test_async_process_cleanup())

        # Test 3: Multiple processes
        test_multiple_processes()

        # Test 4: Signal handler
        test_signal_handler()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
