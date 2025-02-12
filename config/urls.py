from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.articles.views import ArticleViewSet
from apps.vocabulary.views import VocabularyViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'vocabulary', VocabularyViewSet)

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/', include(router.urls)),
]