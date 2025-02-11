from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.articles.views import ArticleViewSet
from apps.vocabulary.views import VocabularyViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'vocabulary', VocabularyViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]