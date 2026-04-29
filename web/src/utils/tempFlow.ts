const TEMP_FLOW_PREFIX = '[Temp] ';
const TEMP_FLOW_META_KEY = '__meta';
const TEMP_FLOW_SOURCE = 'nodeflow_demo';

type FlowLike = {
  name?: string;
  flow?: Record<string, any> | null;
};

export function buildTempFlowName(business: string): string {
  return `${TEMP_FLOW_PREFIX}NodeFlowDemo (${business})`;
}

export function buildTempFlowPayload(flow: Record<string, any>): Record<string, any> {
  const meta = flow?.[TEMP_FLOW_META_KEY];
  return {
    ...flow,
    [TEMP_FLOW_META_KEY]: {
      ...(meta && typeof meta === 'object' ? meta : {}),
      is_temp: true,
      source: TEMP_FLOW_SOURCE,
    },
  };
}

export function isTempFlowItem(flowItem: FlowLike): boolean {
  const meta = flowItem.flow?.[TEMP_FLOW_META_KEY];
  return Boolean(meta && typeof meta === 'object' && meta.is_temp === true);
}
