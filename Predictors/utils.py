from datetime import datetime, date


class TimeUtils:

    @staticmethod
    def get_time_string(da: datetime):
        return da.strftime("%Y-%m-%dT%H:00:00.000Z")

    @staticmethod
    def get_date_string(da: date):
        return da.strftime("%Y-%m-%d")