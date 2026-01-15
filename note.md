
### python Block class

``` py
import uuid
import inspect
from types import MethodType
from typing import Callable, Any, Dict, List, Type
from dataclasses import asdict, dataclass, field
from flow.block.option import BlockOption, BlockOptionValue
from flow.block.interface import BlockInterface, IT, is_valid_interface_type


@dataclass
class Block:
    # Public fields
    name: str = "Block"

    # Private fields (excluded from init and compare)
    _type: str = field(init=False, repr=False, compare=False)
    _inputs: Dict[str, BlockInterface] = field(
        init=False, default_factory=dict, compare=False
    )
    _outputs: Dict[str, BlockInterface] = field(
        init=False, default_factory=dict, compare=False
    )
    _options: Dict[str, BlockOption] = field(
        init=False, default_factory=dict, compare=False
    )
    _state: Dict[str, object] = field(
        init=False, default_factory=lambda: {"info": None}, repr=False, compare=False
    )
    _interface_names: List[str] = field(
        init=False, default_factory=list, repr=False, compare=False
    )

    def __post_init__(self):
        """
        Post-initialization to set up private fields based on the given `name`.
        """
        # Generate a unique name if the default is used
        if self.name == "Block":
            self.name = f"Block_{str(uuid.uuid4()).replace('-', '_')}"

        # Set the type to match the name
        self._type = self.name

    def add_input(self, name: str = None, interface_type: Type[IT] = Any) -> None:
        """
        Add an Input interface to the Block

        Args:
            name (str, optional): The name of the Input interface. If None, a default name will be generated.
            interface_type (Type[IT], optional): The type of the interface. Defaults to Any.
                Must be a Python built-in type, typing module type, or dataclass.

        Raises:
            ValueError: If the name already exists as an interface to the Block.
            TypeError: If the interface_type is not a valid type.

        Examples:
            >>> block.add_input(name='Input Name', interface_type=int)
        """
        is_valid_interface_type(interface_type)

        if name is None:
            name = f"Input {len(self._inputs) + 1}"

        if name in self._interface_names:
            raise ValueError(
                f"name: {name} already exists as an interface to the Block."
            )

        self._inputs[name] = BlockInterface[interface_type](name=name)
        self._interface_names.append(name)

    def add_output(self, name: str = None, interface_type: Type[IT] = Any) -> None:
        """
        Add an Output interface to the Block

        Args:
            name (str, optional): The name of the Output interface. If None, a default name will be generated.
            interface_type (Type[IT], optional): The type of the interface. Defaults to Any.
                Must be a Python built-in type, typing module type, or dataclass.

        Raises:
            ValueError: If the name already exists as an interface to the Block.
            TypeError: If the interface_type is not a valid type.

        Examples:
            >>> block.add_output(name='Output Name', interface_type=str)
        """
        is_valid_interface_type(interface_type)

        if name is None:
            name = f"Output {len(self._outputs) + 1}"

        if name in self._interface_names:
            raise ValueError(
                f"name: {name} already exists as an interface to the Block."
            )

        self._outputs[name] = BlockInterface[interface_type](name=name)
        self._interface_names.append(name)

    def get_interface(self, name: str):
        """
        Get the value of a given interface.

        Args:
            name (str): The name of the interface.

        Returns:
            The value of the interface.

        Raises:
            ValueError: If no interface with the given name is found.
        """
        if name in self._inputs:
            return self._inputs[name].value
        elif name in self._outputs:
            return self._outputs[name].value
        else:
            raise ValueError(f"No interface with name: {name} found for Block")

    def set_interface(self, name: str, value) -> None:
        """
        Set the value for a given interface.

        Args:
            name (str): The name of the interface.
            value: The value to set for the interface.

        Raises:
            ValueError: If no interface with the given name is found.
        """
        if name in self._inputs:
            self._inputs[name].set_value(value)
        elif name in self._outputs:
            self._outputs[name].set_value(value)
        else:
            raise ValueError(f"No interface with name: {name} found for Block")

    def set_state(self, key: str, value: Any) -> None:
        """
        Set a state value for the block.
        Reserved keys: ['info']

        Args:
            key (str): The key for the state value.
            value (Any): The value to set for the state.

        Raises:
            ValueError: If the key is a reserved state key.
        """
        reserved_state_keys = ["info"]
        if key in reserved_state_keys:
            raise ValueError(
                f"Key: {key} used for setting state of block is reserved. Use another key."
            )
        else:
            self._state[key] = value

    def get_state(self, key: str) -> Any:
        """
        Get a state value for the block.

        Args:
            key (str): The key for the state value.

        Returns:
            The value of the state.
        """
        if key in self._state:
            return self._state[key]
        else:
            raise ValueError(f"Key: {key} does not exist in state.")

    def add_option(self, name: str, type: str, **kwargs) -> None:
        """
        Add an interactive Option interface to the Block.

        Args:
            name (str): The name of the Option interface.
            type (str): The type of the Option interface. Must be one of: 'checkbox', 'input', 'integer', 'number', 'select', 'slider', 'display'.
            **kwargs: Additional properties depending on the type of Option interface.

        Raises:
            ValueError: If an option with the given name already exists in the Block.
            AssertionError: If the name or type arguments are not strings, or if the type is not a valid option type.

        Examples:
            >>> block.add_option(name='My Option', type='checkbox', value=True)
        """

        assert isinstance(name, str), "Error: 'name' argument should be of type string."
        assert isinstance(type, str), "Error: 'type' argument should be of type string."
        assert type in [
            "checkbox",
            "input",
            "integer",
            "number",
            "select",
            "slider",
            "display",
        ], 'Error: Option "type" is not a standard Option interface parameter.'

        if name in self._options:
            raise ValueError(f"Option with name: {name} already exists in Block.")

        option = BlockOption.build(name, type, kwargs)
        self._options[name] = option

    def set_option(self, name: str, **kwargs) -> None:
        """
        Set the value of an existing Option interface in the Block.

        Args:
            name (str): The name of the Option interface.
            **kwargs: Additional properties to set for the Option. Currently, only 'value' can be set.

        Raises:
            ValueError: If the option name doesn't exist, if trying to set an invalid property,
                        or if the property is not valid for the given option.

        Examples:
            >>> block.set_option('My Option', value=False)
        """
        if name in self._options:
            for arg, value in kwargs.items():
                if arg in self._options[name].__dict__:
                    if arg == "value":
                        setattr(self._options[name], arg, value)
                    else:
                        raise ValueError(
                            f"Cannot set or invalid property: {arg} for Block option."
                        )
                else:
                    raise ValueError(
                        f"Property: {arg} is not a valid option property for {name}."
                    )
        else:
            raise ValueError(f"Option name: {name} does not exist in Block.")

    def get_option(self, name: str) -> BlockOptionValue:
        """
        Get the value of an existing Option interface in the Block.

        Args:
            name (str): The name of the Option interface.

        Returns:
            Value: The value of the Option interface.

        Raises:
            ValueError: If the option name doesn't exist in the Block.

        Examples:
            >>> value = block.get_option('My Option')
        """
        if name in self._options:
            return self._options[name].value
        else:
            raise ValueError(f"Option name: {name} does not exist in Block.")

    def _export(self) -> dict:
        """
        Export the block's data as a dictionary.

        Returns:
            dict: A dictionary containing the block's name, inputs, outputs, and options.
                  The inputs, outputs, and options are exported as lists of their respective values.

        This method is used internally to serialize the block's data for saving or transmitting.
        """
        return {
            "name": self.name,
            "type": self._type,
            "inputs": [input.export() for input in self._inputs.values()],
            "outputs": [output.export() for output in self._outputs.values()],
            "options": [asdict(option) for option in self._options.values()],
        }

    def _on_compute(self) -> Any:
        """默认实现为普通函数，确保基类本身不产生协程对象"""
        pass

    # async def _on_compute(self) -> None:
    #     """
    #     Default compute method for the block.
    #     This method is meant to be overridden by the user-defined compute function.
    #     Can be either synchronous or asynchronous.
    #     """
    #     pass

    def add_compute(self, _func: Callable[["Block"], Any]) -> None:
        """
        Add a compute function to the block.

        Notes:
            - Synchronous functions are automatically wrapped to be async-compatible
            - The function is bound to the block instance, allowing it to access
              and modify the block's attributes through 'self'

        Args:
            _func (Callable[['Block'], Any]): The compute function to be added.
                It should take a single argument of type 'Block' (self).
                Can be either a synchronous function or an async coroutine.

        Examples:
            >>> # Synchronous function
            >>> def compute(self):
            ...     result = self.get_interface("Input 1")
            ...     self.set_interface("Output 1", result)
            >>> block.add_compute(compute)

            >>> # Asynchronous function
            >>> async def compute(self):
            ...     result = await some_async_operation()
            ...     self.set_interface("Output 1", result)
            >>> block.add_compute(compute)
        """

        # 直接绑定函数到实例上，不进行强制异步包装
        self._on_compute = MethodType(_func, self)


        # if inspect.iscoroutinefunction(_func):
        #     self._on_compute = MethodType(_func, self)
        # else:
        #     # Wrap synchronous functions to make them async-compatible
        #     async def wrapper(self):
        #         return _func(self)

        #     self._on_compute = MethodType(wrapper, self)


```

