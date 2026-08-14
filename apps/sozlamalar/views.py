from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import Branch, RestaurantSettings, TaxSettings, ReceiptSettings, OrderFlowSettings
from .serializers import (
    BranchSerializer,
    RestaurantSettingsSerializer,
    TaxSettingsSerializer,
    ReceiptSettingsSerializer,
    OrderFlowSettingsSerializer
)

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'city', 'address', 'phone']
    ordering_fields = ['id', 'name', 'created_at']

class RestaurantSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, branch_id=None):
        if branch_id:
            obj = RestaurantSettings.objects.filter(branch_id=branch_id).first()
            if obj:
                return obj
        obj = RestaurantSettings.objects.first()
        if not obj:
            branch = Branch.objects.first()
            obj = RestaurantSettings.objects.create(
                branch=branch,
                name="Bahor Cafe",
                address="Toshkent sh., Mustaqillik ko'chasi",
                phone="+998 90 123 45 67"
            )
        return obj

    def get(self, request):
        branch_id = request.query_params.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = RestaurantSettingsSerializer(obj)
        return Response(serializer.data)

    def post(self, request):
        return self.put(request)

    def put(self, request):
        branch_id = request.data.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = RestaurantSettingsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

class TaxSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, branch_id=None):
        if branch_id:
            obj = TaxSettings.objects.filter(branch_id=branch_id).first()
            if obj:
                return obj
        obj = TaxSettings.objects.first()
        if not obj:
            branch = Branch.objects.first()
            obj = TaxSettings.objects.create(
                branch=branch,
                tax_percent=0.0,
                service_percent=10.0,
                calculation_type='auto'
            )
        return obj

    def get(self, request):
        branch_id = request.query_params.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = TaxSettingsSerializer(obj)
        return Response(serializer.data)

    def post(self, request):
        return self.put(request)

    def put(self, request):
        branch_id = request.data.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = TaxSettingsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

class CheckSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, branch_id=None):
        if branch_id:
            obj = ReceiptSettings.objects.filter(branch_id=branch_id).first()
            if obj:
                return obj
        obj = ReceiptSettings.objects.first()
        if not obj:
            branch = Branch.objects.first()
            obj = ReceiptSettings.objects.create(
                branch=branch,
                cafe_name="Bahor Cafe",
                address="Toshkent sh., Mustaqillik ko'chasi",
                phone="+998901234567"
            )
        return obj

    def get(self, request):
        branch_id = request.query_params.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = ReceiptSettingsSerializer(obj)
        return Response(serializer.data)

    def post(self, request):
        return self.put(request)

    def put(self, request):
        branch_id = request.data.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = ReceiptSettingsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

class OrderFlowSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, branch_id=None):
        if branch_id:
            obj = OrderFlowSettings.objects.filter(branch_id=branch_id).first()
            if obj:
                return obj
        obj = OrderFlowSettings.objects.first()
        if not obj:
            branch = Branch.objects.first()
            obj = OrderFlowSettings.objects.create(
                branch=branch,
                auto_kitchen=True,
                signal=True,
                bill_btn=True,
                served=False
            )
        return obj

    def get(self, request):
        branch_id = request.query_params.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = OrderFlowSettingsSerializer(obj)
        return Response(serializer.data)

    def post(self, request):
        return self.put(request)

    def put(self, request):
        branch_id = request.data.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = OrderFlowSettingsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)
