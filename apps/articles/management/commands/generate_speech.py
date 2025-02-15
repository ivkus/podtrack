#!/usr/bin/env python3

import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from ...tts_service import TTSService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '将文本转换为语音文件'

    def add_arguments(self, parser):
        parser.add_argument(
            'text',
            help='要转换的文本'
        )
        parser.add_argument(
            '--lang',
            help='语言代码 (en: 英语, zh: 中文)',
            choices=['en', 'zh'],
            default='zh'
        )
        parser.add_argument(
            '--output',
            help='输出音频文件路径 (可选，默认在当前目录)',
            default='output.wav'
        )
        parser.add_argument(
            '--cache-dir',
            help='缓存目录路径 (可选)',
            default='audio_cache'
        )

    def handle(self, *args, **options):
        try:
            # 准备路径
            output_path = Path(options['output'])
            cache_dir = Path(options['cache_dir'])
            cache_dir.mkdir(exist_ok=True)
            
            # 生成音频
            audio_path = TTSService.generate_audio(
                text=options['text'],
                lang=options['lang'],
                cache_dir=cache_dir
            )
            
            if audio_path:
                # 如果生成的文件不在指定的输出路径，复制过去
                if Path(audio_path) != output_path:
                    Path(audio_path).rename(output_path)
                
                self.stdout.write(
                    self.style.SUCCESS(f"语音文件已生成: {output_path}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("生成语音文件失败")
                )
                
        except Exception as e:
            logger.error(f"生成语音时出错: {str(e)}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"生成语音时出错: {str(e)}")
            )
            raise 