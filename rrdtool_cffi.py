import math
import threading
import functools
import cffi
import time
from six.moves import xrange


class error(Exception):
    pass

ffi = cffi.FFI()
ffi.cdef("""
    typedef double rrd_value_t;

    typedef struct rrd_blob_t {
        unsigned long size; /* size of the blob */
        unsigned char *ptr; /* pointer */
    } rrd_blob_t;

    typedef enum rrd_info_type {
        RD_I_VAL = 0,
        RD_I_CNT,
        RD_I_STR,
        RD_I_INT,
        RD_I_BLO
    } rrd_info_type_t;

    typedef union rrd_infoval {
        unsigned long u_cnt;
        rrd_value_t u_val;
        char     *u_str;
        int       u_int;
        rrd_blob_t u_blo;
    } rrd_infoval_t;

    typedef struct rrd_info_t {
        char     *key;
        rrd_info_type_t type;
        rrd_infoval_t value;
        struct rrd_info_t *next;
    } rrd_info_t;

    int rrd_create(int, char**);
    int rrd_update(int, char**);
    int rrd_fetch(
        int,
        char **,
        long int *,
        long int *,
        unsigned long *,
        unsigned long *,
        char ***,
        double **);
    long int rrd_first(int, char**);
    long int rrd_last(int, char**);
    rrd_info_t *rrd_info( int, char**);
    void rrd_info_free(rrd_info_t *);
    void rrd_freemem(void*);
    char* rrd_get_error(void);
    void rrd_clear_error(void);
""")

librrd = ffi.dlopen('rrd')


# Unfortunately the methods without the '_r' postfix are *not* threadsafe
# => There must be a process wide global lock. cffi releases the GIL and it
# seems there is no possibility to change this
# => have to implement the global lock here
_global_lock = threading.Lock()


