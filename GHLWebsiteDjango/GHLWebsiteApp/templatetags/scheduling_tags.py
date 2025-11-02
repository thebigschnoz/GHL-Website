from django import template
register = template.Library()

@register.filter
def get_day(availability, weekday):
    weekdays = ["sunday", "monday", "tuesday", "wednesday", "thursday"]
    day_field = weekdays[weekday] if weekday < len(weekdays) else "thursday"
    return getattr(availability, day_field, None)

@register.simple_tag
def css_class_for_availability(availability, weekday):
    if availability is None:
        return "unknown"
    
    weekdays = ["sunday", "monday", "tuesday", "wednesday", "thursday"]
    day_field = weekdays[weekday] if weekday < len(weekdays) else "thursday"
    return "available" if getattr(availability, day_field, False) else "unavailable"

@register.simple_tag
def scheduled_player(schedule_map, game_id, pos_id):
    return schedule_map.get((game_id, pos_id))