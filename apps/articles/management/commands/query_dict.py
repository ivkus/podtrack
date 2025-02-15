#!/usr/bin/env python3

import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from ...dict_reader import DictReader, format_definition

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'StarDict词典查询工具'

    def add_arguments(self, parser):
        parser.add_argument('word', help='要查询的单词')
        parser.add_argument(
            '-m', '--match',
            action='store_true',
            help='使用前缀匹配模式'
        )
        parser.add_argument(
            '-l', '--limit',
            type=int,
            default=10,
            help='匹配模式下的结果数量限制(默认: 10)'
        )
        parser.add_argument(
            '-s', '--strip',
            action='store_true',
            help='使用stripword模式匹配'
        )

    def handle(self, *args, **options):
        try:
            reader = DictReader()
            
            if options['match']:
                # 匹配模式
                matches = reader.match(
                    options['word'],
                    options['limit'],
                    options['strip']
                )
                if matches:
                    self.stdout.write(f"\n找到 {len(matches)} 个匹配:")
                    for idx, (id_, word) in enumerate(matches, 1):
                        info = reader.query(id_)
                        if info:
                            self.stdout.write(f"\n{idx}. {word}")
                            self.stdout.write(format_definition(info))
                else:
                    self.stdout.write(
                        self.style.WARNING("未找到匹配的单词")
                    )
            else:
                # 精确查询模式
                info = reader.query(options['word'])
                if info:
                    self.stdout.write(f"\n单词: {info['word']}")
                    self.stdout.write(format_definition(info))
                else:
                    self.stdout.write(
                        self.style.WARNING(f"未找到单词 '{options['word']}'")
                    )
                    
                # 显示一些相关单词
                matches = reader.match(options['word'], 5)
                if matches and matches[0][1].lower() != options['word'].lower():
                    self.stdout.write("\n您要找的是不是:")
                    for _, word in matches[:5]:
                        self.stdout.write(f"  {word}")
                    
        except Exception as e:
            logger.error(f"查询词典时出错: {str(e)}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"查询词典时出错: {str(e)}")
            )
            raise 