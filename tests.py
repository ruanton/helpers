import datetime

from django.test import TransactionTestCase

from .dateutils import date_range, strip_time, local_now_tz_aware, month_first_day, month_last_day
from .dateutils import prev_month_first_day, prev_month_last_day, next_month_first_day, next_month_last_day
from .semaphore import Semaphore, SemaphoreLockedException


class HelpersTests(TransactionTestCase):

    def test_dateutils(self):
        ref_date = datetime.datetime(year=2022, month=2, day=14)

        x = month_first_day()
        self.assertEqual(x, strip_time(x))
        self.assertEqual(x.day, 1)

        x = month_last_day(ref_date)
        self.assertEqual(x, datetime.datetime(year=2022, month=2, day=28))

        x = date_range(ref_date, 4)
        self.assertEqual(len(x), 4)
        self.assertEqual(x[0], ref_date)
        self.assertEqual(x[-1], ref_date + datetime.timedelta(days=3))

        x = date_range(ref_date, 4, reverse=True)
        self.assertEqual(len(x), 4)
        self.assertEqual(x[-1], ref_date)
        self.assertEqual(x[0], ref_date + datetime.timedelta(days=3))

        x = prev_month_first_day(ref_date)
        self.assertEqual(x, datetime.datetime(year=2022, month=1, day=1))

        x = prev_month_last_day(ref_date)
        self.assertEqual(x, datetime.datetime(year=2022, month=1, day=31))

        x = next_month_first_day(ref_date)
        self.assertEqual(x, datetime.datetime(year=2022, month=3, day=1))

        x = next_month_last_day(ref_date)
        self.assertEqual(x, datetime.datetime(year=2022, month=3, day=31))

    def test_semaphore(self):
        now = local_now_tz_aware()
        s = Semaphore('test')
        self.assertGreaterEqual(s.pinged, now)
        self.assertGreaterEqual(s.locked, now)

        self.assertRaises(SemaphoreLockedException, lambda: Semaphore('test'))

        s.release()
        now = local_now_tz_aware()
        s = Semaphore('test', timeout=123)
        self.assertGreaterEqual(s.pinged, now)
        self.assertGreaterEqual(s.locked, now)
        self.assertEqual(s.timeout, 123)

        now = local_now_tz_aware()
        s.ping()
        self.assertLessEqual(s.locked, now)
        self.assertGreaterEqual(s.pinged, now)
