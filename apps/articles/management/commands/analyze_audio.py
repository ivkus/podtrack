#!/usr/bin/env python3

import json
import logging
from dataclasses import asdict
from pathlib import Path

from django.core.management.base import BaseCommand

from ...whisper_service import WhisperService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Analyze audio file using Whisper and extract transcript with timestamps'

    def add_arguments(self, parser):
        parser.add_argument('input', help='Input audio file path')
        parser.add_argument(
            '--language',
            help='Language code (e.g., en, zh, es)',
            default=None
        )
        parser.add_argument(
            '--output',
            help='Output JSON file path (optional)'
        )

    def handle(self, *args, **options):
        try:
            input_path = Path(options['input'])
            
            # 分析音频
            result = WhisperService.analyze_audio(
                str(input_path), 
                options['language']
            )
            
            # 格式化输出
            output = {
                "full_text": result["full_text"],
                "segments": [asdict(segment) for segment in result["segments"]],
                "sentences": [asdict(sentence) for sentence in result["sentences"]]
            }
            
            # 写入或打印结果
            if options['output']:
                output_path = Path(options['output'])
                output_path.write_text(
                    json.dumps(output, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                self.stdout.write(
                    self.style.SUCCESS(f"结果已保存到: {output_path}")
                )
            else:
                self.stdout.write(
                    json.dumps(output, ensure_ascii=False, indent=2)
                )
                
        except Exception as e:
            logger.error(f"分析音频时出错: {str(e)}", exc_info=True)
            raise