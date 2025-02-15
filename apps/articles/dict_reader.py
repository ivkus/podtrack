#!/usr/bin/env python3
# apps/articles/dict_parser.py

import os
import sqlite3
import json
import argparse
import sys
from typing import Dict, Optional, List, Tuple, Sequence, Any, Union
import logging
import settings

logger = logging.getLogger(__name__)

class DictReader:
    """读取StarDict格式词典的类"""
    
    _instance = None

    def __new__(cls, filename: str = settings.DICTIONARY_PATH, verbose: bool = False):
        """确保DictReader是单例"""
        if cls._instance is None:
            cls._instance = super(DictReader, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, filename: str = settings.DICTIONARY_PATH, verbose: bool = False):
        """初始化词典读取器
        
        Args:
            filename: StarDict SQLite数据库文件路径
            verbose: 是否输出详细日志
        """
        if self.__initialized:
            return  # 防止重复初始化

        self.__dbname = filename
        if filename != ':memory:':
            self.__dbname = os.path.abspath(filename)
        self.__conn = None
        self.__verbose = verbose
        self.__fields = (
            ('id', 0),
            ('word', 1), 
            ('sw', 2),
            ('phonetic', 3),
            ('definition', 4),
            ('translation', 5),
            ('pos', 6),
            ('collins', 7),
            ('oxford', 8),
            ('tag', 9),
            ('bnc', 10),
            ('frq', 11),
            ('exchange', 12),
            ('detail', 13),
            ('audio', 14)
        )
        self.__names = {k:v for k,v in self.__fields}
        self.__enable = self.__fields[3:]
        self.__open()
        self.__initialized = True

    def __open(self) -> bool:
        """打开数据库连接"""
        try:
            self.__conn = sqlite3.connect(self.__dbname, isolation_level="IMMEDIATE")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to open database: {e}")
            return False

    def __record2obj(self, record) -> Optional[Dict]:
        """将数据库记录转换为字典对象
        
        Args:
            record: 数据库记录元组
            
        Returns:
            包含单词信息的字典,如果记录为空则返回None
        """
        if record is None:
            return None
            
        word = {}
        for k, v in self.__fields:
            word[k] = record[v]
            
        if word['detail']:
            try:
                word['detail'] = json.loads(word['detail'])
            except json.JSONDecodeError:
                word['detail'] = None
                
        return word

    def close(self):
        """关闭数据库连接"""
        if self.__conn:
            self.__conn.close()
        self.__conn = None
    
    def __del__(self):
        self.close()

    def query(self, key: Union[str, int]) -> Optional[Dict]:
        """查询单词
        
        Args:
            key: 要查询的单词或ID
            
        Returns:
            包含单词信息的字典,如果未找到则返回None
        """
        if self.__conn is None:
            return None
            
        c = self.__conn.cursor()
        record = None
        
        try:
            if isinstance(key, int):
                c.execute('SELECT * FROM stardict WHERE id = ?;', (key,))
            elif isinstance(key, str):
                c.execute('SELECT * FROM stardict WHERE word = ?', (key,))
            else:
                return None
                
            record = c.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database error when querying {key}: {e}")
            return None
            
        return self.__record2obj(record)

    def query_batch(self, keys: Sequence[Union[str, int]]) -> List[Optional[Dict]]:
        """批量查询单词
        
        Args:
            keys: 要查询的单词或ID列表
            
        Returns:
            查询结果的列表,与输入顺序对应,未找到的位置为None
        """
        if not keys:
            return []
            
        # 准备SQL语句
        queries = []
        params = []
        for key in keys:
            if isinstance(key, int):
                queries.append('id = ?')
            elif isinstance(key, str):
                queries.append('word = ?')
            params.append(key)
            
        sql = 'SELECT * FROM stardict WHERE ' + ' OR '.join(queries) + ';'
        
        try:
            c = self.__conn.cursor()
            c.execute(sql, tuple(params))
            
            # 构建结果映射
            results = {}
            for row in c.fetchall():
                obj = self.__record2obj(row)
                if obj:
                    results[obj['id']] = obj
                    results[obj['word'].lower()] = obj
                    
            # 按输入顺序返回结果
            output = []
            for key in keys:
                if isinstance(key, int):
                    output.append(results.get(key))
                else:
                    output.append(results.get(key.lower()))
                    
            return output
            
        except sqlite3.Error as e:
            logger.error(f"Database error in batch query: {e}")
            return [None] * len(keys)

    def match(self, word: str, limit: int = 10, strip: bool = False) -> List[Tuple[int, str]]:
        """查询匹配的单词
        
        Args:
            word: 要匹配的单词前缀
            limit: 返回结果数量限制
            strip: 是否使用stripped word匹配
            
        Returns:
            匹配单词的列表,每个元素为(id, word)元组
        """
        if self.__conn is None:
            return []
            
        c = self.__conn.cursor()
        
        try:
            if not strip:
                sql = 'SELECT id, word FROM stardict WHERE word >= ? '
                sql += 'ORDER BY word COLLATE NOCASE LIMIT ?;'
                c.execute(sql, (word, limit))
            else:
                sql = 'SELECT id, word FROM stardict WHERE sw >= ? '
                sql += 'ORDER BY sw, word COLLATE NOCASE LIMIT ?;'
                c.execute(sql, (self.stripword(word), limit))
                
            return [(record[0], record[1]) for record in c.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Database error in match: {e}")
            return []

    def count(self) -> int:
        """返回词典中的单词总数"""
        if self.__conn is None:
            return 0
            
        try:
            c = self.__conn.cursor()
            c.execute('SELECT count(*) FROM stardict;')
            record = c.fetchone()
            return record[0] if record else 0
        except sqlite3.Error as e:
            logger.error(f"Database error in count: {e}")
            return 0

    @staticmethod
    def stripword(word: str) -> str:
        """提取单词中的字母数字部分并转为小写
        
        Args:
            word: 输入单词
            
        Returns:
            处理后的单词
        """
        return ''.join(c for c in word if c.isalnum()).lower()

    def __len__(self):
        """返回词典大小"""
        return self.count()

    def __contains__(self, key):
        """检查单词是否在词典中"""
        return self.query(key) is not None

    def __getitem__(self, key):
        """获取单词信息"""
        return self.query(key)

def format_definition(word_info: Dict[str, Any]) -> str:
    """格式化单词释义信息
    
    Args:
        word_info: 单词信息字典
        
    Returns:
        格式化的字符串
    """
    parts = []
    
    if word_info.get('phonetic'):
        parts.append(f"音标: [{word_info['phonetic']}]")
        
    if word_info.get('definition'):
        parts.append(f"释义: {word_info['definition']}")
        
    if word_info.get('translation'):
        parts.append(f"翻译: {word_info['translation']}")
        
    if word_info.get('pos'):
        parts.append(f"词性: {word_info['pos']}")
        
    return '\n'.join(parts)

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='StarDict词典查询工具')
    parser.add_argument('db_file', help='StarDict SQLite数据库文件路径')
    parser.add_argument('word', help='要查询的单词')
    parser.add_argument('-m', '--match', action='store_true', 
                      help='使用前缀匹配模式')
    parser.add_argument('-l', '--limit', type=int, default=10,
                      help='匹配模式下的结果数量限制(默认: 10)')
    parser.add_argument('-s', '--strip', action='store_true',
                      help='使用stripword模式匹配')
    
    args = parser.parse_args()
    
    # 检查数据库文件是否存在
    if not os.path.exists(args.db_file):
        print(f"错误: 数据库文件 '{args.db_file}' 不存在", file=sys.stderr)
        return 1
        
    try:
        reader = DictReader(args.db_file)
        
        if args.match:
            # 匹配模式
            matches = reader.match(args.word, args.limit, args.strip)
            if matches:
                print(f"\n找到 {len(matches)} 个匹配:")
                for idx, (id_, word) in enumerate(matches, 1):
                    info = reader.query(id_)
                    if info:
                        print(f"\n{idx}. {word}")
                        print(format_definition(info))
            else:
                print("未找到匹配的单词")
        else:
            # 精确查询模式
            info = reader.query(args.word)
            if info:
                print(f"\n单词: {info['word']}")
                print(format_definition(info))
            else:
                print(f"未找到单词 '{args.word}'")
                
            # 显示一些相关单词
            matches = reader.match(args.word, 5)
            if matches and matches[0][1].lower() != args.word.lower():
                print("\n您要找的是不是:")
                for _, word in matches[:5]:
                    print(f"  {word}")
                    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())

def get_dict_reader(verbose: bool = False) -> DictReader:
    """提供DictReader实例的接口
    
    Args:
        verbose: 是否输出详细日志
        
    Returns:
        DictReader实例
    """
    return DictReader(verbose=verbose)
