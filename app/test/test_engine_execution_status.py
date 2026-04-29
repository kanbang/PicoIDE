import asyncio
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

if "cachetools" not in sys.modules:
    cachetools_stub = types.ModuleType("cachetools")

    class LRUCache(dict):
        def __init__(self, maxsize: int = 128):
            super().__init__()
            self.maxsize = maxsize

    cachetools_stub.LRUCache = LRUCache
    sys.modules["cachetools"] = cachetools_stub

if "flow.blocks_manager" not in sys.modules:
    blocks_manager_stub = types.ModuleType("flow.blocks_manager")

    class _BlocksRegistry:
        def get_blocks_with_scripts(self, business, scripts):
            return []

    def _register_static_blocks():
        return None

    def _build_blocks_from_scripts(scripts):
        return []

    blocks_manager_stub.blocks_registry = _BlocksRegistry()
    blocks_manager_stub.register_static_blocks = _register_static_blocks
    blocks_manager_stub.build_blocks_from_scripts = _build_blocks_from_scripts
    sys.modules["flow.blocks_manager"] = blocks_manager_stub

if "flow.engine_manager" not in sys.modules:
    engine_manager_stub = types.ModuleType("flow.engine_manager")

    class EngineManager:
        pass

    engine_manager_stub.EngineManager = EngineManager
    sys.modules["flow.engine_manager"] = engine_manager_stub

from flow.block import Block
from flow.engine import ComputeEngine
from flow.runtime_bus import RuntimeEventBus, RuntimeEventType


class RetrySource(Block):
    NAME = "RetrySource"
    calls = 0

    def __init__(self):
        super().__init__()
        self.add_output("out")

    async def on_compute(self, execution_id: str = None):
        type(self).calls += 1
        if type(self).calls == 1:
            raise RuntimeError("source transient failure")
        self.set_interface("out", {"value": 1})


class StableSource(Block):
    NAME = "StableSource"
    calls = 0

    def __init__(self):
        super().__init__()
        self.add_output("out")

    async def on_compute(self, execution_id: str = None):
        type(self).calls += 1
        self.set_interface("out", {"value": 1})


class CountingSink(Block):
    NAME = "CountingSink"
    calls = 0

    def __init__(self):
        super().__init__()
        self.add_input("inp")

    async def on_compute(self, execution_id: str = None):
        type(self).calls += 1


class FailingSink(Block):
    NAME = "FailingSink"
    calls = 0

    def __init__(self):
        super().__init__()
        self.add_input("inp")

    async def on_compute(self, execution_id: str = None):
        type(self).calls += 1
        raise RuntimeError("sink failure")


class HangingSource(Block):
    NAME = "HangingSource"
    STREAMING = True
    calls = 0

    def __init__(self):
        super().__init__()
        self.add_output("out")

    async def on_compute(self, execution_id: str = None):
        type(self).calls += 1
        self.set_interface("out", {"value": 1})
        await asyncio.sleep(3600)


class EngineExecutionStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        RetrySource.calls = 0
        StableSource.calls = 0
        CountingSink.calls = 0
        FailingSink.calls = 0
        HangingSource.calls = 0

    async def _wait_until_execution_finishes(self, engine: ComputeEngine, execution_id: str):
        for _ in range(200):
            if execution_id not in engine.executions:
                return
            await asyncio.sleep(0.01)
        self.fail(f"Execution {execution_id} did not finish in time")

    async def _collect_event_types(self, execution_id: str):
        bus = RuntimeEventBus()
        events = []
        async for event in bus.subscribe(execution_id):
            events.append(event.type)
        bus.cleanup(execution_id)
        return events

    async def test_source_node_retries_and_execution_completes(self):
        engine = ComputeEngine()
        engine.set_blocks([RetrySource, CountingSink])
        engine.set_flow(
            {
                "nodes": [
                    {
                        "id": "source",
                        "type": "RetrySource",
                        "inputs": {},
                        "outputs": {"out": {"id": "port_source_out"}},
                    },
                    {
                        "id": "sink",
                        "type": "CountingSink",
                        "inputs": {"inp": {"id": "port_sink_in"}},
                        "outputs": {},
                    },
                ],
                "connections": [{"from": "port_source_out", "to": "port_sink_in"}],
            }
        )

        bus = RuntimeEventBus()
        execution_id = "test_retry_source_exec"
        bus.cleanup(execution_id)

        original_sleep = asyncio.sleep

        async def fast_sleep(delay, result=None):
            return await original_sleep(0)

        with patch("flow.engine.asyncio.sleep", new=fast_sleep):
            await engine.run(execution_id)
            await self._wait_until_execution_finishes(engine, execution_id)

        event_types = await self._collect_event_types(execution_id)

        self.assertEqual(RetrySource.calls, 2)
        self.assertEqual(CountingSink.calls, 1)
        self.assertIn(RuntimeEventType.EXECUTION_COMPLETED, event_types)
        self.assertNotIn(RuntimeEventType.EXECUTION_FAILED, event_types)

    async def test_non_source_failure_marks_execution_failed(self):
        engine = ComputeEngine()
        engine.set_blocks([StableSource, FailingSink])
        engine.set_flow(
            {
                "nodes": [
                    {
                        "id": "source",
                        "type": "StableSource",
                        "inputs": {},
                        "outputs": {"out": {"id": "port_source_out"}},
                    },
                    {
                        "id": "sink",
                        "type": "FailingSink",
                        "inputs": {"inp": {"id": "port_sink_in"}},
                        "outputs": {},
                    },
                ],
                "connections": [{"from": "port_source_out", "to": "port_sink_in"}],
            }
        )

        bus = RuntimeEventBus()
        execution_id = "test_non_source_failure_exec"
        bus.cleanup(execution_id)

        await engine.run(execution_id)
        await self._wait_until_execution_finishes(engine, execution_id)

        event_types = await self._collect_event_types(execution_id)

        self.assertEqual(StableSource.calls, 1)
        self.assertEqual(FailingSink.calls, 1)
        self.assertIn(RuntimeEventType.EXECUTION_FAILED, event_types)
        self.assertNotIn(RuntimeEventType.EXECUTION_COMPLETED, event_types)

    async def test_stop_emits_stopped_terminal_event(self):
        engine = ComputeEngine()
        engine.set_blocks([HangingSource])
        engine.set_flow(
            {
                "nodes": [
                    {
                        "id": "source",
                        "type": "HangingSource",
                        "inputs": {},
                        "outputs": {"out": {"id": "port_source_out"}},
                    }
                ],
                "connections": [],
            }
        )

        bus = RuntimeEventBus()
        execution_id = "test_stop_exec"
        bus.cleanup(execution_id)

        await engine.run(execution_id)
        await asyncio.sleep(0.01)
        await engine.stop_execution(execution_id)
        await self._wait_until_execution_finishes(engine, execution_id)

        event_types = await self._collect_event_types(execution_id)

        self.assertGreaterEqual(HangingSource.calls, 1)
        self.assertIn(RuntimeEventType.EXECUTION_STOPPED, event_types)


if __name__ == "__main__":
    unittest.main()
