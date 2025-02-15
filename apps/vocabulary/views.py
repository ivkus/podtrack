from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import VocabularyItem
from .serializers import VocabularyItemSerializer

class VocabularyViewSet(viewsets.ModelViewSet):
    queryset = VocabularyItem.objects.all()
    serializer_class = VocabularyItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mastered', 'ignored']

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(word__lemma__icontains=search)
            )
        
        return queryset.select_related('word')

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

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        VocabularyItem.objects.filter(id__in=ids).delete()
        return Response({'status': 'success'})