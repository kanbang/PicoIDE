'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-20 16:22:38
LastEditors: zhai
LastEditTime: 2026-01-20 16:23:08
'''

# 配置日志
import logging
from flow.setting import settings


logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)