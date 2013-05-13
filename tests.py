import unittest
import re
import os
import six
from rrdtool_cffi import create
from rrdtool_cffi import update
from rrdtool_cffi import fetch
from rrdtool_cffi import error
from rrdtool_cffi import first
from rrdtool_cffi import last
from rrdtool_cffi import info

time_ref = 1368278979


class TestRRDTool(unittest.TestCase):
    SIMPLE_CREATE_ARGS = [
        '/tmp/foo',
        '-b %i' % time_ref,
        '-s 10',
        'DS:a:GAUGE:120:0:U',
        'DS:b:GAUGE:120:0:U',
        'RRA:AVERAGE:0.5:1:100',
        'RRA:AVERAGE:0.5:10:1000'
    ]

    # so it works with old python versions
    def assertRaisesRegexp(self, err_cls, regex):
        return AssertRaisesContext(err_cls, regex, self)

    def tearDown(self):
        if os.path.isfile('/tmp/foo'):
            os.unlink('/tmp/foo')

    def test_create(self):
        create(self.SIMPLE_CREATE_ARGS)
        self.assertTrue(os.path.isfile('/tmp/foo'))

    def test_create_with_lists(self):
        args = [
            '/tmp/foo',
            '-s 10',
            [
                'DS:a:GAUGE:120:0:U',
                'DS:b:GAUGE:120:0:U'
            ],
            [
                'RRA:AVERAGE:0.5:1:100',
                'RRA:AVERAGE:0.5:10:1000'
            ]
        ]
        create(*args)
        self.assertTrue(os.path.isfile('/tmp/foo'))

    def test_create_with_error(self):
        with self.assertRaisesRegexp(error, 'need name of an rrd file'):
            create(())

    def test_update(self):
        create(self.SIMPLE_CREATE_ARGS)
        for i in range(1, 100):
            update('/tmp/foo', '%i:%i:%i' % (time_ref + i, i, i))

    def test_fetch_all_none(self):
        create(self.SIMPLE_CREATE_ARGS)
        ret = fetch(
            '/tmp/foo',
            'AVERAGE',
            '-s %i' % time_ref,
            '-e %i' % (time_ref + 200)
        )

        ref = (
            (1368278970, 1368279180, 10),
            (six.u('a'), six.u('b')),
            [
                (None, None), (None, None), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None)
            ]
        )

        self.assertEqual(ref, ret)

    def test_fetch_with_data(self):
        create(self.SIMPLE_CREATE_ARGS)
        update_start = time_ref + 1
        for ts in range(update_start, update_start + 300, 10):
            update('/tmp/foo', '%i:100:200' % ts)

        ret = fetch(
            '/tmp/foo',
            'AVERAGE',
            '-s %i' % time_ref,
            '-e %i' % (time_ref + 400)
        )

        ref = (
            (1368278970, 1368279380, 10),
            (six.u('a'), six.u('b')),
            [
                (None, None), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0),
                (100.0, 200.0), (100.0, 200.0), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None), (None, None), (None, None), (None, None),
                (None, None)
            ]
        )
        self.assertEqual(ref, ret)

    def test_first(self):
        create(self.SIMPLE_CREATE_ARGS)
        self.assertEqual(1368277980, first('/tmp/foo'))

    def test_last(self):
        create(self.SIMPLE_CREATE_ARGS)
        self.assertEqual(time_ref, last('/tmp/foo'))

        update_start = time_ref + 1
        for ts in range(update_start, update_start + 300, 10):
            update('/tmp/foo', '%i:100:200' % ts)

        self.assertEqual(ts, last('/tmp/foo'))

    def test_info(self):
        create(self.SIMPLE_CREATE_ARGS)
        ret = info('/tmp/foo')

        ref = {
            six.u('filename'): '/tmp/foo',
            six.u('header_size'): 1128,
            six.u('last_update'): 1368278979,
            six.u('step'): 10,
            six.u('rrd_version'): '0003',
            six.u('ds[a].index'): 0,
            six.u('ds[a].value'): 0.0,
            six.u('ds[a].type'): 'GAUGE',
            six.u('ds[a].min'): 0.0,
            six.u('ds[a].max'): None,
            six.u('ds[a].minimal_heartbeat'): 120,
            six.u('ds[a].unknown_sec'): 9,
            six.u('ds[a].last_ds'): 'U',
            six.u('ds[b].index'): 1,
            six.u('ds[b].value'): 0.0,
            six.u('ds[b].type'): 'GAUGE',
            six.u('ds[b].min'): 0.0,
            six.u('ds[b].max'): None,
            six.u('ds[b].minimal_heartbeat'): 120,
            six.u('ds[b].unknown_sec'): 9,
            six.u('ds[b].last_ds'): 'U',
            six.u('rra[0].cf'): 'AVERAGE',
            six.u('rra[0].pdp_per_row'): 1,
            six.u('rra[0].rows'): 100,
            six.u('rra[0].xff'): 0.5,
            six.u('rra[0].cur_row'): 61,
            six.u('rra[0].cdp_prep[1].unknown_datapoints'): 0,
            six.u('rra[0].cdp_prep[1].value'): None,
            six.u('rra[0].cdp_prep[0].unknown_datapoints'): 0,
            six.u('rra[0].cdp_prep[0].value'): None,
            six.u('rra[1].cf'): 'AVERAGE',
            six.u('rra[1].pdp_per_row'): 10,
            six.u('rra[1].rows'): 1000,
            six.u('rra[1].xff'): 0.5,
            six.u('rra[1].cur_row'): 177,
            six.u('rra[1].cdp_prep[1].unknown_datapoints'): 7,
            six.u('rra[1].cdp_prep[1].value'): None,
            six.u('rra[1].cdp_prep[0].unknown_datapoints'): 7,
            six.u('rra[1].cdp_prep[0].value'): None,
        }

        # seems like 'current row is not so stable'
        del ref[six.u('rra[0].cur_row')]
        del ref[six.u('rra[1].cur_row')]
        del ret[six.u('rra[0].cur_row')]
        del ret[six.u('rra[1].cur_row')]
        self.assertEqual(ref, ret)


class AssertRaisesContext(object):
    def __init__(self, err_cls, regex, test_case):
        self.fail = test_case.fail
        self.err_cls = err_cls
        self.regex = regex

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            self.fail("%s not raised" % self.err_cls)

        if not issubclass(exc_type, self.err_cls):
            return False

        if re.search(self.regex, str(exc_value)):
            return True

        raise self.fail("regex did not match")


if __name__ == '__main__':
    unittest.main()