### python 定义 Blocks 
``` py
channel = Block(name="Channel")
channel.add_output("O-List-XY")
channel.add_option(name="启用", type="checkbox", value=True)
channel.add_option(
    name="通道",
    type="select",
    items=[
        "Channel 0",
        "Channel 1",
        "Channel 2",
        "Channel 3",
        "Channel 4",
        "Channel 5",
        "Channel 6",
        "Channel 7",
    ],
)

ChannelMap = {
    "Channel 0": 0,
    "Channel 1": 1,
    "Channel 2": 2,
    "Channel 3": 3,
    "Channel 4": 4,
    "Channel 5": 5,
    "Channel 6": 6,
    "Channel 7": 7,
}


def channel_func(self):
    sensor = self.get_interface(name="I-Sensor")
    on = self.get_option("启用")
    if not on:
        return

    channel = ChannelMap[self.get_option("通道")]

    data = adlink_bridge_instance.get_channel_data(channel)

    self.set_interface(
        name="O-List-XY",
        value={"type": "channel", "data": data},
    )


channel.add_compute(channel_func)


##########################################################################################
# X, Y
list1d = Block(name="ToList1D")
list1d.add_input("I-List-XY")
list1d.add_output("O-List-V")
list1d.add_option(name="输出", type="select", items=["X", "Y"], value="Y")


def list1d_func(self):
    i_data_xy = self.get_interface(name="I-List-XY")
    vout = self.get_option("输出")
    if vout == "X":
        self.set_interface(
            name="O-List-V",
            value={"type": "list1d", "data": i_data_xy["data"]["x"]},
        )
    else:
        self.set_interface(
            name="O-List-V",
            value={"type": "list1d", "data": i_data_xy["data"]["y"]},
        )


list1d.add_compute(list1d_func)

list2d = Block(name="ToList2D")
list2d.add_input("I-List-X")
list2d.add_input("I-List-Y")
list2d.add_output("O-List-XY")


def list2d_func(self):
    i_data_x = self.get_interface(name="I-List-X")
    i_data_y = self.get_interface(name="I-List-Y")
    self.set_interface(
        name="O-List-XY",
        value={
            "type": "list2d",
            "data": {"x": i_data_x["data"], "y": i_data_y["data"]},
        },
    )


list2d.add_compute(list2d_func)

##########################################################################################
# FourierTransform
fourier = Block(name="FourierTransform")
fourier.add_input("I-List-V")
fourier.add_output("O-List-XY")
fourier.add_option(name="绝对值", type="checkbox", value=True)


def fourier_func(self):
    i_data = self.get_interface(name="I-List-V")
    data = i_data["data"]
    abs = self.get_option("绝对值")
    fdata = fourier_transform(data)

    self.set_interface(name="O-List-XY", value={"type": "fourier", "data": fdata})


fourier.add_compute(fourier_func)


##########################################################################################
# Result
result = Block(name="Result")
result.add_input("List-XY")
result.add_option(name="类型", type="select", items=["时域", "频域", "FREE"])
result.add_option(name="名称", type="input", value="")


def result_func(self):
    i_data = self.get_interface(name="List-XY")
    t = self.get_option("类型")
    name = self.get_option("名称")
    data = {"name": name, "value": i_data["data"]}
    if t == "时域":
        adlink_bridge_instance.add_data_t(data)
    elif t == "频域":
        adlink_bridge_instance.add_data_p(data)
    else:
        adlink_bridge_instance.add_data_xy(data)


result.add_compute(result_func)
```


