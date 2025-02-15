from django.db import models


class VocabularyItem(models.Model):
    word = models.ForeignKey('articles.Word', on_delete=models.CASCADE)
    mastered = models.BooleanField(default=False)
    ignored = models.BooleanField(default=False)  # For words to be excluded
    last_reviewed = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['word'], 
                name='unique_vocabulary_item'
            )
        ]

    def __str__(self):
        return f"{self.word.lemma} ({'Mastered' if self.mastered else 'Learning'})"