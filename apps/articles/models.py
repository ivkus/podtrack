from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Sentence(models.Model):
    article = models.ForeignKey(Article, related_name='sentences', on_delete=models.CASCADE)
    content = models.TextField()
    order = models.IntegerField()  # Sentence order in the article
    
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