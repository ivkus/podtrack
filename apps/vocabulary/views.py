from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import VocabularyItem
from .serializers import VocabularyItemSerializer

class VocabularyViewSet(viewsets.ModelViewSet):
    queryset = VocabularyItem.objects.all()
    serializer_class = VocabularyItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mastered', 'ignored']

    @action(detail=True, methods=['post'])
    def toggle_mastered(self, request, pk=None):
        item = self.get_object()
        item.mastered = not item.mastered
        item.save()
        return Response({'status': 'success'})

    @action(detail=True, methods=['post'])
    def toggle_ignored(self, request, pk=None):
        item = self.get_object()
        item.ignored = not item.ignored
        item.save()
        return Response({'status': 'success'})