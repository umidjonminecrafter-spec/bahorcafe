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
                service_percent=0.0,
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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

class TelegramBotSettingsView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, branch_id=None):
        from .models import TelegramBotSettings
        if branch_id:
            obj = TelegramBotSettings.objects.filter(branch_id=branch_id).first()
            if obj:
                return obj
        obj = TelegramBotSettings.objects.first()
        if not obj:
            branch = Branch.objects.first()
            obj = TelegramBotSettings.objects.create(
                branch=branch,
                bot_token="",
                chat_id="",
                is_active=True,
                notify_order_paid=True,
                notify_order_cancelled=True,
                notify_daily_report=True,
                daily_report_time="20:00"
            )
        return obj

    def get(self, request):
        from .serializers import TelegramBotSettingsSerializer
        branch_id = request.query_params.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = TelegramBotSettingsSerializer(obj)
        return Response(serializer.data)

    def post(self, request):
        return self.put(request)

    def put(self, request):
        from .serializers import TelegramBotSettingsSerializer
        branch_id = request.data.get('branch') or request.query_params.get('branch_id')
        obj = self.get_object(branch_id)
        serializer = TelegramBotSettingsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

class TelegramTestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.core.telegram import test_telegram_connection
        token = request.data.get('bot_token') or request.data.get('token')
        chat_id = request.data.get('chat_id')
        ok, msg = test_telegram_connection(bot_token=token, chat_id=chat_id)
        if ok:
            return Response({"status": "success", "message": "Test xabari Telegramga muvaffaqiyatli yuborildi!"})
        else:
            return Response({"status": "error", "message": f"Xatolik: {msg}"}, status=status.HTTP_400_BAD_REQUEST)

class TelegramDailyReportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.core.telegram import send_daily_summary_report
        branch_id = request.data.get('branch_id') or request.query_params.get('branch_id')
        branch = Branch.objects.filter(id=branch_id).first() if branch_id else None
        
        ok, result = send_daily_summary_report(branch=branch, async_send=False)
        if ok:
            return Response({
                "status": "success",
                "message": "Kunlik hisobot Telegramga muvaffaqiyatli yuborildi!",
                "data": result
            })
        else:
            return Response({
                "status": "warning",
                "message": "Hisobot shakllantirildi, ammo Telegram bot token yoki Chat ID sozlanmaganligi sababli xabar yuborilmadi.",
                "data": result
            }, status=status.HTTP_200_OK)

class TelegramWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.core.telegram import process_telegram_update
        update_data = request.data
        res = process_telegram_update(update_data)
        return Response(res, status=status.HTTP_200_OK)



