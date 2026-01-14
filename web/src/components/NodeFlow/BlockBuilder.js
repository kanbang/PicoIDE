/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09 11:12:55
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-14 09:38:18
 */
import { NodeInterface, defineNode } from "@baklavajs/core";
import * as Interfaces from "@baklavajs/renderer-vue";

/**
 * 接口构造函数映射表
 * 这里的 key 必须与你 Python 后端 Option 的 opt_type 一致
 */
const INTERFACE_MAP = {
    Checkbox:      (t, v) => new Interfaces.CheckboxInterface(t, v ?? false),
    Integer:       (t, v, o) => new Interfaces.IntegerInterface(t, v ?? 0, o.min, o.max),
    Number:        (t, v, o) => new Interfaces.NumberInterface(t, v ?? 0, o.min, o.max),
    Slider:        (t, v, o) => new Interfaces.SliderInterface(t, v ?? o.min ?? 0, o.min ?? 0, o.max ?? 100),
    Select:        (t, v, o) => new Interfaces.SelectInterface(t, v, o.items ?? []),
    TextInput:     (t, v) => new Interfaces.TextInputInterface(t, v ?? ""),
    TextareaInput: (t, v) => new Interfaces.TextareaInputInterface(t, v ?? ""),
    Text:          (t, v) => new Interfaces.TextInterface(t, v ?? ""),
    Button:        (t) => new Interfaces.ButtonInterface(t, () => {}),
};

export function BuildBlock(nodeDef) {
    const { name, inputs = [], outputs = [], options = [] } = nodeDef;

    return defineNode({
        type: name,
        inputs: {
            // 1. 处理常规数据输入端口
            ...Object.fromEntries(inputs.map(i => [
                i.name, 
                () => new NodeInterface(i.name, "")
            ])),
            
            // 2. 处理配置项 (Options)
            ...Object.fromEntries(options.map(opt => [
                opt.name,
                () => {
                    const factory = INTERFACE_MAP[opt.type] || (() => new NodeInterface(opt.name, opt.value));
                    const intf = factory(opt.title || opt.name, opt.value, opt);
                    intf.setPort(false); // Option 默认不显示连线端口
                    return intf;
                }
            ]))
        },
        outputs: Object.fromEntries(outputs.map(o => [
            o.name, 
            () => new NodeInterface(o.name, "")
        ])),
        calculate: () => ({}),
    });
}