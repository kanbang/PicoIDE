import asyncio
import importlib.util
from pathlib import Path
import sys
import unittest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

MODULE_PATH = APP_ROOT / "flow" / "runtime_bus.py"
SPEC = importlib.util.spec_from_file_location("test_runtime_bus_module", MODULE_PATH)
runtime_bus = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runtime_bus)

RuntimeEvent = runtime_bus.RuntimeEvent
RuntimeEventBus = runtime_bus.RuntimeEventBus
RuntimeEventType = runtime_bus.RuntimeEventType


class RuntimeEventBusTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bus = RuntimeEventBus()

    def tearDown(self):
        self.bus.cleanup("test_broadcast_exec")
        self.bus.cleanup("test_replay_exec")
        self.bus.cleanup("test_terminal_exec")
        self.bus.cleanup("test_cleanup_exec")

    async def test_same_execution_broadcasts_to_multiple_subscribers(self):
        execution_id = "test_broadcast_exec"
        self.bus.cleanup(execution_id)

        async def read_one():
            async for event in self.bus.subscribe(execution_id):
                return event

        subscriber_one = asyncio.create_task(read_one())
        subscriber_two = asyncio.create_task(read_one())

        await asyncio.sleep(0)

        expected = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.STATUS,
            source="test",
            message="running",
            data={"status": "running"},
        )
        await self.bus.emit(expected)

        event_one, event_two = await asyncio.gather(subscriber_one, subscriber_two)

        self.assertEqual(event_one, expected)
        self.assertEqual(event_two, expected)
        self.assertEqual(event_one.ts, event_two.ts)

    async def test_late_subscriber_receives_cached_history(self):
        execution_id = "test_replay_exec"
        self.bus.cleanup(execution_id)

        status_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.STATUS,
            source="engine",
            message="started",
            data={"status": "running"},
        )
        file_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.FILE,
            source="viewer",
            message="Generated file: demo.html",
            data={"file": {"file_id": "f1", "filename": "demo.html"}},
        )

        await self.bus.emit(status_event)
        await self.bus.emit(file_event)

        received = []

        async def read_two():
            async for event in self.bus.subscribe(execution_id):
                received.append(event)
                if len(received) == 2:
                    break

        await asyncio.wait_for(read_two(), timeout=1)

        self.assertEqual(received, [status_event, file_event])

    async def test_terminal_execution_replays_and_finishes_without_waiting_for_live_events(self):
        execution_id = "test_terminal_exec"
        self.bus.cleanup(execution_id)

        status_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.STATUS,
            source="engine",
            message="started",
            data={"status": "running"},
        )
        completed_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.EXECUTION_COMPLETED,
            source="engine",
            message="Execution completed",
            data={"duration": 0.2},
        )

        await self.bus.emit(status_event)
        await self.bus.emit(completed_event)

        received = []
        async for event in self.bus.subscribe(execution_id):
            received.append(event)

        self.assertEqual(received, [status_event, completed_event])

    async def test_cleanup_closes_live_subscribers(self):
        execution_id = "test_cleanup_exec"
        self.bus.cleanup(execution_id)

        finished = asyncio.Event()

        async def consume():
            async for _event in self.bus.subscribe(execution_id):
                pass
            finished.set()

        task = asyncio.create_task(consume())
        await asyncio.sleep(0)

        self.bus.cleanup(execution_id)

        await asyncio.wait_for(finished.wait(), timeout=1)
        await asyncio.wait_for(task, timeout=1)


if __name__ == "__main__":
    unittest.main()
