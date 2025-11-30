from django.core.exceptions import ObjectDoesNotExist

from httpcore import request
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
from task.serializers import ReceiptSerializer, ReceiptListSerializer,ReceiptCustomSerializer
from task.filters import ReceiptFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination

from django.db.models import Sum
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils import timezone

@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=ReceiptListSerializer,
    responses=ReceiptListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllReceipt(request):
    """
    Fetch all non-deleted receipts with pagination
    """
    # Filter out soft-deleted receipts
    receipts = Receipt.objects.filter(is_deleted=False)
    total_elements = receipts.count()

    page = request.query_params.get('page')
    size = request.query_params.get('size')

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Paginate the filtered receipts
    receipts = pagination.paginate_data(receipts)

    # Serialize the paginated receipts
    serializer = ReceiptListSerializer(receipts, many=True)

    response = {
        'reciept': serializer.data,
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
def updateReceipt(request, pk):
    try:
        receipt = Receipt.objects.get(pk=pk)
        data = request.data
        data.pop('extracted_data', None)

        if 'items' in data:

            current_items = receipt.items or []
            updated_items = data.get('items', [])

            for item in current_items[:]:
                if item not in updated_items:
                    current_items.remove(item)

            for item in updated_items:
                if item not in current_items:
                    current_items.append(item)

            receipt.items = current_items

        serializer = ReceiptSerializer(receipt, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except ObjectDoesNotExist:
        return Response({"detail": f"Receipt with id {pk} does not exist."}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteReceipt(request, pk):
    """
    Soft delete a receipt by marking it as deleted
    """
    try:
        receipt = Receipt.objects.get(pk=pk, is_deleted=False)
        
        # Soft delete the receipt
        receipt.is_deleted = True
        receipt.deleted_at = timezone.now()
        receipt.deleted_by = request.user
        receipt.save()
        
        return Response(
            {'detail': f'Receipt id - {pk} is deleted successfully'}, 
            status=status.HTTP_200_OK
        )
    except ObjectDoesNotExist:
        return Response(
            {'detail': f"Receipt id - {pk} doesn't exist or already deleted"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def addItemtoReceipt(request, receipt_id):
    """
    Add a new item to an existing receipt
    """
    receipt = get_object_or_404(Receipt, id=receipt_id)

    name = request.data.get("name")
    qty = request.data.get("qty", 1)

    if not name:
        return Response({"error": "Item name is required"}, status=status.HTTP_400_BAD_REQUEST)
    new_item = {
        "name": name,
        "quantity": qty
    }
    receipt.items = (receipt.items or []) + [new_item]
    receipt.save()

    return Response({
        "message": "Item added successfully",
        "items": receipt.items
    }, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter("page", type=int, description="Page number"),
        OpenApiParameter("size", type=int, description="Page size")
    ],
    request=ReceiptListSerializer,
    responses=ReceiptListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def listReceipts(request):
    receipt_type = request.GET.get("type")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("size", 10))

    base_qs = Receipt.objects.filter(is_deleted=False)

    if receipt_type:
        if receipt_type not in ["expense", "sales", "pantry"]:
            return Response(
                {"error": "Invalid type. Use 'expense', 'sales', or 'pantry'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        receipts = base_qs.filter(receipt_type=receipt_type)
    else:
        receipts = base_qs

    # Pagination
    total_count = receipts.count()
    pagination = Pagination()  
    pagination.page = page
    pagination.size = page_size

    receipts = pagination.paginate_data(receipts)

    serializer = ReceiptCustomSerializer(receipts, many=True)

    response = {
        'reciept': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_count,
    }

    return Response(response, status=status.HTTP_200_OK)

@api_view(['POST'])
def monthly_report(request):
    current_date = datetime.now()
    month_start = current_date.replace(day=1)
    next_month = month_start.replace(day=28) + timedelta(days=4)
    month_end = next_month - timedelta(days=next_month.day)

    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(days=1)

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

    total_sales = sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    total_expenses = expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    profit = total_sales - total_expenses

    last_month_sales = last_month_sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    last_month_expenses = last_month_expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    last_month_profit = last_month_sales - last_month_expenses

    profit_change_percentage = 0
    expense_change_percentage = 0

    if last_month_profit != 0:
        profit_change_percentage = ((profit - last_month_profit) / last_month_profit) * 100
    
    if last_month_expenses != 0:
        expense_change_percentage = ((total_expenses - last_month_expenses) / last_month_expenses) * 100

    profit_change_percentage = f"{profit_change_percentage:.2f}%"
    expense_change_percentage = f"{expense_change_percentage:.2f}%"

    report_data = {
        "month_year": current_date.strftime("%Y-%m"), 
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "profit": profit,
        "last_month_sales": last_month_sales,
        "last_month_expenses": last_month_expenses,
        "last_month_profit": last_month_profit,
        "profit_change_percentage": profit_change_percentage,
        "expense_change_percentage": expense_change_percentage,
    }

    return Response(report_data, status=200)


@api_view(['POST'])
def monthly_statistics(request):
    current_date = datetime.now()
    month_start = current_date.replace(day=1)

    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    months_back = 6  

    monthly_data = []

    for month_offset in range(months_back):
        month_start_date = (month_start - timedelta(days=month_offset * 30)).replace(day=1)
        next_month = month_start_date.replace(day=28) + timedelta(days=4)
        month_end_date = next_month - timedelta(days=next_month.day)

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

        total_sales = sales_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        total_expenses = expense_receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        profit = total_sales - total_expenses

        monthly_data.append({
            "month": month_start_date.strftime("%b"),
            "total_sales": total_sales,
            "total_expenses": total_expenses,
            "profit": profit
        })

    return Response({"monthly_data": monthly_data}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pantry_items(request):
    """
    Return aggregated pantry items: list of {name, quantity}
    """
    receipts = Receipt.objects.filter(receipt_type='pantry')
    # only consider non-deleted pantry receipts
    receipts = Receipt.objects.filter(receipt_type='pantry', is_deleted=False)
    items_map = {}
    for r in receipts:
        for it in (r.items or []):
            if isinstance(it, dict):
                name = (it.get('name') or it.get('item_name') or '').strip()
                qty = it.get('quantity', it.get('qty', 1))
            else:
                name = str(it).strip()
                qty = 1

            if not name:
                continue
            try:
                qty = int(qty)
            except Exception:
                try:
                    qty = int(float(qty))
                except Exception:
                    qty = 0

            items_map[name] = items_map.get(name, 0) + qty

    items = [{"name": n, "quantity": q} for n, q in items_map.items()]
    return Response({"items": items}, status=200)


@extend_schema(
    request={"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object"}}}},
    responses={200: {"type": "object"}}
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def pantry_update(request):
    """
    Update ONLY qty for pantry inventory items across ALL pantry receipts.
    - Payload: {"items":[{"name":"Milk","qty":2} ... ]}
    - If an incoming item has qty <= 0 or "delete": true -> item is removed from each pantry receipt
    - This updates all receipts with receipt_type='pantry' (ignores receipt_id).
    - Does NOT modify price fields (subtotal, total_cost, tax, vat, discount).
    - Distributes incoming totals across all pantry receipts so aggregated totals equal incoming totals.
    """
    items = request.data.get('items')
    if not isinstance(items, list):
        return Response({"error": "items must be a list"}, status=status.HTTP_400_BAD_REQUEST)

    # normalize incoming instructions
    incoming = {}
    for it in items:
        if not isinstance(it, dict):
            return Response({"error": "each item must be an object with name and qty/quantity or delete flag"}, status=status.HTTP_400_BAD_REQUEST)
        name = (it.get('name') or it.get('item_name') or '').strip()
        if not name:
            return Response({"error": "each item must include a name"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            qty = int(it.get('qty', it.get('quantity', 0)) or 0)
        except Exception:
            try:
                qty = int(float(it.get('qty', it.get('quantity', 0))))
            except Exception:
                qty = 0
        delete_flag = bool(it.get('delete', False)) or (qty <= 0)
        incoming[name.lower()] = {"name": name, "qty": qty, "delete": delete_flag}

    # Update ALL pantry receipts (ignore single receipt targeting)
    receipts_qs = Receipt.objects.filter(receipt_type='pantry', is_deleted=False)

    # If no pantry receipts exist, create one (only with item qtys — prices left default)
    if not receipts_qs.exists():
        normalized = []
        for v in incoming.values():
            if not v['delete']:
                normalized.append({"name": v["name"], "qty": v["qty"], "quantity": v["qty"]})
        if not normalized:
            return Response({"items": [], "message": "nothing to create, all incoming items marked for deletion"}, status=status.HTTP_200_OK)
        inventory = Receipt.objects.create(
            date='',
            time='',
            shop_name='pantry_inventory',
            address='',
            payment_method='',
            items=normalized,
            services=[],
            vat_percentage=0.0,
            vat_amount=0.0,
            subtotal=0.0,
            tax=0.0,
            discount=0.0,
            quantity=sum(i['qty'] for i in normalized),
            total_cost=0.0,
            extracted_data={"source": "pantry_update_created"},
            processed_at=datetime.now(),
            receipt_type='pantry'
        )
        response_items = [{"name": it["name"], "quantity": int(it["qty"])} for it in normalized]
        return Response({"items": response_items, "receipt_ids": [inventory.id]}, status=status.HTTP_200_OK)

    # DISTRIBUTE incoming totals across all pantry receipts so aggregated totals
    # equal the incoming quantities (instead of setting same qty on every receipt).
    receipts = list(receipts_qs)
    n_receipts = len(receipts)
    if n_receipts == 0:
        return Response({"items": [], "modified_receipts": []}, status=status.HTTP_200_OK)

    per_receipt_assignments = [dict() for _ in range(n_receipts)]
    delete_names = set()

    for key, inc in incoming.items():
        if inc['delete']:
            delete_names.add(key)
            continue
        total = max(0, int(inc['qty'] or 0))
        base = total // n_receipts
        rem = total % n_receipts
        for idx in range(n_receipts):
            assigned = base + (1 if idx < rem else 0)
            per_receipt_assignments[idx][key] = assigned

    modified_receipts = []
    for idx, inventory in enumerate(receipts):
        assignment = per_receipt_assignments[idx]
        # build existing map
        existing = {}
        for it in (inventory.items or []):
            if isinstance(it, dict):
                n = (it.get('name') or it.get('item_name') or '').strip()
                if not n:
                    continue
                try:
                    current_qty = int(it.get('qty', it.get('quantity', 0)) or 0)
                except Exception:
                    try:
                        current_qty = int(float(it.get('qty', it.get('quantity', 0))))
                    except Exception:
                        current_qty = 0
                item_copy = dict(it)
                item_copy['qty'] = current_qty
                item_copy['quantity'] = current_qty
                existing[n.lower()] = item_copy
            else:
                n = str(it).strip()
                if n:
                    existing[n.lower()] = {"name": n, "qty": 1, "quantity": 1}

        # remove globals marked for deletion
        for d in delete_names:
            existing.pop(d, None)

        # apply this receipt's assigned updates
        for key, assigned_qty in assignment.items():
            if assigned_qty <= 0:
                existing.pop(key, None)
                continue
            if key in existing:
                existing[key]['qty'] = assigned_qty
                existing[key]['quantity'] = assigned_qty
            else:
                existing[key] = {"name": incoming[key]['name'], "qty": assigned_qty, "quantity": assigned_qty}

        updated_items = [v for v in existing.values()]
        inventory.items = updated_items
        inventory.quantity = sum(int(i.get('qty', i.get('quantity', 0)) or 0) for i in updated_items)
        inventory.processed_at = datetime.now()
        inventory._skip_recalc = True
        try:
            inventory.save(update_fields=['items', 'quantity', 'processed_at'], skip_recalc=True)
        except TypeError:
            inventory.save(update_fields=['items', 'quantity', 'processed_at'])
        modified_receipts.append(inventory.id)

    response_items = [{"name": inc['name'], "quantity": int(inc['qty'])} for inc in incoming.values() if not inc['delete']]
    return Response({"items": response_items, "modified_receipts": modified_receipts}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_pantry_item(request):
    """
    Permanently remove pantry items from ALL pantry receipts (receipt_type='pantry').
    Accepts JSON body: {"name":"X"} or {"names":["A","B"]} or {"items":[{"name":"A"}]}
    Returns list of removed names and receipts modified.
    """
    data = request.data or {}

    names = data.get('names')
    single = data.get('name')
    items_list = data.get('items')

    if isinstance(items_list, list):
        extracted = []
        for it in items_list:
            if isinstance(it, dict):
                n = (it.get('name') or it.get('item_name') or '').strip()
                if n:
                    extracted.append(n)
            elif isinstance(it, str):
                extracted.append(it.strip())
        if extracted:
            names = extracted

    if isinstance(names, str) and ',' in names:
        names = [n.strip() for n in names.split(',') if n.strip()]

    if not names and single:
        names = [single]

    if not names:
        return Response({"error": "Provide 'name' or 'names' or 'items' to delete"}, status=status.HTTP_400_BAD_REQUEST)

    targets = [t.strip() for t in (names or []) if isinstance(t, str) and t.strip()]
    if not targets:
        return Response({"error": "No valid names provided"}, status=status.HTTP_400_BAD_REQUEST)
    targets_lower = set(t.lower() for t in targets)

    receipts = Receipt.objects.filter(receipt_type='pantry')
    modified_receipts = []
    removed_global = set()

    for inventory in receipts:
        kept = []
        removed_local = []
        for it in (inventory.items or []):
            if isinstance(it, dict):
                n = (it.get('name') or it.get('item_name') or '').strip()
            else:
                n = str(it).strip()
            if not n:
                continue
            if n.lower() in targets_lower:
                removed_local.append(n)
                continue
            kept.append(it)

        if removed_local:
            inventory.items = kept
            inventory.quantity = sum(int(i.get('qty', i.get('quantity', 0)) or 0) if isinstance(i, dict) else 1 for i in kept)
            inventory.processed_at = datetime.now()

            inventory._skip_recalc = True
            try:
                inventory.save(update_fields=['items', 'quantity', 'processed_at'], skip_recalc=True)
            except TypeError:
                inventory.save(update_fields=['items', 'quantity', 'processed_at'])

            modified_receipts.append(inventory.id)
            for n in removed_local:
                removed_global.add(n)

    if not modified_receipts:
        return Response({"error": "No matching item(s) found to delete"}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "removed": sorted(list(removed_global)),
        "modified_receipts": modified_receipts
    }, status=status.HTTP_200_OK)


