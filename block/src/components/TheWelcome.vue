<!--
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09 10:29:35
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-09 10:38:44
-->
<template>
    <!--
        By default, the editor completely fills its parent HTML element.
        If you directly use the editor in the <body> element, make sure to use
        a wrapper <div> with specified width and height properties:
        <div style="width: 90vw; height: 90vh">
            <BaklavaEditor :view-model="baklava" />
        </div>
    -->
    <BaklavaEditor :view-model="baklava" />
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava } from "@baklavajs/renderer-vue";
import "@baklavajs/themes/dist/syrup-dark.css";

const baklava = useBaklava();
</script>