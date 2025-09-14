from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from drf_spectacular.utils import  extend_schema, OpenApiParameter
from django.http import JsonResponse

from authentication.decorators import has_permissions
from task.models import Receipt
from task.serializers import ReceiptSerializer, ReceiptListSerializer
from task.filters import ReceiptFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination

from django.db.models import Sum

from datetime import datetime, timedelta


@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=ReceiptSerializer,
    responses=ReceiptSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllReceipt(request):
    # Fetch all receipts
    recipts = Receipt.objects.all()
    total_elements = recipts.count()

    page = request.query_params.get('page')
    size = request.query_params.get('size')

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Corrected variable name to 'recipts'
    recipts = pagination.paginate_data(recipts)

    # Serialize the paginated receipts
    serializer = ReceiptListSerializer(recipts, many=True)

    response = {
        'reciept': serializer.data,  # Notice the spelling here is correct as 'reciept'
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    return Response(response, status=status.HTTP_200_OK)





@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=ReceiptSerializer,
	responses=ReceiptSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllReceiptWithoutPagination(request):
	reciept = Receipt.objects.all()

	serializer = ReceiptListSerializer(reciept, many=True)

	return Response({'reciept': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAReceipt(request, pk):
	try:
		city = Receipt.objects.get(pk=pk)
		serializer = ReceiptSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchReceipt(request):
	reciept = ReceiptFilter(request.GET, queryset=Receipt.objects.all())
	reciept = reciept.qs

	print('searched_products: ', reciept)

	total_elements = reciept.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	reciept = pagination.paginate_data(reciept)

	serializer = ReceiptListSerializer(reciept, many=True)

	response = {
		'reciept': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(reciept) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no reciept matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createReceipt(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = ReceiptSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateReceipt(request,pk):
	try:
		city = Receipt.objects.get(pk=pk)
		data = request.data
		serializer = ReceiptSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteReceipt(request, pk):
	try:
		client = Receipt.objects.get(pk=pk)
		client.delete()
		return Response({'detail': f'Receipt id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

# @api_view(['POST'])
# def addItemtoReceipt(request, receipt_id):
#     """
#     Add a new item to an existing receipt
#     """
#     receipt = get_object_or_404(Receipt, id=receipt_id)

#     name = request.data.get("name")
#     qty = request.data.get("qty", 1)

#     if not name:
#         return Response({"error": "Item name is required"}, status=status.HTTP_400_BAD_REQUEST)

#     # Prepare new item dictionary
#     new_item = {
#         "name": name,
#         "quantity": qty
#     }

#     # Append to existing items
#     receipt.items = (receipt.items or []) + [new_item]
#     receipt.save()

#     return Response({
#         "message": "Item added successfully",
#         "items": receipt.items
#     }, status=status.HTTP_200_OK)

# @api_view(['PUT'])
# def updateItemOrService(request, receipt_id, type_str, index):
#     """
#     Update an item or service in a receipt by index
#     type_str: 'item' or 'service'
#     index: position in the JSON array (0-based)
#     """
#     receipt = get_object_or_404(Receipt, id=receipt_id)
    
#     if type_str not in ['item', 'service']:
#         return Response({"error": "type must be 'item' or 'service'"}, status=status.HTTP_400_BAD_REQUEST)

#     data_list = receipt.items if type_str == 'item' else receipt.services

#     if not data_list or index < 0 or index >= len(data_list):
#         return Response({"error": f"{type_str} index out of range"}, status=status.HTTP_400_BAD_REQUEST)

#     # Get updated data
#     name = request.data.get("name", data_list[index].get("name"))
#     quantity = request.data.get("quantity", data_list[index].get("quantity"))

#     # Update the item/service
#     data_list[index]["name"] = name
#     data_list[index]["quantity"] = quantity

#     if type_str == 'item':
#         receipt.items = data_list
#     else:
#         receipt.services = data_list

#     receipt.save()

#     return Response({
#         "message": f"{type_str.capitalize()} updated successfully",
#         type_str + "s": data_list
#     }, status=status.HTTP_200_OK)

# @api_view(['DELETE'])
# def deleteItemOrService(request, receipt_id, type_str, index):
#     """
#     Delete an item or service from a receipt by index
#     """
#     receipt = get_object_or_404(Receipt, id=receipt_id)

#     if type_str not in ['item', 'service']:
#         return Response({"error": "type must be 'item' or 'service'"}, status=status.HTTP_400_BAD_REQUEST)

#     data_list = receipt.items if type_str == 'item' else receipt.services

#     if not data_list or index < 0 or index >= len(data_list):
#         return Response({"error": f"{type_str} index out of range"}, status=status.HTTP_400_BAD_REQUEST)

#     # Remove the item/service
#     removed = data_list.pop(index)

#     if type_str == 'item':
#         receipt.items = data_list
#     else:
#         receipt.services = data_list

#     receipt.save()

#     return Response({
#         "message": f"{type_str.capitalize()} deleted successfully",
#         "removed": removed,
#         type_str + "s": data_list
#     }, status=status.HTTP_200_OK)





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listReceipts(request):
    receipt_type = request.GET.get("type")  # "expense", "sales", or None
    page = int(request.GET.get("page", 1))  # default page = 1
    page_size = int(request.GET.get("page_size", 10))  # default 10 per page

    # Filter by type if provided
    if receipt_type:
        if receipt_type not in ["expense", "sales", "pantry"]:
            return JsonResponse(
                {"error": "Invalid type. Use 'expense', 'sales', or 'pantry'"},
                status=400
            )
        receipts = Receipt.objects.filter(receipt_type=receipt_type)
    else:
        receipts = Receipt.objects.all()

    total_count = receipts.count()
    start = (page - 1) * page_size
    end = start + page_size
    receipts = receipts[start:end]

    data = []
    for r in receipts:
        data.append({
            "id": r.id,
            "receipt_type": r.receipt_type,
            "date": r.date,
            "time": r.time,
            "shop_name": r.shop_name,
            "address": r.address,
            "payment_method": r.payment_method,
            "items": r.items,
            "services": r.services,
            "vat_percentage": r.vat_percentage,
            "vat_amount": r.vat_amount,
            "subtotal": r.subtotal,
            "tax": r.tax,
            "discount": r.discount,
            "quantity": r.quantity,
            "total_cost": r.total_cost,
        })

    return JsonResponse({
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "results": data
    }, status=200)




@api_view(['POST'])
def monthly_report(request):
    # Get the current date
    current_date = datetime.now()

    # Get the first day of the current month (start of the month)
    month_start = current_date.replace(day=1)

    # Get the last day of the current month (end of the month)
    next_month = month_start.replace(day=28) + timedelta(days=4)  # this gives the first day of next month
    month_end = next_month - timedelta(days=next_month.day)  # subtract days to get the last day of the current month

    # Get the first day of last month
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Get the last day of last month
    last_month_end = month_start - timedelta(days=1)

    # Filter receipts for the current month based on the 'date' field (convert to datetime)
    sales_receipts = Receipt.objects.filter(
        date__gte=month_start.strftime('%m/%d/%Y'), 
        date__lte=month_end.strftime('%m/%d/%Y'), 
        receipt_type='sales'
    )
    expense_receipts = Receipt.objects.filter(
        date__gte=month_start.strftime('%m/%d/%Y'), 
        date__lte=month_end.strftime('%m/%d/%Y'), 
        receipt_type='expense'
    )

    # Filter receipts for last month based on the 'date' field
    last_month_sales_receipts = Receipt.objects.filter(
        date__gte=last_month_start.strftime('%m/%d/%Y'), 
        date__lte=last_month_end.strftime('%m/%d/%Y'), 
        receipt_type='sales'
    )
    last_month_expense_receipts = Receipt.objects.filter(
        date__gte=last_month_start.strftime('%m/%d/%Y'), 
        date__lte=last_month_end.strftime('%m/%d/%Y'), 
        receipt_type='expense'
    )

    # Calculate total sales, expenses, and profit for the current month
    total_sales = sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    total_expenses = expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    profit = total_sales - total_expenses

    # Calculate total sales, expenses, and profit for last month
    last_month_sales = last_month_sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    last_month_expenses = last_month_expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    last_month_profit = last_month_sales - last_month_expenses

    # Calculate percentage change in profit and expenses from last month
    profit_change_percentage = 0
    expense_change_percentage = 0

    if last_month_profit != 0:
        profit_change_percentage = ((profit - last_month_profit) / last_month_profit) * 100
    
    if last_month_expenses != 0:
        expense_change_percentage = ((total_expenses - last_month_expenses) / last_month_expenses) * 100

    # Format the percentages to 2 decimal places and add the '%' sign
    profit_change_percentage = f"{profit_change_percentage:.2f}%"
    expense_change_percentage = f"{expense_change_percentage:.2f}%"

    # Prepare the response data
    report_data = {
        "month_year": current_date.strftime("%Y-%m"),  # Current month in "YYYY-MM" format
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "profit": profit,
        "last_month_sales": last_month_sales,
        "last_month_expenses": last_month_expenses,
        "last_month_profit": last_month_profit,  # Include last month's profit
        "profit_change_percentage": profit_change_percentage,
        "expense_change_percentage": expense_change_percentage,
    }

    return Response(report_data, status=200)


@api_view(['POST'])
def monthly_statistics(request):
    # Get the current date
    current_date = datetime.now()

    # Get the first day of the current month (start of the month)
    month_start = current_date.replace(day=1)

    # Get the first day of the previous month
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Get the number of months you want to look back
    months_back = 6  # Last 6 months including the current month

    # Initialize a list to hold monthly data
    monthly_data = []

    # Loop through the last few months
    for month_offset in range(months_back):
        # Calculate the first and last day of the month
        month_start_date = (month_start - timedelta(days=month_offset * 30)).replace(day=1)
        next_month = month_start_date.replace(day=28) + timedelta(days=4)
        month_end_date = next_month - timedelta(days=next_month.day)

        # Get the sales and expense receipts for the given month
        sales_receipts = Receipt.objects.filter(
            date__gte=month_start_date.strftime('%m/%d/%Y'),
            date__lte=month_end_date.strftime('%m/%d/%Y'),
            receipt_type='sales'
        )
        expense_receipts = Receipt.objects.filter(
            date__gte=month_start_date.strftime('%m/%d/%Y'),
            date__lte=month_end_date.strftime('%m/%d/%Y'),
            receipt_type='expense'
        )

        # Calculate total sales, expenses, and profit for the month
        total_sales = sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        total_expenses = expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        profit = total_sales - total_expenses

        # Prepare the monthly data
        monthly_data.append({
            "month": month_start_date.strftime("%b"),  # Month name (e.g., "Jan", "Feb")
            "total_sales": total_sales,
            "total_expenses": total_expenses,
            "profit": profit
        })

    return Response({"monthly_data": monthly_data}, status=200)