### 使用 blocks 节点连接后的流式计算 Schema 示例

``` json

{
  "id": "908dd800-7082-4872-b821-86da3d09a4b5",
  "nodes": [
    {
      "type": "Channel",
      "id": "8b853ef4-79c7-4192-a9da-8ed1da40c6fe",
      "title": "Channel",
      "inputs": {
        "启用": {
          "id": "ba0cdbc6-2df4-46e4-b016-fd1223504c56",
          "value": true
        },
        "通道": {
          "id": "3833d62b-0813-4ff7-b4c0-528ec95ab3f9",
          "value": "Channel 0"
        }
      },
      "outputs": {
        "O-List-XY": {
          "id": "23e745c3-a734-4898-aa8c-27c1a67b99a4",
          "value": ""
        }
      },
      "position": {
        "x": 15,
        "y": 157
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "Result",
      "id": "ff93794e-4bb3-41ef-bdb3-517034747c2b",
      "title": "Result",
      "inputs": {
        "List-XY": {
          "id": "010c3b9a-889c-4fff-8914-98929c2c6bfa",
          "value": ""
        },
        "类型": {
          "id": "4e59357b-7422-4baa-8d26-c5531474bc6c",
          "value": "时域"
        },
        "名称": {
          "id": "504d74a7-057f-4999-aaa7-f3f053592c58",
          "value": "旋转"
        }
      },
      "outputs": {},
      "position": {
        "x": 891,
        "y": 298
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "ToList1D",
      "id": "c9ad94bc-506d-4d6b-8564-fc7b306b0e56",
      "title": "ToList1D",
      "inputs": {
        "I-List-XY": {
          "id": "4fde7804-f728-4d17-b45e-55d890acb424",
          "value": ""
        },
        "输出": {
          "id": "f51ef079-c0a1-4e2b-963c-45ce6213e57a",
          "value": "Y"
        }
      },
      "outputs": {
        "O-List-V": {
          "id": "d793cabb-a6d7-47e7-83bb-a40d4b43da51",
          "value": ""
        }
      },
      "position": {
        "x": 313,
        "y": 157
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "ToList2D",
      "id": "f9c6fcee-1e50-41bb-82aa-21f65bba61db",
      "title": "ToList2D",
      "inputs": {
        "I-List-X": {
          "id": "ac6bdc15-e185-400c-a696-fe845661863e",
          "value": ""
        },
        "I-List-Y": {
          "id": "0a5fadc5-9431-4189-8301-935e78dcfd1d",
          "value": ""
        }
      },
      "outputs": {
        "O-List-XY": {
          "id": "1f55123a-de93-4998-aafe-a1cdd722dc31",
          "value": ""
        }
      },
      "position": {
        "x": 610,
        "y": 252
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "Channel",
      "id": "37e38f4e-9c9b-45d9-aa4d-684289960270",
      "title": "Channel",
      "inputs": {
        "启用": {
          "id": "0848045a-06c0-4612-bec7-534eb58071ef",
          "value": true
        },
        "通道": {
          "id": "0557f3e5-1f8d-4072-a12f-8e77247c088f",
          "value": "Channel 1"
        }
      },
      "outputs": {
        "O-List-XY": {
          "id": "3fb5ad2a-7c42-48d7-96ca-c6e1656e7b9a",
          "value": ""
        }
      },
      "position": {
        "x": 12,
        "y": 415
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "ToList1D",
      "id": "c45c2164-8442-40ef-a3ef-2967dfb2c4d5",
      "title": "ToList1D",
      "inputs": {
        "I-List-XY": {
          "id": "a1ee45b3-fae2-4f5b-9aad-7a436046e4f1",
          "value": ""
        },
        "输出": {
          "id": "adb9d774-7328-45c0-b4a0-7531d96cfbb6",
          "value": "Y"
        }
      },
      "outputs": {
        "O-List-V": {
          "id": "97824c1e-86b4-4d75-a8b7-7d32e0658926",
          "value": ""
        }
      },
      "position": {
        "x": 314,
        "y": 414
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "Channel",
      "id": "fd40d2a6-7f03-4255-a05f-7aaeafb1f53e",
      "title": "Channel",
      "inputs": {
        "启用": {
          "id": "be97b3ba-2fb6-4bd8-b719-872251ecec99",
          "value": true
        },
        "通道": {
          "id": "231bc8cc-a63e-4913-b3d2-3b4f2158adef",
          "value": null
        }
      },
      "outputs": {
        "O-List-XY": {
          "id": "4f68b523-2871-400e-9e7c-a096a2eeb1b4",
          "value": ""
        }
      },
      "position": {
        "x": 8,
        "y": 660
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "FourierTransform",
      "id": "236445e2-d2f3-4918-a105-252f574f02a0",
      "title": "FourierTransform",
      "inputs": {
        "I-List-V": {
          "id": "7c7a7481-5a3a-4660-82b1-f5f5a6164560",
          "value": ""
        },
        "绝对值": {
          "id": "82025998-d776-4631-99fd-749fa07ca0dd",
          "value": true
        }
      },
      "outputs": {
        "O-List-XY": {
          "id": "2df29491-f67b-4105-b5ca-39112f8d79b0",
          "value": ""
        }
      },
      "position": {
        "x": 319,
        "y": 674
      },
      "width": 200,
      "twoColumn": false
    },
    {
      "type": "Result",
      "id": "8080e3d3-9718-486d-8082-8d2979237726",
      "title": "Result",
      "inputs": {
        "List-XY": {
          "id": "c11ed8d1-d96f-46da-8f33-b620b5c11b6e",
          "value": ""
        },
        "类型": {
          "id": "f1c7a261-ab55-49e7-918e-c70e33d33ee9",
          "value": "频域"
        },
        "名称": {
          "id": "0bcab21e-a344-4da8-8a9f-82b7a937e2c4",
          "value": "频谱"
        }
      },
      "outputs": {},
      "position": {
        "x": 653,
        "y": 575
      },
      "width": 200,
      "twoColumn": false
    }
  ],
  "connections": [
    {
      "id": "b1828dd6-0c03-4e83-b3d5-d0b662bc4d2e",
      "from": "23e745c3-a734-4898-aa8c-27c1a67b99a4",
      "to": "4fde7804-f728-4d17-b45e-55d890acb424"
    },
    {
      "id": "991a2ed4-a6e9-47d7-b51b-6d9faeaf91a9",
      "from": "3fb5ad2a-7c42-48d7-96ca-c6e1656e7b9a",
      "to": "a1ee45b3-fae2-4f5b-9aad-7a436046e4f1"
    },
    {
      "id": "3107580a-6947-4b24-a485-1e5cb744b96b",
      "from": "d793cabb-a6d7-47e7-83bb-a40d4b43da51",
      "to": "ac6bdc15-e185-400c-a696-fe845661863e"
    },
    {
      "id": "c7afeed7-e8e9-4631-b41c-98a61fc56dca",
      "from": "97824c1e-86b4-4d75-a8b7-7d32e0658926",
      "to": "0a5fadc5-9431-4189-8301-935e78dcfd1d"
    },
    {
      "id": "c2eca0b4-62c9-4166-ac8a-0196b4933495",
      "from": "1f55123a-de93-4998-aafe-a1cdd722dc31",
      "to": "010c3b9a-889c-4fff-8914-98929c2c6bfa"
    },
    {
      "id": "016a71c9-eb46-4d50-b7a4-67cb75a24149",
      "from": "4f68b523-2871-400e-9e7c-a096a2eeb1b4",
      "to": "7c7a7481-5a3a-4660-82b1-f5f5a6164560"
    },
    {
      "id": "ae959e8d-5993-4e8e-b501-81c0bdb4f20a",
      "from": "2df29491-f67b-4105-b5ca-39112f8d79b0",
      "to": "c11ed8d1-d96f-46da-8f33-b620b5c11b6e"
    }
  ],
  "inputs": [],
  "outputs": [],
  "panning": {
    "x": 92,
    "y": -23
  },
  "scaling": 1
}

```

