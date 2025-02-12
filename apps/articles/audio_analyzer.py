#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer
import wave
import json
from typing import List, Dict
import os
import sys
import tempfile
from pydub import AudioSegment

class PodcastAudioAnalyzer:
    def __init__(self, model_path: str = None):
        # 如果没有指定模型路径，使用默认的英语小型模型
        if not model_path:
            model_path = "vosk-model-en-us-0.22"
        
        # 确保模型存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Vosk model not found at {model_path}. Please download it from https://alphacephei.com/vosk/models"
            )
            
        self.model = Model(model_path)
        
    def _convert_audio(self, audio_path: str) -> str:
        """
        将音频转换为 Vosk 所需的格式（WAV、单声道、16bit、16kHz）
        
        Args:
            audio_path: 输入音频文件路径
            
        Returns:
            转换后的临时文件路径
        """
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # 加载音频文件
            audio = AudioSegment.from_file(audio_path)
            
            # 转换为所需格式
            audio = audio.set_channels(1)  # 单声道
            audio = audio.set_sample_width(2)  # 16-bit
            audio = audio.set_frame_rate(16000)  # 16kHz
            
            # 导出为 WAV
            audio.export(temp_path, format="wav")
            
            return temp_path
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)  # 删除临时文件
            raise ValueError(f"Error converting audio file: {str(e)}")
        
    def analyze_audio(self, audio_path: str) -> List[Dict]:
        """
        分析音频文件并返回识别结果
        
        Args:
            audio_path: 音频文件路径（支持多种格式）
            
        Returns:
            List of recognition segments, each containing:
            - result: List of word details (start, end, conf, word)
            - text: Complete text for this segment
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # 转换音频格式
        temp_path = None
        try:
            temp_path = self._convert_audio(audio_path)
            
            # 打开转换后的音频文件
            wf = wave.open(temp_path, "rb")
            
            # 创建识别器
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)  # 启用单词级时间戳
            
            # 存储所有识别结果
            segments = []
            
            # 按块读取音频
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                    
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'result' in result:
                        segments.append(result)
                        
            # 处理最后的结果
            final_result = json.loads(rec.FinalResult())
            if 'result' in final_result:
                segments.append(final_result)
                
            return segments
            
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze podcast audio')
    parser.add_argument('input', help='Input audio file path (supports various formats)')
    parser.add_argument(
        '--model', 
        help='Path to Vosk model (optional)',
        default=None
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = PodcastAudioAnalyzer(args.model)
        results = analyzer.analyze_audio(args.input)
        
        output = {
            'segments': results
        }
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"Results saved to: {args.output}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 