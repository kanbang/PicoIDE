import asyncio
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import platform

# Windows 下必须使用 SelectorEventLoop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 导入新的客户端 API
from client_api import IOClient, ModbusConfig, ModbusWriteRequest, ModbusSubscribeTask, ModbusSubscribeRequest
from config_loader import config


async def test_modbus_write():
    """测试 Modbus 写操作 - 使用辅助类"""
    print("=" * 50)
    print("测试 Modbus 写操作（使用辅助类）")
    print("=" * 50)

    client = IOClient()

    try:
        # 创建 Modbus 配置
        mb_config = ModbusConfig(host='127.0.0.1', port=502)

        # 使用辅助类创建写请求
        write_req = ModbusWriteRequest(
            config=mb_config,
            slave=1,
            addr=10,
            val=999,
            dtype='uint16'
        )

        print(f"发送写请求: {write_req.to_dict()}")

        # 执行写操作
        result = await client.modbus_write(write_req)
        print(f"写操作结果: {result}")

    except Exception as e:
        print(f"Modbus 写测试失败: {e}")
    finally:
        client.close()


async def test_modbus_subscribe():
    """测试 Modbus 订阅操作 - 使用辅助类"""
    print("\n" + "=" * 50)
    print("测试 Modbus 订阅操作（使用辅助类）")
    print("=" * 50)

    client = IOClient()

    try:
        # 创建 Modbus 配置
        mb_config = ModbusConfig(host='127.0.0.1', port=502)

        # 创建订阅任务列表
        tasks = [
            ModbusSubscribeTask(addr=10, dtype='uint16'),
            ModbusSubscribeTask(addr=11, dtype='uint16'),
            ModbusSubscribeTask(addr=12, dtype='uint16'),
        ]

        # 使用辅助类创建订阅请求
        sub_req = ModbusSubscribeRequest(
            config=mb_config,
            slave=1,
            tasks=tasks
        )

        print(f"发送订阅请求: {sub_req.to_dict()}")

        # 执行订阅
        result = await client.modbus_subscribe(sub_req)
        print(f"订阅结果: {result}")

    except Exception as e:
        print(f"Modbus 订阅测试失败: {e}")
    finally:
        client.close()


async def test_convenience_methods():
    """测试便捷方法"""
    print("\n" + "=" * 50)
    print("测试便捷方法")
    print("=" * 50)

    client = IOClient()

    try:
        # 使用便捷方法写寄存器
        mb_config = ModbusConfig(host='127.0.0.1', port=502)

        result = await client.write_register(
            config=mb_config,
            slave=1,
            addr=20,
            val=1234,
            dtype='uint16'
        )
        print(f"便捷写操作结果: {result}")

        # 使用便捷方法订阅多个寄存器
        result = await client.subscribe_registers(
            config=mb_config,
            slave=1,
            addresses=[30, 31, 32],
            dtype='uint16'
        )
        print(f"便捷订阅结果: {result}")

    except Exception as e:
        print(f"便捷方法测试失败: {e}")
    finally:
        client.close()


async def test_can_receive():
    """测试 CAN 接收"""
    print("\n" + "=" * 50)
    print("测试 CAN 接收")
    print("=" * 50)

    client = IOClient()

    try:
        print("开始监听 CAN 帧 (接收 3 帧)...")

        for i in range(3):
            frame = await client.can_receive()
            print(f"[{i+1}] CAN Frame: {frame}")

    except Exception as e:
        print(f"CAN 测试失败: {e}")
    finally:
        client.close()


async def main():
    """主测试函数"""
    print("PicoIDE IO 客户端测试")
    print(f"序列化方式: {config.serialization}")
    print()

    # 运行所有测试
    await test_modbus_write()
    await test_modbus_subscribe()
    await test_convenience_methods()
    # await test_can_receive()

    print("\n" + "=" * 50)
    print("所有测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())