def _syncronize(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _global_lock:
            return func(*args, **kwargs)
    return wrapper


@_syncronize
def create(*args):
    call_args = _prepare_args('create', args)
    if librrd.rrd_create(len(call_args), call_args) == -1:
        raise _get_error()


@_syncronize
def update(*args):
    call_args = _prepare_args('update', args)
    if librrd.rrd_update(len(call_args), call_args) == -1:
        raise _get_error()


@_syncronize
def fetch(*args):
    call_args = _prepare_args('fetch', args)
    start = ffi.new('long int *')
    stop = ffi.new('long int *')
    step = ffi.new('unsigned long *')
    ds_count = ffi.new('unsigned long *')
    ds_names = ffi.new('char ***')
    fetch_ret = ffi.new('double **')
    ret = librrd.rrd_fetch(
        len(call_args),
        call_args,
        start,
        stop,
        step,
        ds_count,
        ds_names,
        fetch_ret
    )

    if ret == -1:
        raise _get_error()

    try:
        return _convert_fetch_result(
            ffi,
            stop,
            start,
            step,
            fetch_ret,
            ds_count,
            ds_names)
    finally:
        for i in range(ds_count[0]):
            librrd.rrd_freemem(ds_names[0][i])
        librrd.rrd_freemem(ds_names[0])
        librrd.rrd_freemem(fetch_ret[0])


@_syncronize
def first(*args):
    call_args = _prepare_args('first', args)
    ret = librrd.rrd_first(len(call_args), call_args)
    if ret == -1:
        raise _get_error()
    return ret


@_syncronize
def last(*args):
    call_args = _prepare_args('last', args)
    ret = librrd.rrd_last(len(call_args), call_args)
    if ret == -1:
        raise _get_error()
    return ret


@_syncronize
def info(*args):
    call_args = _prepare_args('info', args)
    info_ret = librrd.rrd_info(len(call_args), call_args)
    if info_ret == ffi.NULL:
        raise _get_error()

    try:
        return _convert_info(info_ret)
    finally:
        librrd.rrd_info_free(info_ret)


def _prepare_args(cmd_name, args):
    ret = [cmd_name]
    for item in args:
        # to be compatible with the 'native' rrdtool C-Extension bindings
        if isinstance(item, (tuple, list)):
            ret.extend(item)
        else:
            ret.append(item)

    return [ffi.new('char[]', x.encode('ascii')) for x in ret]


def _get_error():
    msg = ffi.string(librrd.rrd_get_error())
    librrd.rrd_clear_error()
    return error(msg)


def _convert_info(info_ret):
    ret = {}
    record = info_ret[0]
    while (record != ffi.NULL):
        type_ = getattr(record, 'type')
        if type_ == librrd.RD_I_VAL:
            val = record.value.u_val
            val = None if math.isnan(val) else val
        elif type_ == librrd.RD_I_CNT:
            val = record.value.u_cnt
        elif type_ == librrd.RD_I_STR:
            val = ffi.string(record.value.u_str).decode('ascii')
        elif type_ == librrd.RD_I_INT:
            val = record.value.u_int
        elif type_ == librrd.RD_I_BLO:
            val = ffi.buffer(record.value.u_blo.ptr, record.value.u_blo.size)
            val = val[:]

        ret[ffi.string(record.key).decode('ascii')] = val
        record = getattr(record, 'next')[0]

    return ret

def _convert_fetch_result(ffi, stop, start, step, fetch_ret, ds_count, ds_names):
   row = (stop[0] - start[0]) // step[0]
   data = []
   index = 0
   for i in xrange(row):
       t = []
       for j in range(ds_count[0]):
           dp = fetch_ret[0][index]
           index += 1
           t.append(None if math.isnan(dp) else dp)
       data.append(tuple(t))

   ds_names_ret = []
   for i in range(ds_count[0]):
       ds_names_ret.append(ffi.string(ds_names[0][i]).decode('ascii'))

   return (
       (start[0], stop[0], step[0]),
       tuple(ds_names_ret),
       data)

def _to_char(ffi, py_string):
    return ffi.new('char[]', py_string.encode('ascii'))



# Here are the thread safe methods
th_ffi = cffi.FFI()
th_ffi.cdef("""
    typedef double rrd_value_t;

    int rrd_create_r(
            const char *,
            unsigned long,
            long int,
            int,
            const char **);

    int rrd_update_r(
        const char *filename,
        const char *_template,
        int argc,
        const char **argv);

    int rrd_fetch_r(
        /* name of the rrd */
        const char *filename,

        /* which consolidation function ? */
        const char *cf,

        /* which time frame do you want ?
         * will be changed to represent reality
         */
        long int *start,
        long int *end,

        /* which stepsize do you want ?
         * will be changed to represent reality
         */
        unsigned long *step,

        /* number of data sources in file */
        unsigned long *ds_cnt,

        /* names of data_sources */
        char ***ds_namv,

        rrd_value_t **data);

    void rrd_freemem(void*);
    char* rrd_get_error(void);
    void rrd_clear_error(void);
    """
)

librrd_th = th_ffi.dlopen('rrd_th')

def create_r(filename, step, start=None, dss=[], rras=[]):
    if start is None:
        start = int(time.time())

    args = [_to_char(th_ffi, x) for x in dss]
    args.extend([_to_char(th_ffi, x) for x in rras])

    ret = librrd_th.rrd_create_r(
        _to_char(th_ffi, filename),
        step,
        start,
        len(args),
        args)

    if ret == -1:
        raise _get_error_th()

def update_r(filename, updates, template=''):
    if not template:
        template = th_ffi.NULL
    else:
        template = _to_char(th_ffi, template)

    args = [_to_char(th_ffi, x) for x in updates]

    ret = librrd_th.rrd_update_r(
        _to_char(th_ffi, filename),
        template,
        len(args),
        args)

    if ret == -1:
        raise _get_error_th()

def fetch_r(filename, cf, py_start, py_stop, py_step=1):
    start = th_ffi.new('long int*')
    start[0] = py_start

    stop = th_ffi.new('long int*')
    stop[0] = py_stop

    step = th_ffi.new('unsigned long*')
    step[0] = py_step

    ds_count = th_ffi.new('unsigned long*')
    ds_names = th_ffi.new('char ***')
    fetch_ret = ffi.new('double **')

    ret = librrd_th.rrd_fetch_r(
        _to_char(th_ffi, filename),
        _to_char(th_ffi, cf),
        start,
        stop,
        step,
        ds_count,
        ds_names,
        fetch_ret)

    if ret == -1:
        raise _get_error_th()

    try:
        return _convert_fetch_result(
            th_ffi,
            stop,
            start,
            step,
            fetch_ret,
            ds_count,
            ds_names)
    finally:
        for i in range(ds_count[0]):
            librrd_th.rrd_freemem(ds_names[0][i])
        librrd_th.rrd_freemem(ds_names[0])
        librrd_th.rrd_freemem(fetch_ret[0])


def _get_error_th():
    msg = th_ffi.string(librrd_th.rrd_get_error())
    librrd_th.rrd_clear_error()
    return error(msg)
