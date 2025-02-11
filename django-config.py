# settings.py
INSTALLED_APPS = [
    # ... 其他默认应用
    'rest_framework',
    'corsheaders',  # 用于处理跨域请求
    'english_learning',  # 你的应用名称
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 添加到最顶部
    # ... 其他中间件
]

# 允许跨域请求（开发环境）
CORS_ALLOW_ALL_ORIGINS = True  # 生产环境要改为具体的域名

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# urls.py (项目级)
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.articles.views import ArticleViewSet
from apps.vocabulary.views import VocabularyViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'vocabulary', VocabularyViewSet, basename='vocabulary')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]