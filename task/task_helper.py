import calendar
from datetime import date as _date, timedelta, datetime as _datetime
from django.utils import timezone
from task.models import Task

def _last_day_of_month(year: int, month: int) -> _date:
    """Get the last day of a given month"""
    last = calendar.monthrange(year, month)[1]
    return _date(year, month, last)

def _generate_and_create_occurrences(task, recurrence):
    """
    Create Task instances for the given task according to recurrence rules:
    - daily: create occurrences from next day up to end of the task's month (NOT crossing the month)
    - weekly: create occurrences on same weekday up to end of the task's month (NOT crossing the month)
    - monthly: create occurrences on same day-of-month up to end of the task's year (NOT crossing the year)
    
    User can select specific dates from the selected_dates array for custom repetition.
    
    Returns list of created Task ids.
    """
    created_ids = []
    if not recurrence or not recurrence.get("pattern"):
        return created_ids

    pattern = (recurrence.get("pattern") or "").lower()
    start_date = task.scheduled_date
    
    # Check if user provided custom selected dates
    selected_dates = recurrence.get("selected_dates", [])
    
    # If user provided selected_dates, use them directly (with validation)
    if selected_dates and isinstance(selected_dates, list) and len(selected_dates) > 0:
        occurrences = []
        for date_str in selected_dates:
            try:
                date_obj = _datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Validate based on pattern rules
                is_valid = False
                
                if pattern == "daily":
                    # Must be in the same month and after start_date
                    if (date_obj.month == start_date.month and 
                        date_obj.year == start_date.year and 
                        date_obj > start_date):
                        is_valid = True
                        
                elif pattern == "weekly":
                    # Must be in the same month, same weekday, and after start_date
                    if (date_obj.month == start_date.month and 
                        date_obj.year == start_date.year and 
                        date_obj.weekday() == start_date.weekday() and 
                        date_obj > start_date):
                        is_valid = True
                        
                elif pattern == "monthly":
                    # Must be in the same year, same day number, and after start_date
                    if (date_obj.year == start_date.year and 
                        date_obj.day == start_date.day and 
                        date_obj > start_date):
                        is_valid = True
                
                if is_valid:
                    occurrences.append(date_obj)
                    
            except Exception as e:
                print(f"Error parsing date {date_str}: {e}")
                continue
    else:
        # Auto-generate dates based on pattern (no selected_dates provided)
        occurrences = _auto_generate_occurrences(start_date, pattern)
    
    # Create the task occurrences
    for occ_date in occurrences:
        # Check if task already exists for this date
        exists = Task.objects.filter(
            created_by=task.created_by,
            task_name=task.task_name,
            scheduled_date=occ_date
        ).exists()
        
        if exists:
            continue
        
        # Create new task instance
        new_task = Task.objects.create(
            task_name=task.task_name,
            task_percentage=task.task_percentage,
            task_category=task.task_category,
            description=task.description,
            scheduled_date=occ_date,
            scheduled_time=task.scheduled_time,
            duration_minutes=task.duration_minutes,
            assigned_to_type=task.assigned_to_type,
            assigned_user=task.assigned_user,
            assigned_partner=task.assigned_partner,
            assigned_child=task.assigned_child,
            priority=task.priority,
            status='pending',
            generated_by_ai=task.generated_by_ai,
            raw_ai_response=None,
            created_by=task.created_by,
            updated_by=task.created_by,
            is_recurring=False,  # Individual occurrences are not marked as recurring
            recurrence_pattern=None
        )
        created_ids.append(new_task.id)
    
    return created_ids


def _auto_generate_occurrences(start_date, pattern):
    """
    Auto-generate occurrence dates based on pattern.
    Returns list of dates.
    """
    occurrences = []
    
    # Define end date based on pattern
    if pattern == "daily":
        # End of current month only
        end_date = _last_day_of_month(start_date.year, start_date.month)
    elif pattern == "weekly":
        # End of current month only
        end_date = _last_day_of_month(start_date.year, start_date.month)
    elif pattern == "monthly":
        # End of current year only
        end_date = _date(start_date.year, 12, 31)
    else:
        return occurrences

    current = start_date
    
    if pattern == "daily":
        # Daily repetition: every day within the same month
        while True:
            current = current + timedelta(days=1)
            
            # Stop if we cross the month boundary
            if current.month != start_date.month or current > end_date:
                break
            
            occurrences.append(current)
    
    elif pattern == "weekly":
        # Weekly repetition: same weekday every week, within the same month
        original_weekday = start_date.weekday()  # 0=Monday, 6=Sunday
        
        while True:
            current = current + timedelta(weeks=1)
            
            # Stop if we cross the month boundary
            if current.month != start_date.month or current > end_date:
                break
            
            # Ensure it's the same weekday
            if current.weekday() == original_weekday:
                occurrences.append(current)
    
    elif pattern == "monthly":
        # Monthly repetition: same day of month, for rest of the year
        original_day = start_date.day
        current_month = start_date.month + 1
        
        while current_month <= 12:
            try:
                # Try to create date with same day number
                next_date = _date(start_date.year, current_month, original_day)
                
                if next_date > end_date:
                    break
                
                occurrences.append(next_date)
            except ValueError:
                # Day doesn't exist in this month (e.g., Feb 30), skip it
                pass
            
            current_month += 1
    
    return occurrences