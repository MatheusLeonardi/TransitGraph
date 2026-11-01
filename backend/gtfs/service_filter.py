
def get_active_service_ids(calendar_rows, service_date):
    """
    Retorna os service_ids ativos em uma data.

    Considera os dias da semana e o período de validade
    informado em calendar.txt.
    """

    weekday = service_date.strftime("%A").lower()
    date_string = service_date.strftime("%Y%m%d")

    active_services = set()

    for row in calendar_rows:
        start_date = row["start_date"]
        end_date = row["end_date"]

        if start_date <= date_string <= end_date:
            if row.get(weekday) == "1":
                active_services.add(row["service_id"])

    return active_services
