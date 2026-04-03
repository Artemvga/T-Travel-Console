from rest_framework import generics

from .models import Carrier
from .serializers import CarrierSerializer


class CarrierListAPIView(generics.ListAPIView):
    queryset = Carrier.objects.filter(is_active=True).order_by("name")
    serializer_class = CarrierSerializer
    authentication_classes = []
    permission_classes = []
