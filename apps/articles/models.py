from django.db import models
from django.utils import timezone


def article_audio_path(instance, filename):
    # 生成上传音频文件的路径
    return f'articles/audio/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

def processed_audio_path(instance, filename):
    # 生成处理后音频文件的路径
    return f'articles/processed_audio/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

class Article(models.Model):
    TRANSCRIPTION_STATUS_CHOICES = [
        ('pending', '等待转写'),
        ('processing', '转写中'),
        ('completed', '转写完成'),
        ('failed', '转写失败'),
    ]
    
    ANALYSIS_STATUS_CHOICES = [
        ('pending', '等待分析'),
        ('processing', '分析中'),
        ('completed', '分析完成'),
        ('failed', '分析失败'),
    ]
    
    AUDIO_PROCESSING_STATUS_CHOICES = [
        ('pending', '等待处理'),
        ('processing', '处理中'),
        ('completed', '处理完成'),
        ('failed', '处理失败'),
    ]

    title = models.CharField(max_length=200)
    text_file = models.FileField(
        upload_to='articles/texts/',
        null=True,
        blank=True
    )
    audio_file = models.FileField(upload_to=article_audio_path)
    processed_audio_file = models.FileField(upload_to=processed_audio_path, blank=True, null=True)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 转写状态（音频->文字）
    transcription_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPTION_STATUS_CHOICES,
        default='pending'
    )
    
    # 分析状态（找出生词）
    analysis_status = models.CharField(
        max_length=20,
        choices=ANALYSIS_STATUS_CHOICES,
        default='pending'
    )
    
    # 音频处理状态（生成带解说的音频）
    audio_processing_status = models.CharField(
        max_length=20,
        choices=AUDIO_PROCESSING_STATUS_CHOICES,
        default='pending'
    )

    def __str__(self):
        return self.title

class Sentence(models.Model):
    article = models.ForeignKey(Article, related_name='sentences', on_delete=models.CASCADE)
    content = models.TextField()
    order = models.IntegerField()  # Sentence order in the article
    start_time = models.FloatField(null=True)  # 句子开始时间（秒）
    end_time = models.FloatField(null=True)    # 句子结束时间（秒）
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.content[:50]}..."

class Word(models.Model):
    lemma = models.CharField(max_length=100)
    sentences = models.ManyToManyField(Sentence, related_name='words')
    articles = models.ManyToManyField(Article, related_name='words')

    def __str__(self):
        return self.lemma