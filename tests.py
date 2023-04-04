import datetime
import decimal
from decimal import Decimal
from django.test import TransactionTestCase

# library imports
from .dateutils import date_range, strip_time, local_now_tz_aware, month_first_day, month_last_day
from .dateutils import prev_month_first_day, prev_month_last_day, next_month_first_day, next_month_last_day
from .semaphore import Semaphore, SemaphoreLockedException, semaphore_wait
from .decimal import dec_round_down, dec_round_up
from .misc import iter_blocks, in_memory_csv


class HelpersTests(TransactionTestCase):

    def test_decimal(self):
        prec = decimal.getcontext().prec
        a = Decimal(f'3.{"3"*(prec-1)}')
        x = a*3 + 10
        y = dec_round_down(lambda: a*3 + 10)
        z = dec_round_down(lambda: a*3 + 10, 5)
        self.assertEqual(x, 20)
        self.assertEqual(y, Decimal(f'19.{"9"*(prec-2)}'))
        self.assertEqual(z, Decimal('19.99999'))

        x = a + 10
        y = dec_round_up(lambda: a + 10)
        z = dec_round_up(lambda: a + 10, 3)
        self.assertEqual(x, Decimal(f'13.{"3"*(prec-2)}'))
        self.assertEqual(y, Decimal(f'13.{"3"*(prec-3)}4'))
        self.assertEqual(z, Decimal('13.334'))

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
        s.release()

        s = semaphore_wait(key='test', sem_timeout=5)
        now = local_now_tz_aware()
        self.assertRaises(SemaphoreLockedException, lambda: semaphore_wait('test', wait_timeout=0.5))
        s.release()

        s1 = semaphore_wait(key='test', sem_timeout=3.5)
        callback_num = 0
        def sem_callback(ex):
            nonlocal callback_num
            print(f'ex: {ex}')
            callback_num += 1
        s2 = semaphore_wait(key='test', callback=sem_callback, cb_delay=1, retry_delay=0.1)
        self.assertEqual(callback_num, 4)
        s1.release()
        s2.release()


    def test_misc(self):
        blocks = list(iter_blocks(list(range(25)), 10))
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[-1], [20, 21, 22, 23, 24])

        mem_csv = in_memory_csv((1, 2, 3), headers=('one', 'two', 'three'), values=lambda x: (x, x**2, x**3))
        self.assertEqual(mem_csv.read().splitlines(), ['one,two,three', '1,1,1', '2,4,8', '3,9,27'])
