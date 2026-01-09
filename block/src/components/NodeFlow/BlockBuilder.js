import { NodeInterface, defineNode } from "@baklavajs/core";
import {
  CheckboxInterface,
  IntegerInterface,
  NumberInterface,
  SelectInterface,
  SliderInterface,
  TextInterface,
  TextInputInterface,
  TextareaInputInterface
} from "@baklavajs/renderer-vue";




// export * from './button/ButtonInterface';
// export * from './checkbox/CheckboxInterface';
// export * from './integer/IntegerInterface';
// export * from './number/NumberInterface';
// export * from './select/SelectInterface';
// export * from './slider/SliderInterface';
// export * from './text/TextInterface';
// export * from './textinput/TextInputInterface';
// export * from './textareainput/TextareaInputInterface';


// 接口类型映射
const INTERFACE_MAP = {
  default: NodeInterface,
  CheckboxOption: CheckboxInterface,
  InputOption: TextInputInterface,
  IntegerOption: IntegerInterface,
  NumberOption: NumberInterface,
  SelectOption: SelectInterface,
  SliderOption: SliderInterface,
  TextOption: TextInterface,
};

export function BuildBlock(nodeDef) {
  const { name, inputs = [], outputs = [], options = [] } = nodeDef;

  // 转换输入定义
  const processedInputs = {};

  // 处理常规inputs
  inputs.forEach((inputDef) => {
    const { name } = inputDef;
    processedInputs[name] = () => new NodeInterface(name, "");
  });

  // 处理options作为inputs（hasPort=false）
  options.forEach((optionDef) => {
    const {
      name,
      type: optionType,
      value: defaultValue,
      items: optionItems = [],
      min,
      max,
      title = name,
    } = optionDef;

    processedInputs[name] = createInterface(
      optionType,
      title,
      defaultValue,
      optionItems,
      min,
      max,
      false // options总是hasPort=false
    );
  });

  // 转换输出定义
  const processedOutputs = {};
  outputs.forEach((outputDef) => {
    const { name } = outputDef;
    processedOutputs[name] = () => new NodeInterface(name, "");
  });

  // 创建节点
  return defineNode({
    type: name,
    inputs: processedInputs,
    outputs: processedOutputs,
    calculate: () => ({}), // 默认空计算函数
  });
}

// 辅助函数：创建接口实例
function createInterface(
  type,
  title,
  defaultValue,
  options,
  min,
  max,
  hasPort
) {
  return () => {
    let interfaceInstance;
    const interfaceType = INTERFACE_MAP[type];

    if (!interfaceType) {
      throw new Error(`Unknown interface type: ${type}`);
    }

    // 根据不同类型创建接口实例
    switch (type) {
      case "SelectOption":
        interfaceInstance = new interfaceType(title, defaultValue, options);
        break;
      case "NumberOption":
        interfaceInstance = new interfaceType(title, defaultValue?defaultValue:min, min, max);
        break;
      case "SliderOption":
        interfaceInstance = new interfaceType(title, defaultValue?defaultValue:min, min, max);
        break;
      default: // CheckboxOption, checkbox, text等
        interfaceInstance = new interfaceType(title, defaultValue);
    }

    // 设置是否有端口
    if (!hasPort) {
      interfaceInstance.setPort(false);
    }

    return interfaceInstance;
  };
}
