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

// ============================================================================
// 接口类型映射表
// ============================================================================

const interfaceTypeMap = {
  default: NodeInterface,
  CheckboxOption: CheckboxInterface,
  InputOption: TextInputInterface,
  IntegerOption: IntegerInterface,
  NumberOption: NumberInterface,
  SelectOption: SelectInterface,
  SliderOption: SliderInterface,
  TextOption: TextInterface,
  TextareaOption: TextareaInputInterface,
};

// ============================================================================
// 主函数：构建节点
// ============================================================================

/**
 * 根据节点定义构建 Baklavajs 节点
 * @param {Object} nodeDef - 节点定义对象
 * @param {string} nodeDef.name - 节点名称
 * @param {Array} nodeDef.inputs - 输入端口定义数组
 * @param {Array} nodeDef.outputs - 输出端口定义数组
 * @param {Array} nodeDef.options - 选项定义数组
 * @returns {Object} Baklavajs 节点定义
 */
export function BuildBlock(nodeDef) {
  const { name, inputs = [], outputs = [], options = [] } = nodeDef;

  const processedInputs = processInputs(inputs, options);
  const processedOutputs = processOutputs(outputs);

  return defineNode({
    type: name,
    inputs: processedInputs,
    outputs: processedOutputs,
    calculate: () => ({}),
  });
}

// ============================================================================
// 辅助函数：处理输入和输出
// ============================================================================

/**
 * 处理输入定义，包括常规输入和选项
 */
function processInputs(inputs, options) {
  const processedInputs = {};

  // 处理常规输入端口
  inputs.forEach((inputDef) => {
    const { name } = inputDef;
    processedInputs[name] = () => new NodeInterface(name, "");
  });

  // 处理选项作为输入（无端口）
  options.forEach((optionDef) => {
    const interfaceConfig = {
      type: optionDef.type,
      title: optionDef.title ?? optionDef.name,
      defaultValue: optionDef.value,
      options: optionDef.items ?? [],
      min: optionDef.min,
      max: optionDef.max,
      hasPort: false,
    };

    processedInputs[optionDef.name] = createInterface(interfaceConfig);
  });

  return processedInputs;
}

/**
 * 处理输出定义
 */
function processOutputs(outputs) {
  const processedOutputs = {};

  outputs.forEach((outputDef) => {
    const { name } = outputDef;
    processedOutputs[name] = () => new NodeInterface(name, "");
  });

  return processedOutputs;
}

// ============================================================================
// 辅助函数：创建接口实例
// ============================================================================

/**
 * 创建接口实例的工厂函数
 * @param {Object} config - 接口配置对象
 * @returns {Function} 返回创建接口实例的函数
 */
function createInterface(config) {
  return () => {
    const {
      type,
      title,
      defaultValue,
      options,
      min,
      max,
      hasPort,
    } = config;

    const InterfaceClass = interfaceTypeMap[type];

    if (!InterfaceClass) {
      throw new Error(`Unknown interface type: ${type}`);
    }

    const interfaceInstance = createInterfaceByType(
      type,
      InterfaceClass,
      title,
      defaultValue,
      options,
      min,
      max
    );

    if (!hasPort) {
      interfaceInstance.setPort(false);
    }

    return interfaceInstance;
  };
}

/**
 * 根据类型创建具体的接口实例
 */
function createInterfaceByType(type, InterfaceClass, title, defaultValue, options, min, max) {
  switch (type) {
    case "CheckboxOption":
      return new InterfaceClass(title, defaultValue ?? false);

    case "IntegerOption":
      return createNumberRangeInterface(InterfaceClass, title, defaultValue, min, max);

    case "NumberOption":
      return createNumberRangeInterface(InterfaceClass, title, defaultValue, min, max);

    case "SelectOption":
      return new InterfaceClass(title, defaultValue, options);

    case "SliderOption":
      return new InterfaceClass(
        title,
        defaultValue ?? min ?? 0,
        min ?? 0,
        max ?? 1
      );

    case "TextOption":
      return new InterfaceClass(title, defaultValue ?? "");

    case "InputOption":
      return new InterfaceClass(title, defaultValue ?? "");

    case "TextareaOption":
      return new InterfaceClass(title, defaultValue ?? "");

    default:
      return new NodeInterface(title, defaultValue);
  }
}

/**
 * 创建带范围的数值接口（Integer 或 Number）
 */
function createNumberRangeInterface(InterfaceClass, title, defaultValue, min, max) {
  if (min !== undefined && max !== undefined) {
    return new InterfaceClass(title, defaultValue ?? 0, min, max);
  }
  return new InterfaceClass(title, defaultValue ?? 0);
}