### 实现 ComputeEngine
1. 根据 python定义的 的 Block class list 和 Schema json，根据connections传递节点的值，执行各节点的compute函数
2. 执行同步执行和异步执行
3. 异步执行时，没有路径依赖关系的，可以并行运算
4. 可以重新设置blocks
5. blocks初始化后，可以反复设置schema
6. 可以多次run，async_run
7. 运行过程中打印有好的提示信息，并可以反馈到外部，


### option 类型
Button
Checkbox
Integer
Number
Select
Slider
Text
TextInput
TextareaInput
其中
Button不需要value
其他的可以有默认值
Integer、Number、Slider支持min, max
Select支持Option



根据想要观测的转速波动频率来决定 PPR。

$$PPR_{min} > \frac{2 \times \text{最高波动频率 (Hz)}}{\text{基础转速 (Hz)}}$$




























### 通过python Blocks 得到的 Json

``` json
{
    "blocks": [
        {
            "name": "Channel",
            "inputs": [],
            "outputs": [
                {
                    "name": "O-List-XY"
                }
            ],
            "options": [
                {
                    "name": "启用",
                    "type": "CheckboxOption",
                    "value": true
                },
                {
                    "name": "通道",
                    "type": "SelectOption",
                    "value": null,
                    "items": [
                        "Channel 0",
                        "Channel 1",
                        "Channel 2",
                        "Channel 3",
                        "Channel 4",
                        "Channel 5",
                        "Channel 6",
                        "Channel 7"
                    ],
                    "properties": {
                        "items": [
                            "Channel 0",
                            "Channel 1",
                            "Channel 2",
                            "Channel 3",
                            "Channel 4",
                            "Channel 5",
                            "Channel 6",
                            "Channel 7"
                        ]
                    }
                }
            ]
        },
        {
            "name": "ToList1D",
            "inputs": [
                {
                    "name": "I-List-XY"
                }
            ],
            "outputs": [
                {
                    "name": "O-List-V"
                }
            ],
            "options": [
                {
                    "name": "输出",
                    "type": "SelectOption",
                    "value": "Y",
                    "items": [
                        "X",
                        "Y"
                    ],
                    "properties": {
                        "items": [
                            "X",
                            "Y"
                        ]
                    }
                }
            ]
        },
        {
            "name": "ToList2D",
            "inputs": [
                {
                    "name": "I-List-X"
                },
                {
                    "name": "I-List-Y"
                }
            ],
            "outputs": [
                {
                    "name": "O-List-XY"
                }
            ],
            "options": []
        },
        {
            "name": "FourierTransform",
            "inputs": [
                {
                    "name": "I-List-V"
                }
            ],
            "outputs": [
                {
                    "name": "O-List-XY"
                }
            ],
            "options": [
                {
                    "name": "绝对值",
                    "type": "CheckboxOption",
                    "value": true
                }
            ]
        },
        {
            "name": "Result",
            "inputs": [
                {
                    "name": "List-XY"
                }
            ],
            "outputs": [],
            "options": [
                {
                    "name": "类型",
                    "type": "SelectOption",
                    "value": null,
                    "items": [
                        "时域",
                        "频域",
                        "FREE"
                    ],
                    "properties": {
                        "items": [
                            "时域",
                            "频域",
                            "FREE"
                        ]
                    }
                },
                {
                    "name": "名称",
                    "type": "InputOption",
                    "value": ""
                }
            ]
        }
    ]
}
```