<template>
  <BaklavaEditor :view-model="baklava" :schema="schema" :blocks="blocks"
    @update:schema="(newSchema) => schema = newSchema" />
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import "@baklavajs/themes/dist/syrup-dark.css";
import { defineModel, defineProps, onMounted, watch, defineComponent, h } from 'vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from "./TestNode";
import SaveIcon from '@/components/icons/Save.vue'

const baklava = useBaklava();
const editor = baklava.editor;

baklava.settings.sidebar.enabled = false;
baklava.settings.sidebar.resizable = true;

baklava.settings.enableMinimap = true;
baklava.settings.toolbar.enabled = true;


// baklava.settings.toolbar.commands = baklava.settings.toolbar.commands.slice(0,-1);


// 1. Register a custom command
const SAVE_COMMAND = "SAVE";
baklava.commandHandler.registerCommand(SAVE_COMMAND, {
  execute: () => {
    // Clear all nodes from the graph
    // baklava.displayedGraph.nodes.forEach((node) => {
    //   baklava.displayedGraph.removeNode(node);
    // });
    const data = editor.save();
    console.log(data);
    // axios.post("/api/execute", data)
    //   .then(response => {
    //     console.log(response.data);
    //   })
    //   .catch(error => {
    //     console.error(error);
    //   });
  },
  // Optional: Define when the command can be executed
  canExecute: () => baklava.displayedGraph.nodes.length > 0,
});

// 2. & 3. Add the command to the toolbar
baklava.settings.toolbar.commands = [
  ...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1),
  {
    command: SAVE_COMMAND,
    title: "保存", // 提示文本
    icon: defineComponent(() => {
      return () => h('div', {
        style: {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100%'
        }
      }, [
        h(SaveIcon)
      ])
    }),
  },
];


// Schema uses defineModel for two-way binding
const schema = defineModel('schema', {
  type: Object,
  default: () => ({ nodes: [], connections: [] })
});

// Blocks is a read-only prop
const props = defineProps<{
  blocks?: any[];
}>();


onMounted(() => {
  baklava.editor.registerNodeType(TestNode, { category: "Tests" });

  console.log(TestNode);
  props.blocks.forEach(el => {
    const Block = BuildBlock({
      name: el.name,
      inputs: el.inputs,
      outputs: el.outputs,
      options: el.options
    });

    console.log(Block);
    // register the nodes we have defined, so they can be
    // added by the user as well as saved & loaded. Add a
    // category to it if it exists.

    if (Object.hasOwn(el, 'category')) {
      baklava.editor.registerNodeType(Block, { category: el.category });
    } else {
      baklava.editor.registerNodeType(Block);
    }

    // editor.registerNodeType(el.name, Block);
  });


  // Load the editor data if load_editor_schema not equal to null.
  // if (schema.value) {
  //   baklava.load(schema.value);
  // }


})
</script>

<style>
.baklava-node-palette {
  display: none !important;
}
</style>