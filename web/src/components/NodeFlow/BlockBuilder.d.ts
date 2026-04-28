/*
 * @Descripttion:
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09 11:12:55
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-14 09:38:18
 */
import { NodeInterface } from "@baklavajs/core";
import type { Node as BaklavaNode } from "@baklavajs/core";

export interface BlockDefinition {
  name: string;
  displayName?: string;
  category?: string;
  inputs?: BlockPortDefinition[];
  outputs?: BlockPortDefinition[];
  options?: BlockOptionDefinition[];
  metadata?: Record<string, any>;
}

export interface BlockPortDefinition {
  name: string;
  type?: string;
  required?: boolean;
  description?: string;
}

export interface BlockOptionDefinition {
  name: string;
  type: 'Checkbox' | 'Integer' | 'Number' | 'Slider' | 'Select' | 'TextInput' | 'TextareaInput' | 'Text' | 'Button';
  title?: string;
  value?: any;
  min?: number;
  max?: number;
  items?: string[];
  description?: string;
}

export interface BaklavaNodeInterface extends NodeInterface {
  setPort(visible: boolean): void;
}

export function BuildBlock(nodeDef: BlockDefinition): BaklavaNode;